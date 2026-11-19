"""Turn results/image_compare.csv into a video: each test image on screen, each
model's answer as a caption and spoken by Piper, one after the other.

Run inside the cosmos-tf container:
  python scripts/render_image_compare.py
Writes results/image_compare.mp4.
"""
import csv
import re
import subprocess
import tempfile
import wave
from pathlib import Path

from huggingface_hub import hf_hub_download
from PIL import Image, ImageDraw, ImageFont

VOICE = "en/en_US/lessac/medium/en_US-lessac-medium.onnx"
W, H, IMG_H = 1280, 960, 720
LABEL = {"cosmos3-edge-nf4": "Cosmos3-Edge NF4", "qwen3vl-4b": "Qwen3-VL-4B NF4",
         "qwen3vl-8b": "Qwen3-VL-8B NF4"}


def spoken_text(answer, limit=220):
    """Collapse line breaks and cut a looping answer down to something sayable."""
    text = re.sub(r"\s+", " ", answer).strip()
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "..."


def wrap(draw, text, font, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + [line]


def frame(image_path, header, caption, verdict, out):
    canvas = Image.new("RGB", (W, H), (16, 16, 16))
    img = Image.open(image_path).convert("RGB")
    img.thumbnail((W, IMG_H))
    canvas.paste(img, ((W - img.width) // 2, (IMG_H - img.height) // 2))
    d = ImageDraw.Draw(canvas)
    color = (120, 220, 140) if verdict == "True" else (240, 120, 110)
    d.text((24, IMG_H + 12), header, fill=color, font=ImageFont.load_default(size=26))
    font = ImageFont.load_default(size=28)
    for i, line in enumerate(wrap(d, caption, font, W - 48)[:5]):
        d.text((24, IMG_H + 52 + i * 34), line, fill="white", font=font)
    canvas.save(out)


def main():
    from piper import PiperVoice
    voice = PiperVoice.load(hf_hub_download("rhasspy/piper-voices", VOICE))
    hf_hub_download("rhasspy/piper-voices", VOICE + ".json")
    rows = list(csv.DictReader(open("results/image_compare.csv")))
    order = list(dict.fromkeys(r["model"] for r in rows))
    items = list(dict.fromkeys((r["image"], r["question"]) for r in rows))

    with tempfile.TemporaryDirectory() as td:
        segments = []
        for i, (image, question) in enumerate(items):
            for model in order:
                r = next(x for x in rows if x["model"] == model and x["image"] == image
                         and x["question"] == question)
                text = spoken_text(r["answer"])
                wav = f"{td}/{len(segments):03d}.wav"
                with wave.open(wav, "wb") as w:
                    voice.synthesize_wav(f"{LABEL[model]}. {text}", w)
                png = f"{td}/{len(segments):03d}.png"
                verdict = "pass" if r["passed"] == "True" else "fail"
                frame(f"test_images/{image}",
                      f"{i + 1}/{len(items)}  Q: {question}   |   {LABEL[model]}: {verdict}, "
                      f"{float(r['latency_s']):.1f}s", text, r["passed"], png)
                seg = f"{td}/{len(segments):03d}.mp4"
                subprocess.run(
                    ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", png, "-i", wav,
                     "-af", "apad=pad_dur=0.6", "-shortest", "-r", "10", "-c:v", "libx264",
                     "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", seg],
                    check=True,
                )
                segments.append(seg)
        listing = f"{td}/list.txt"
        Path(listing).write_text("".join(f"file '{s}'\n" for s in segments))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                        "-i", listing, "-c", "copy", "results/image_compare.mp4"], check=True)
    print("wrote results/image_compare.mp4")


if __name__ == "__main__":
    main()
