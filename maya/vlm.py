"""Qwen3-VL-4B NF4 as the one resident model for image, video, document and code items.

Load path and Conv3d fix follow app/models.py (docs/decisions.md D5). The NF4
weights saved by the app on first load are reused here, so a load is a read,
not a re-quantization.
"""
import time
from pathlib import Path

import torch
from transformers import AutoModelForImageTextToText, AutoProcessor, BitsAndBytesConfig

MODEL_ID = "Qwen/Qwen3-VL-4B-Instruct"
NF4_CACHE = Path("/root/.cache/huggingface/maya/qwen3vl-4b-nf4")


class Conv3dAsLinear(torch.nn.Module):
    """Patch embed whose kernel equals its stride, as one matmul.

    bf16 Conv3d on sm_120 with torch 2.9.0 took 14 to 17 s per image; this takes
    0.2 ms with the same weights (docs/decisions.md D5).
    """

    def __init__(self, conv):
        super().__init__()
        out_ch = conv.out_channels
        self.weight = torch.nn.Parameter(conv.weight.detach().reshape(out_ch, -1), requires_grad=False)
        self.bias = None if conv.bias is None else torch.nn.Parameter(conv.bias.detach(), requires_grad=False)

    def forward(self, x):
        y = torch.nn.functional.linear(x.reshape(x.shape[0], -1).to(self.weight.dtype), self.weight, self.bias)
        return y.view(x.shape[0], -1, 1, 1, 1)


def _patch_conv3d(model):
    visual = getattr(getattr(model, "model", model), "visual", None)
    conv = getattr(getattr(visual, "patch_embed", None), "proj", None)
    if isinstance(conv, torch.nn.Conv3d) and tuple(conv.kernel_size) == tuple(conv.stride):
        visual.patch_embed.proj = Conv3dAsLinear(conv)


class Vlm:
    def __init__(self, model_id=MODEL_ID, nf4_cache=NF4_CACHE):
        t = time.perf_counter()
        self.proc = AutoProcessor.from_pretrained(model_id)
        if nf4_cache and (Path(nf4_cache) / "config.json").exists():
            self.model = AutoModelForImageTextToText.from_pretrained(
                nf4_cache, device_map="cuda", dtype=torch.bfloat16).eval()
        else:
            quant = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
                llm_int8_skip_modules=["model.visual", "lm_head"])
            self.model = AutoModelForImageTextToText.from_pretrained(
                model_id, device_map="cuda", quantization_config=quant, dtype=torch.bfloat16).eval()
        _patch_conv3d(self.model)
        self.load_s = time.perf_counter() - t

    def chat(self, content, system=None, max_new_tokens=128, history=None, processor_kwargs=None):
        """content: list of {"type": "text"|"image"|"video", ...} for the user turn.

        history: earlier (user_content, assistant_text) pairs, for retry loops.
        processor_kwargs: e.g. {"do_sample_frames": False, "video_metadata": ...} for a
        frame list; without it the processor resamples frames as 24 fps footage
        (maya/video.py qwen_chat).
        Returns (text, info) with input tokens and seconds.
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": [{"type": "text", "text": system}]})
        for user, answer in history or []:
            messages.append({"role": "user", "content": user})
            messages.append({"role": "assistant", "content": [{"type": "text", "text": answer}]})
        messages.append({"role": "user", "content": content})
        inputs = self.proc.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True, return_dict=True,
            return_tensors="pt", enable_thinking=False,
            **({"processor_kwargs": processor_kwargs} if processor_kwargs else {})).to(self.model.device)
        t = time.perf_counter()
        with torch.inference_mode():
            out = self.model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
        n_in = inputs["input_ids"].shape[-1]
        text = self.proc.decode(out[0][n_in:], skip_special_tokens=True).strip()
        return text, {"input_tokens": int(n_in), "output_tokens": int(out.shape[-1] - n_in),
                      "model_s": round(time.perf_counter() - t, 3)}

    def text(self, prompt, system=None, max_new_tokens=256, history=None):
        return self.chat([{"type": "text", "text": prompt}], system, max_new_tokens, history)
