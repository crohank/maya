"""Short-video questions: sampled frames to Qwen3-VL, plus pixel measurements for synthetic clips.

Options (eng.opts, strings; defaults in DEFAULTS, chosen on results/pack/vid_* and hv_* runs):
  video_fps      frames per second sent to the VLM
  video_max      cap on frames sent; first and last frame are always kept
  video_side     long side of each frame in px
  video_cv       1: add maya/video_cv.py measurements when the clip looks synthetic
  video_prompt   plain | steps (short time-ordered notes, then an "Answer:" line)
  video_input    video (one video input) | images (one image per frame, timestamped)
  video_model    qwen | cosmos
  video_resample 1: let the processor resample the frames (the old behavior, 4 frames seen)
  video_style    short (answer first, at most one more sentence) | sentence (one full sentence)
  video_debug    1: print measurements and token counts
"""
import re
import time

import av
import numpy as np
from PIL import Image

from . import video_cv

SYSTEM = ("You answer questions about a short video for a person who cannot see it. "
          "Start with the answer itself, then at most one short sentence.")
SYSTEM_SENTENCE = ("You answer questions about a short video for a person who cannot see it. "
                   "Reply with one short, complete sentence that states the answer. "
                   "Write counts as digits.")
STEPS = ("First write at most four short lines, in time order, about what changes in the video "
         "that matters for the question. Then write the final answer on a last line that starts "
         "with 'Answer:'. The final answer is a full short sentence.")
FACTS_HEAD = ("Measured from every frame by pixel analysis (exact for counts, colors, order of "
              "appearance, motion, size and background; read any text yourself):")
DEFAULTS = {"video_fps": "2", "video_max": "32", "video_side": "448", "video_cv": "1",
            "video_prompt": "plain", "video_input": "video", "video_model": "qwen",
            "video_resample": "0", "video_style": "short"}


def decode(path, max_fps=12.0, long_side=640):
    """RGB frames at most `max_fps` and `long_side`, so a 30 s 1080p upload stays near 330 MB."""
    frames, times, next_t, last = [], [], None, None
    with av.open(path) as c:
        s = c.streams.video[0]
        s.thread_type = "AUTO"
        for f in c.decode(s):
            t = float(f.pts * s.time_base) if f.pts is not None else len(times) / 24.0
            last = (f, t)
            if next_t is not None and t + 1e-6 < next_t:
                continue
            next_t = t + 1.0 / max_fps if next_t is None else next_t + 1.0 / max_fps
            frames.append(_rgb(f, long_side))
            times.append(t)
        if last is not None and last[1] != times[-1]:
            frames.append(_rgb(last[0], long_side))
            times.append(last[1])
    return frames, times


def _rgb(f, long_side):
    k = min(1.0, long_side / max(f.width, f.height))
    if k < 1:
        a = f.reformat(width=round(f.width * k) // 2 * 2, height=round(f.height * k) // 2 * 2,
                       format="rgb24").to_ndarray()
    else:
        a = f.to_ndarray(format="rgb24")
    # PyAV does not apply the display matrix, so portrait phone clips decode sideways.
    # f.rotation is counterclockwise degrees; np.rot90 with this k matched ffmpeg's
    # autorotate on clips tagged rotate=90, 180 and 270.
    turns = round((getattr(f, "rotation", 0) or 0) / 90) % 4
    return np.ascontiguousarray(np.rot90(a, turns)) if turns else a


def pick(times, fps, max_frames):
    """Indices at about `fps`, always including the first and last frame."""
    idx, next_t = [], times[0]
    for i, t in enumerate(times):
        if t + 1e-6 >= next_t:
            idx.append(i)
            next_t += 1.0 / fps
    if idx[-1] != len(times) - 1:
        idx.append(len(times) - 1)
    if len(idx) > max_frames:
        idx = sorted({idx[round(k)] for k in np.linspace(0, len(idx) - 1, max_frames)})
    return idx


def to_pil(frame, side):
    im = Image.fromarray(frame)
    im.thumbnail((side, side))
    return im


def final_line(text):
    m = re.search(r"answer\s*:\s*(.+)", text, re.I | re.S)
    if not m:
        return text.strip()
    return m.group(1).strip().split("\n")[0].strip()


def cosmos_loader():
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor
    mid = "ubr-physical-ai/Cosmos3-Edge-NF4-bnb"
    t = time.perf_counter()
    proc = AutoProcessor.from_pretrained(mid)
    model = AutoModelForImageTextToText.from_pretrained(mid, device_map="cuda").eval()
    return {"proc": proc, "model": model, "torch": torch, "load_s": time.perf_counter() - t}


def cosmos_chat(cm, content, system, max_new_tokens, processor_kwargs):
    msgs = [{"role": "system", "content": [{"type": "text", "text": system}]},
            {"role": "user", "content": content}]
    has_video = any(c["type"] == "video" for c in content)
    inputs = cm["proc"].apply_chat_template(
        msgs, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt",
        enable_thinking=False,
        processor_kwargs=processor_kwargs if has_video else None).to(cm["model"].device)
    t = time.perf_counter()
    with cm["torch"].inference_mode():
        out = cm["model"].generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    n_in = inputs["input_ids"].shape[-1]
    text = cm["proc"].decode(out[0][n_in:], skip_special_tokens=True).strip()
    # vid_b2_cosmos_cv2 (64 new tokens): 11 of 15 answers were reasoning text cut
    # before "</think>"; the answer follows that tag when the model reasons anyway.
    text = text.split("</think>")[-1].strip()
    return text, {"input_tokens": int(n_in), "model_s": round(time.perf_counter() - t, 3)}


def qwen_chat(vlm, content, system, max_new_tokens, processor_kwargs):
    """maya/vlm.py Vlm.chat plus processor_kwargs, which Vlm.chat cannot pass.

    Without do_sample_frames=False the Qwen3-VL processor treats a frame list
    as 24 fps footage and resamples it to 2 fps: 11 to 19 frames from a 5 to 9 s
    practice clip collapsed to 4 frames (about 290 visual tokens) in every case.
    """
    import torch
    messages = [{"role": "system", "content": [{"type": "text", "text": system}]},
                {"role": "user", "content": content}]
    inputs = vlm.proc.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=True, return_dict=True,
        return_tensors="pt", enable_thinking=False, processor_kwargs=processor_kwargs).to(vlm.model.device)
    t = time.perf_counter()
    with torch.inference_mode():
        out = vlm.model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    n_in = inputs["input_ids"].shape[-1]
    text = vlm.proc.decode(out[0][n_in:], skip_special_tokens=True).strip()
    return text, {"input_tokens": int(n_in), "output_tokens": int(out.shape[-1] - n_in),
                  "model_s": round(time.perf_counter() - t, 3)}


def answer(eng, path, question):
    o = {**DEFAULTS, **{k: v for k, v in eng.opts.items() if k.startswith("video_")}}
    fps, side, cap = float(o["video_fps"]), int(o["video_side"]), int(o["video_max"])
    frames, times = decode(path)
    idx = pick(times, fps, cap)
    if len(idx) < 2:
        # Qwen3-VL merges frames in pairs (temporal_patch_size 2) and raises on one frame.
        idx = idx * 2
    ims = [to_pil(frames[i], side) for i in idx]

    facts, cv_info = [], {}
    if o["video_cv"] == "1":
        facts, cv_info = video_cv.facts(frames, times)

    prompt = question
    if facts:
        prompt = FACTS_HEAD + "\n" + "\n".join("- " + f for f in facts) + "\n\nQuestion: " + question
    steps = o["video_prompt"] == "steps"
    if steps:
        prompt += "\n\n" + STEPS

    if o["video_input"] == "images":
        content = []
        for i, im in zip(idx, ims):
            content += [{"type": "text", "text": f"Frame at {times[i] - times[0]:.1f} s:"},
                        {"type": "image", "image": im}]
    else:
        content = [{"type": "video", "video": ims}]
    content.append({"type": "text", "text": prompt})
    # frames_indices index the decoded list, so its rate makes the prompt timestamps real seconds.
    dec_fps = (len(times) - 1) / (times[-1] - times[0]) if times[-1] > times[0] else 1.0
    pk = {"do_sample_frames": False,
          "video_metadata": [{"fps": dec_fps, "frames_indices": idx, "total_num_frames": len(times),
                              "duration": times[-1] - times[0]}]}

    system = SYSTEM_SENTENCE if o["video_style"] == "sentence" else SYSTEM
    max_new = 200 if steps else 64
    if o["video_model"] == "cosmos":
        t = time.perf_counter()
        cm = eng.gpu_model("cosmos", cosmos_loader)
        swap_s = time.perf_counter() - t
        text, info = cosmos_chat(cm, content, system, max(max_new, 384), pk)
        info["swap_s"] = round(swap_s, 2)
    elif o["video_resample"] == "1":
        text, info = eng.vlm.chat(content, system, max_new_tokens=max_new)
    else:
        text, info = qwen_chat(eng.vlm, content, system, max_new, pk)
    raw = text
    if steps:
        text = final_line(text)
    if o.get("video_debug") == "1":
        print(f"  [video] frames={len(ims)} cv={cv_info} tokens={info.get('input_tokens')} swap_s={info.get('swap_s')} "
              f"facts={facts} raw={raw!r}", flush=True)
    return text, {**info, "route": "video", "frames": len(ims), "cv_facts": len(facts),
                  "synthetic": cv_info.get("synthetic")}
