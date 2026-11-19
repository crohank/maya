"""Smoke test for Cosmos3-Edge reasoner (NF4) on an 8 GB GPU.

Run inside the cosmos-tf container:
  python scripts/smoke_cosmos.py                      # synthetic image + video
  python scripts/smoke_cosmos.py --video clip.mp4 --question "..."
Prints load time, VRAM, answers, and latency per request.
"""
import argparse
import os
import subprocess
import tempfile
import time

import torch
from PIL import Image, ImageDraw
from transformers import AutoModelForImageTextToText, AutoProcessor

MODEL_ID = os.environ.get("COSMOS_MODEL", "ubr-physical-ai/Cosmos3-Edge-NF4-bnb")
# The NF4 repo ships no video_preprocessor_config.json; the base repo does.
PROCESSOR_ID = os.environ.get("COSMOS_PROCESSOR", "nvidia/Cosmos3-Edge")
FPS = 4
MAX_FRAMES = 40

SYSTEM = (
    "You describe scenes for a person with low vision. Use positional words "
    "(left, right, ahead). Answer in at most two sentences. Never say it is safe "
    "to cross or tell the person what physical action to take."
)


def gib(n):
    return f"{n / 2**30:.2f} GiB"


def make_test_image(path):
    img = Image.new("RGB", (640, 480), "skyblue")
    d = ImageDraw.Draw(img)
    d.rectangle([150, 180, 490, 360], fill="yellow", outline="black", width=4)
    d.text((200, 220), "BUS 42  DOWNTOWN", fill="black", font_size=36)
    d.rectangle([0, 400, 640, 480], fill="gray")
    img.save(path)


def make_test_video(path):
    """3 s clip: red box (car) moving left to right over a gray road."""
    with tempfile.TemporaryDirectory() as td:
        for i in range(12 * 3):
            img = Image.new("RGB", (640, 360), "skyblue")
            d = ImageDraw.Draw(img)
            d.rectangle([0, 220, 640, 360], fill="gray")
            x = 20 + i * 16
            d.rectangle([x, 240, x + 120, 300], fill="red", outline="black", width=3)
            img.save(f"{td}/f{i:03d}.png")
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-framerate", "12",
             "-i", f"{td}/f%03d.png", "-pix_fmt", "yuv420p", path],
            check=True,
        )


def sample_frames(video, fps=FPS, max_frames=MAX_FRAMES):
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(
            ["ffmpeg", "-loglevel", "error", "-i", video, "-vf", f"fps={fps}",
             f"{td}/f%04d.jpg"],
            check=True,
        )
        files = sorted(os.listdir(td))[-max_frames:]
        return [Image.open(f"{td}/{f}").convert("RGB") for f in files]


def generate(model, proc, content, max_new_tokens=128):
    messages = [
        {"role": "system", "content": [{"type": "text", "text": SYSTEM}]},
        {"role": "user", "content": content},
    ]
    inputs = proc.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=True, return_dict=True,
        return_tensors="pt", enable_thinking=False,
    ).to(model.device)
    torch.cuda.reset_peak_memory_stats()
    t = time.perf_counter()
    with torch.inference_mode():
        out = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    dt = time.perf_counter() - t
    text = proc.decode(out[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
    return text.strip(), dt, inputs["input_ids"].shape[-1]


def report(label, text, dt, n_in):
    print(f"\n[{label}] {dt:.2f}s, {n_in} input tokens, peak {gib(torch.cuda.max_memory_allocated())}")
    print(f"  -> {text}")


def ask_video(model, proc, video, question):
    try:
        text, dt, n = generate(model, proc, [
            {"type": "video", "path": video},
            {"type": "text", "text": question},
        ])
        report("video native", text, dt, n)
        return
    except Exception as e:  # processor may not accept video for this model
        print(f"\n[video native] failed: {type(e).__name__}: {str(e)[:300]}")
    frames = sample_frames(video)
    content = [{"type": "image", "image": f} for f in frames]
    content.append({"type": "text", "text": f"These are {len(frames)} frames at {FPS} fps, in order. {question}"})
    text, dt, n = generate(model, proc, content)
    report(f"video as {len(frames)} frames", text, dt, n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video")
    ap.add_argument("--image")
    ap.add_argument("--question", default="Describe what is happening, especially any vehicles and which way they move.")
    args = ap.parse_args()

    print(f"GPU: {torch.cuda.get_device_name(0)}, total {gib(torch.cuda.get_device_properties(0).total_memory)}")
    t = time.perf_counter()
    proc = AutoProcessor.from_pretrained(PROCESSOR_ID)
    model = AutoModelForImageTextToText.from_pretrained(MODEL_ID, device_map="cuda")
    model.eval()
    load = time.perf_counter() - t
    import bitsandbytes as bnb
    n4 = sum(isinstance(m, bnb.nn.Linear4bit) for m in model.modules())
    print(f"Loaded in {load:.1f}s, Linear4bit modules: {n4} (card expects 169), "
          f"allocated {gib(torch.cuda.memory_allocated())}")

    with tempfile.TemporaryDirectory() as td:
        img = args.image or f"{td}/bus.png"
        if not args.image:
            make_test_image(img)
        text, dt, n = generate(model, proc, [
            {"type": "image", "image": Image.open(img).convert("RGB")},
            {"type": "text", "text": "What does the sign say?"},
        ])
        report("image", text, dt, n)

        vid = args.video or f"{td}/car.mp4"
        if not args.video:
            make_test_video(vid)
        ask_video(model, proc, vid, args.question)


if __name__ == "__main__":
    main()
