"""Image reading test: Cosmos3-Edge (NF4) vs Qwen3-VL (NF4) on the same items.

Items: 3 real frames from test_videos/ (ground truth read by hand) and 7
synthetic images with known text, generated into test_images/ on first run.
Scoring rule: an answer passes when every required key appears in it
(case-insensitive; a key "a|b" accepts either). Key recall is reported too.

Run inside the cosmos-tf container:
  python scripts/compare_image_models.py                # both models
  python scripts/compare_image_models.py --models qwen3vl-4b
Writes results/image_compare.csv and results/image_compare.md.
"""
import argparse
import csv
import gc
import random
import re
import statistics
import time
from pathlib import Path

import torch
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from transformers import AutoModelForImageTextToText, AutoProcessor, BitsAndBytesConfig

IMG_DIR = Path("test_images")
SYSTEM = (
    "You help a person with low vision. Read any text exactly as written, "
    "including numbers. Answer in at most two sentences."
)

MODELS = {
    # Pre-quantized; its config carries the NF4 recipe.
    "cosmos3-edge-nf4": dict(id="ubr-physical-ai/Cosmos3-Edge-NF4-bnb", quant=None),
    # BF16 checkpoints quantized on load. Vision tower and lm_head stay BF16,
    # same split as the Cosmos NF4 build.
    "qwen3vl-4b": dict(id="Qwen/Qwen3-VL-4B-Instruct", quant="nf4", patch_conv3d=True),
    "qwen3vl-8b": dict(id="Qwen/Qwen3-VL-8B-Instruct", quant="nf4", patch_conv3d=True),
}

ITEMS = [
    ("real_kiosk_sign.png", "What do the purple signs say?",
     ["kiosk opens", "2:58", "one minute"]),
    ("real_parking_sign.png", "Read the signs in this image.",
     ["303", "parking", "wegmans", "exit only"]),
    ("real_lunch_sign.png", "What does the white sign on the right say?",
     ["monday", "wednesday", "1-2|1 - 2|1 to 2"]),
    ("real_parking_sign.png", "Is there a vehicle on the road? What is it and where?",
     ["truck|pickup|gmc", "black"]),
    ("syn_bus_sign.png", "What bus number and destination are shown?",
     ["m15", "south ferry"]),
    ("syn_slide.png", "Read this slide.",
     ["quarterly results", "12%", "3.1%", "4 engineers|four engineers"]),
    ("syn_whiteboard.png", "What does the whiteboard say?",
     ["dec 3|december 3", "214", "5-7|5 - 7|5 to 7"]),
    ("syn_medicine.png", "What is the dose, how often, and the daily limit?",
     ["200 mg|200mg", "4 to 6 hours|4-6 hours", "6 tablets|six tablets"]),
    ("syn_bar_chart.png", "Which bar is tallest and what is its value?",
     ["b", "7"]),
    ("syn_small_text.png", "What is the best-before date on this label?",
     ["2026-12-14|14 december 2026|december 14, 2026|12/14/2026"]),
]


def font(size):
    return ImageFont.load_default(size=size)


def make_synthetic():
    IMG_DIR.mkdir(exist_ok=True)
    rnd = random.Random(0)

    img = Image.new("RGB", (900, 300), (20, 20, 20))
    d = ImageDraw.Draw(img)
    d.rectangle([20, 40, 880, 260], fill=(5, 5, 5), outline=(80, 80, 80), width=6)
    d.text((60, 90), "M15", fill=(255, 150, 0), font=font(110))
    d.text((330, 80), "SELECT BUS", fill=(255, 150, 0), font=font(50))
    d.text((330, 150), "SOUTH FERRY", fill=(255, 150, 0), font=font(60))
    img.save(IMG_DIR / "syn_bus_sign.png")

    img = Image.new("RGB", (1280, 720), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 1280, 140], fill=(30, 60, 120))
    d.text((60, 35), "Quarterly Results", fill="white", font=font(70))
    for i, line in enumerate(["Revenue up 12%", "Churn down to 3.1%", "Hiring 4 engineers"]):
        d.text((90, 220 + i * 120), "• " + line, fill=(20, 20, 20), font=font(56))
    img.save(IMG_DIR / "syn_slide.png")

    img = Image.new("RGB", (1200, 800), (236, 238, 232))
    d = ImageDraw.Draw(img)
    d.rectangle([10, 10, 1190, 790], outline=(150, 150, 150), width=14)
    d.text((90, 160), "Exam: Dec 3, Room 214", fill=(20, 50, 160), font=font(80))
    d.text((90, 330), "Covers Ch. 5-7", fill=(20, 50, 160), font=font(80))
    d.text((90, 500), "Bring a calculator", fill=(170, 30, 30), font=font(64))
    img = img.rotate(3, expand=False, fillcolor=(236, 238, 232)).filter(ImageFilter.GaussianBlur(1.2))
    img.save(IMG_DIR / "syn_whiteboard.png")

    img = Image.new("RGB", (1000, 640), (250, 250, 245))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 1000, 120], fill=(200, 30, 40))
    d.text((40, 25), "IBUPROFEN 200 mg", fill="white", font=font(64))
    d.text((40, 180), "Directions:", fill="black", font=font(40))
    d.text((40, 250), "Take 1 tablet every 4 to 6 hours", fill="black", font=font(40))
    d.text((40, 320), "Do not exceed 6 tablets in 24 hours", fill="black", font=font(40))
    d.text((40, 420), "Keep out of reach of children", fill=(90, 90, 90), font=font(32))
    img.save(IMG_DIR / "syn_medicine.png")

    img = Image.new("RGB", (900, 600), "white")
    d = ImageDraw.Draw(img)
    d.line([100, 520, 820, 520], fill="black", width=4)
    d.line([100, 80, 100, 520], fill="black", width=4)
    for v in range(0, 9, 2):
        y = 520 - v * 50
        d.text((50, y - 15), str(v), fill="black", font=font(28))
    for i, (lab, val) in enumerate([("A", 3), ("B", 7), ("C", 5)]):
        x = 180 + i * 220
        d.rectangle([x, 520 - val * 50, x + 120, 520], fill=(60, 120, 200))
        d.text((x + 45, 535), lab, fill="black", font=font(36))
    d.text((300, 20), "Units sold (thousands)", fill="black", font=font(34))
    img.save(IMG_DIR / "syn_bar_chart.png")

    img = Image.new("RGB", (640, 480), (200, 190, 170))
    px = img.load()
    for _ in range(20000):
        x, y = rnd.randrange(640), rnd.randrange(480)
        g = rnd.randrange(150, 230)
        px[x, y] = (g, g - 10, g - 30)
    d = ImageDraw.Draw(img)
    d.rectangle([150, 170, 490, 300], fill=(245, 245, 240))
    d.text((165, 190), "NET WT 12 OZ (340 g)", fill=(60, 60, 60), font=font(18))
    d.text((165, 230), "Best before 2026-12-14", fill=(60, 60, 60), font=font(16))
    d.text((165, 262), "LOT 4471B", fill=(60, 60, 60), font=font(14))
    img = img.rotate(-6, expand=False, fillcolor=(200, 190, 170))
    img.save(IMG_DIR / "syn_small_text.png")


def normalize(s):
    s = s.lower().replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", s)


def score(answer, keys):
    a = normalize(answer)
    hits = [any(alt in a for alt in k.split("|")) for k in keys]
    return all(hits), sum(hits) / len(hits)


class Conv3dAsLinear(torch.nn.Module):
    """Patch-embed Conv3d whose kernel equals its stride is a plain matmul.

    On the RTX 5060 (sm_120), torch 2.9.0+cu128, Qwen3-VL's bf16 Conv3d patch
    embed took 14 to 17 s per 640x360 image, cuDNN on or off; one matmul over
    the same weights is equivalent (each patch is exactly one kernel window).
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


def load(spec):
    kwargs = dict(device_map="cuda")
    if spec["quant"] == "nf4":
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
            llm_int8_skip_modules=["model.visual", "lm_head"],
        )
        kwargs["dtype"] = torch.bfloat16
    proc = AutoProcessor.from_pretrained(spec["id"])
    model = AutoModelForImageTextToText.from_pretrained(spec["id"], **kwargs).eval()
    if spec.get("patch_conv3d"):
        patch_conv3d(model)
    return model, proc


def ask(model, proc, image, question, max_new_tokens):
    messages = [
        {"role": "system", "content": [{"type": "text", "text": SYSTEM}]},
        {"role": "user", "content": [
            {"type": "image", "image": image},
            {"type": "text", "text": question},
        ]},
    ]
    inputs = proc.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=True, return_dict=True,
        return_tensors="pt", enable_thinking=False,
    ).to(model.device)
    with torch.inference_mode():
        out = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    text = proc.decode(out[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
    return text.strip(), inputs["input_ids"].shape[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="cosmos3-edge-nf4,qwen3vl-4b")
    ap.add_argument("--max-new-tokens", type=int, default=96)
    args = ap.parse_args()

    make_synthetic()
    rows, summary = [], []
    for name in args.models.split(","):
        spec = MODELS[name]
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        t = time.perf_counter()
        model, proc = load(spec)
        load_s = time.perf_counter() - t
        import bitsandbytes as bnb
        n4 = [n for n, m in model.named_modules() if isinstance(m, bnb.nn.Linear4bit)]
        n4_visual = sum("visual" in n for n in n4)
        print(f"\n== {name}: loaded in {load_s:.1f}s, Linear4bit {len(n4)} "
              f"({n4_visual} in vision tower), allocated "
              f"{torch.cuda.memory_allocated() / 2**30:.2f} GiB", flush=True)

        ask(model, proc, Image.new("RGB", (64, 64)), "Hi", 4)  # warm-up
        lat = []
        for fname, question, keys in ITEMS:
            image = Image.open(IMG_DIR / fname).convert("RGB")
            t0 = time.perf_counter()
            answer, n_in = ask(model, proc, image, question, args.max_new_tokens)
            dt = time.perf_counter() - t0
            lat.append(dt)
            ok, recall = score(answer, keys)
            rows.append(dict(model=name, image=fname, question=question, keys=" ; ".join(keys),
                             passed=ok, key_recall=round(recall, 2), latency_s=round(dt, 2),
                             input_tokens=n_in, answer=answer))
            print(f"  [{'PASS' if ok else 'fail'} {recall:.2f}] {dt:5.2f}s {n_in:5d} tok  "
                  f"{fname}: {answer}", flush=True)
        mine = [r for r in rows if r["model"] == name]
        summary.append(dict(
            model=name, passed=sum(r["passed"] for r in mine), n=len(mine),
            recall=statistics.mean(r["key_recall"] for r in mine),
            median=statistics.median(lat), p90=sorted(lat)[int(0.9 * (len(lat) - 1))],
            peak=torch.cuda.max_memory_allocated() / 2**30, load_s=load_s,
        ))
        del model, proc
        gc.collect()
        torch.cuda.empty_cache()

    out = Path("results")
    out.mkdir(exist_ok=True)
    with open(out / "image_compare.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with open(out / "image_compare.md", "w") as f:
        f.write("# Image reading: Cosmos3-Edge vs Qwen3-VL\n\n")
        f.write("Rule: pass when every required key string appears in the answer "
                "(case-insensitive, alternatives separated by |). 10 items: 3 real "
                "frames from test_videos/, 7 synthetic with known text.\n\n")
        f.write("| Model | Passed | Mean key recall | Median latency | p90 latency | Peak VRAM | Load time |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for s in summary:
            f.write(f"| {s['model']} | {s['passed']}/{s['n']} | {s['recall']:.2f} | "
                    f"{s['median']:.2f}s | {s['p90']:.2f}s | {s['peak']:.2f} GiB | {s['load_s']:.1f}s |\n")
        f.write("\n| Model | Image | Pass | Answer |\n|---|---|---|---|\n")
        for r in rows:
            f.write(f"| {r['model']} | {r['image']} | {'yes' if r['passed'] else 'no'} | "
                    f"{r['answer'].replace('|', '/').replace(chr(10), ' ')} |\n")
    print("\n" + (out / "image_compare.md").read_text().split("\n| Model | Image")[0])


if __name__ == "__main__":
    main()
