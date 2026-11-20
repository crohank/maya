import re, time, torch, av
from PIL import Image, ImageDraw, ImageFont
from transformers import AutoModelForImageTextToText, AutoProcessor

SRC = "/Users/zyrus/Downloads/bicycle-ride-in-london-canary-wharf-jubilee-plaza-and-reuters-plaza.mp4"
BOX = """I am blind and I am walking. This photo comes from a phone camera on my chest, facing where I walk. Please be my eyes.

Find everything near me, within about 5 steps, that I could walk into:
- people and vehicles
- obstacles on the ground: signs, A-frame boards, kiosks, bins, poles, bollards, benches, planters, steps, curbs
Ignore buildings, the sky and anything far away.

Give one entry per object. Coordinates are 0 to 1000 (x from the left edge, y from the top edge).
Reply with JSON only: a list of objects, each with "label" (text) and "bbox_2d" (four numbers: x1, y1, x2, y2)."""
GUIDE = """I am blind and I am walking. The video comes from a phone camera on my chest, facing where I walk. The last frame is now. Please be my eyes and guide me for the next few steps.

Give one instruction with a number of steps, for example "2 steps right", "keep straight 4 steps", "1 step left, then straight", "slow down" or "stop". Then say why in one short sentence, naming the person or object that matters, where it is, and how many steps away it is.
Answer in this format:
Instruction: ...
Reason: ..."""
font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 13)

def frames(t0, t1, fps=4):
    out, want = [], t0
    with av.open(SRC) as c:
        for f in c.decode(video=0):
            if f.time > t1 + 1e-6:
                break
            if f.time + 1e-6 >= want:
                out.append((f.time, f.to_image().convert("RGB"))); want += 1 / fps
    return out

mid = "nvidia/Cosmos3-Edge"
proc = AutoProcessor.from_pretrained(mid)
model = AutoModelForImageTextToText.from_pretrained(mid, dtype=torch.bfloat16).to("mps").eval()

def run(content, max_new, **kw):
    x = proc.apply_chat_template([{"role": "user", "content": content}], add_generation_prompt=True,
                                 tokenize=True, return_dict=True, return_tensors="pt", enable_thinking=False, **kw).to("mps")
    t = time.perf_counter()
    with torch.inference_mode():
        out = model.generate(**x, max_new_tokens=max_new, do_sample=False, repetition_penalty=1.1)
    txt = proc.decode(out[0][x["input_ids"].shape[-1]:], skip_special_tokens=True).split("</think>")[-1].strip()
    return txt, time.perf_counter() - t

for n, t0, t1 in [("w1", 2.0, 4.0), ("w2", 8.0, 10.0), ("w3", 15.0, 17.0)]:
    fr = frames(t0, t1)
    # 9-frame sheet for judging
    sheet = Image.new("RGB", (384 * 3, 216 * 3))
    for i, (t, im) in enumerate(fr[:9]):
        th = im.resize((384, 216)); ImageDraw.Draw(th).text((6, 4), f"{t:.2f}s", fill=(255, 255, 0), font=font)
        sheet.paste(th, (384 * (i % 3), 216 * (i // 3)))
    sheet.save(f"judge_{n}.png")
    last = fr[-1][1]
    boxes_txt, bt = run([{"type": "image", "image": last}, {"type": "text", "text": BOX}], 512)
    guide_txt, gt = run([{"type": "video", "path": f"walk_{n}_4fps.mp4"}, {"type": "text", "text": GUIDE}], 96,
                        processor_kwargs={"fps": 4})
    im = last.copy(); W, H = im.size; d = ImageDraw.Draw(im)
    n_b = 0
    for chunk in re.findall(r"\{[^{}]*\}", boxes_txt):
        b = re.search(r"\[\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\]", chunk)
        if not b: continue
        lab = (re.search(r'"label"\s*:\s*"([^"]+)"', chunk) or [None, "?"])[1]
        x1, y1, x2, y2 = (int(v) * s / 1000 for v, s in zip(b.groups(), (W, H, W, H)))
        cx = (x1 + x2) / 2 / W
        c = (255, 140, 0) if cx < 0.42 else (0, 120, 255) if cx > 0.58 else (230, 0, 0)
        d.rectangle((x1, y1, x2, y2), outline=c, width=3)
        d.rectangle((x1, y1 - 16, x1 + d.textlength(lab, font=font) + 6, y1), fill=c)
        d.text((x1 + 3, y1 - 15), lab, fill=(0, 0, 0), font=font); n_b += 1
    d.rectangle((0, H - 60, W, H), fill=(0, 0, 0))
    for i, line in enumerate(guide_txt.splitlines()[:2]):
        d.text((8, H - 54 + 24 * i), line[:110], fill=(255, 255, 255), font=font)
    im.save(f"guide_{n}.png")
    print(f"=== {n} (video {t0:.0f}-{t1:.0f} s)\nboxes: {n_b} ({bt:.1f} s)\n{boxes_txt[:900]}\nguide ({gt:.1f} s):\n{guide_txt}\n", flush=True)
