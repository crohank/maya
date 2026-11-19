"""GPU model manager: Cosmos3-Edge resident, Qwen3-VL-4B loaded on demand.

Cosmos NF4 peaks 2.4 GiB and Qwen3-VL-4B NF4 peaks 3.6 GiB against about
5.2 GB free on the 8 GB card, so a load evicts the other model whenever
torch.cuda.mem_get_info says the incoming one does not fit. Every load, unload
and swap is timed and logged to results/app_models.jsonl.
"""
import gc
import json
import logging
import re
import threading
import time
from pathlib import Path

import torch
from transformers import AutoModelForImageTextToText, AutoProcessor, BitsAndBytesConfig

log = logging.getLogger("maya.models")

COSMOS_SYSTEM = (
    "You are the eyes of a blind pedestrian. The video is from a camera on their "
    "chest, facing where they walk. Say where things are (left, right, ahead) "
    "and how many steps away. Answer in one short sentence. Never say it is "
    "safe to cross or go, and never make crossing decisions."
)
COSMOS_DEFAULT_QUESTION = (
    "Name the nearest person, vehicle, or obstacle in my path and where it is, "
    "in under 10 words. Example answers: 'Person walking toward you, slightly "
    "left.' 'Bus passing on your right.' 'Pole two steps ahead.'"
)
COSMOS_SUFFIX = " Answer in one short sentence about what you see."
TIMESTAMP_JUNK = re.compile(r"<\s*[\d.]+(\s*seconds?)?\s*>")
QWEN_SYSTEM = (
    "You help a person with low vision. Read any text exactly as written, "
    "including numbers. Answer in at most two sentences."
)


class Conv3dAsLinear(torch.nn.Module):
    """Patch-embed Conv3d whose kernel equals its stride is a plain matmul.

    Copied from scripts/compare_image_models.py. On the RTX 5060 (sm_120), torch
    2.9.0+cu128, Qwen3-VL's bf16 Conv3d patch embed took 14 to 17 s per 640x360
    image; one matmul over the same weights takes 0.2 ms (docs/decisions.md D5).
    """

    def __init__(self, conv):
        super().__init__()
        out_ch = conv.out_channels
        self.weight = torch.nn.Parameter(conv.weight.detach().reshape(out_ch, -1), requires_grad=False)
        self.bias = None if conv.bias is None else torch.nn.Parameter(conv.bias.detach(), requires_grad=False)

    def forward(self, x):
        y = torch.nn.functional.linear(x.reshape(x.shape[0], -1).to(self.weight.dtype), self.weight, self.bias)
        return y.view(x.shape[0], -1, 1, 1, 1)


def patch_conv3d(model):
    visual = getattr(getattr(model, "model", model), "visual", None)
    conv = getattr(getattr(visual, "patch_embed", None), "proj", None)
    if isinstance(conv, torch.nn.Conv3d) and tuple(conv.kernel_size) == tuple(conv.stride):
        visual.patch_embed.proj = Conv3dAsLinear(conv)
        return True
    return False


def _generate(model, proc, system, media, question, max_new_tokens):
    messages = [
        {"role": "system", "content": [{"type": "text", "text": system}]},
        {"role": "user", "content": [media, {"type": "text", "text": question}]},
    ]
    inputs = proc.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=True, return_dict=True,
        return_tensors="pt", enable_thinking=False,
    ).to(model.device)
    with torch.inference_mode():
        out = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    n_in = inputs["input_ids"].shape[-1]
    return proc.decode(out[0][n_in:], skip_special_tokens=True).strip(), n_in


def free_gib():
    free, _ = torch.cuda.mem_get_info()
    return free / 2**30


class ModelManager:
    def __init__(self, cfg, log_path):
        self.cfg = cfg
        self.loaded = {}          # name -> (model, proc)
        self.last_used = {}
        # One GPU job at a time: generate and load/unload never overlap.
        self.lock = threading.RLock()
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _log(self, event, **kw):
        row = {"ts": round(time.time(), 3), "event": event, **kw,
               "free_gib": round(free_gib(), 2),
               "allocated_gib": round(torch.cuda.memory_allocated() / 2**30, 2)}
        log.info("%s", row)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")

    def _load(self, name):
        spec = self.cfg[name]
        t = time.perf_counter()
        if name == "cosmos":
            proc = AutoProcessor.from_pretrained(spec.get("processor_id", spec["id"]))
            model = AutoModelForImageTextToText.from_pretrained(spec["id"], device_map="cuda").eval()
        else:
            quant = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
                llm_int8_skip_modules=["model.visual", "lm_head"],
            )
            proc = AutoProcessor.from_pretrained(spec["id"])
            # Quantizing the 8 GB BF16 checkpoint on every load is the slow part of
            # a swap, so the first load saves the NF4 weights and later loads read those.
            cache = Path(spec.get("nf4_cache", ""))
            if spec.get("nf4_cache") and (cache / "config.json").exists():
                model = AutoModelForImageTextToText.from_pretrained(
                    cache, device_map="cuda", dtype=torch.bfloat16).eval()
            else:
                model = AutoModelForImageTextToText.from_pretrained(
                    spec["id"], device_map="cuda", quantization_config=quant, dtype=torch.bfloat16,
                ).eval()
                if spec.get("nf4_cache"):
                    try:
                        model.save_pretrained(cache)
                    except Exception:
                        log.exception("could not save NF4 copy to %s", cache)
            if not patch_conv3d(model):
                log.warning("Qwen3-VL patch embed not patched; expect about 15 s per image")
        self.loaded[name] = (model, proc)
        self.last_used[name] = time.time()
        dt = time.perf_counter() - t
        self._log("load", model=name, seconds=round(dt, 2))
        return dt

    def _unload(self, name):
        if name not in self.loaded:
            return 0.0
        t = time.perf_counter()
        del self.loaded[name]
        gc.collect()
        torch.cuda.empty_cache()
        dt = time.perf_counter() - t
        self._log("unload", model=name, seconds=round(dt, 2))
        return dt

    def ensure(self, name):
        """Load `name`, evicting the other model if it does not fit. Returns seconds spent."""
        with self.lock:
            if name in self.loaded:
                return 0.0
            t = time.perf_counter()
            need = self.cfg[name]["need_gib"]
            exclusive = self.cfg.get("exclusive", True)
            evicted = []
            for other in list(self.loaded):
                if not exclusive and free_gib() >= need:
                    break
                self._unload(other)
                evicted.append(other)
            self._load(name)
            dt = time.perf_counter() - t
            if evicted:
                self._log("swap", model=name, evicted=evicted, seconds=round(dt, 2))
            return dt

    def warm_up(self, name):
        from PIL import Image
        with self.lock:
            self.ensure(name)
            model, proc = self.loaded[name]
            t = time.perf_counter()
            _generate(model, proc, "", {"type": "image", "image": Image.new("RGB", (64, 64))}, "Hi", 4)
            self._log("warm_up", model=name, seconds=round(time.perf_counter() - t, 2))

    def ask_video(self, clip_path, question):
        media = {"type": "video", "path": clip_path}
        if not question:
            return self._ask("cosmos", COSMOS_SYSTEM, media, COSMOS_DEFAULT_QUESTION)
        text, info = self._ask("cosmos", COSMOS_SYSTEM, media, question + COSMOS_SUFFIX)
        # "Is it safe to cross?" on the 3874684 clip returned only timestamps
        # ("<0.75 seconds> <1.25 seconds> ..."); fall back to the describe prompt.
        if TIMESTAMP_JUNK.search(text) or not re.search(r"[A-Za-z]{3}", text):
            text, retry = self._ask("cosmos", COSMOS_SYSTEM, media, COSMOS_DEFAULT_QUESTION)
            info["model_s"] += retry["model_s"]
            info["retried"] = True
        return text, info

    def ask_image(self, image, question):
        return self._ask("qwen", QWEN_SYSTEM, {"type": "image", "image": image}, question)

    def _ask(self, name, system, media, question):
        with self.lock:
            load_s = self.ensure(name)
            model, proc = self.loaded[name]
            t = time.perf_counter()
            text, n_in = _generate(model, proc, system, media, question,
                                   self.cfg[name]["max_new_tokens"])
            self.last_used[name] = time.time()
            return text, {"load_s": load_s, "model_s": time.perf_counter() - t, "input_tokens": n_in}

    def reap_idle(self):
        """Unload Qwen after its idle timeout, then bring Cosmos back if it was evicted."""
        idle = self.cfg["qwen"]["idle_unload_s"]
        if not self.lock.acquire(blocking=False):
            return
        try:
            if "qwen" in self.loaded and time.time() - self.last_used["qwen"] > idle:
                self._unload("qwen")
            # Only refill an empty GPU: with exclusive on, loading Cosmos while
            # Qwen is still in use would evict Qwen between two reads.
            if self.cfg["cosmos"].get("resident") and not self.loaded:
                self.ensure("cosmos")
        finally:
            self.lock.release()

    def status(self):
        return {"loaded": sorted(self.loaded),
                "free_gib": round(free_gib(), 2),
                "allocated_gib": round(torch.cuda.memory_allocated() / 2**30, 2)}
