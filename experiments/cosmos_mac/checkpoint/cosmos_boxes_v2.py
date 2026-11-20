import json, re, time, torch, av
from PIL import Image, ImageDraw, ImageFont
from transformers import AutoModelForImageTextToText, AutoProcessor

SRC = "/Users/zyrus/Downloads/bicycle-ride-in-london-canary-wharf-jubilee-plaza-and-reuters-plaza.mp4"
HEAD = "I am blind and I am walking. This photo comes from a phone camera on my chest, facing where I walk. Please be my eyes.\n\n"
P1 = HEAD + """Find everything near me, within about 5 steps, that I could walk into:
- people and vehicles
- obstacles on the ground: signs, A-frame boards, kiosks, bins, poles, bollards, benches, planters, steps, curbs
Ignore buildings, the sky and anything far away.

Give one entry per object. Coordinates are 0 to 1000 (x from the left edge, y from the top edge).
Reply with JSON only. Example:
[{"label": "person", "bbox_2d": [180, 510, 290, 940], "side": "left", "steps_away": 2},
 {"label": "A-frame sign", "bbox_2d": [170, 580, 290, 840], "side": "left", "steps_away": 3}]"""
P2 = HEAD + """Find every obstacle on the ground near me, within about 5 steps: signs, A-frame boards, kiosks, bins, poles, bollards, benches, planters, steps, curbs. Do not include people. Ignore buildings, the sky and anything far away.

Give one entry per object. Coordinates are 0 to 1000 (x from the left edge, y from the top edge).
Reply with JSON only. Example:
[{"label": "bin", "bbox_2d": [640, 520, 720, 650], "side": "right", "steps_away": 4}]"""
VARIANTS = [("P1", P1, dict(do_sample=True), True),
            ("P2", P2, dict(do_sample=True), True),
            ("P3", P1, dict(do_sample=False, repetition_penalty=1.1), False)]
COL = {"left": (255, 140, 0), "ahead": (230, 0, 0), "right": (0, 120, 255)}
font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 13)

def frame_at(t):
    with av.open(SRC) as c:
        for f in c.decode(video=0):
            if f.time + 1e-6 >= t:
                return f.to_image().convert("RGB")

def objects(text):
    """Tolerant: each {...} chunk -> label, first 4-number list, side, steps."""
    objs = []
    for chunk in re.findall(r"\{[^{}]*\}", text):
        b = re.search(r"\[\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\]", chunk)
        if not b:
            continue
        g = lambda k: (re.search(rf'"{k}"\s*:\s*"?([^",}}]+)"?', chunk) or [None, None])[1]
        objs.append(dict(label=g("label"), box=tuple(map(int, b.groups())), side=g("side"), steps=g("steps_away")))
    return objs

def clean_json(text):
    m = re.findall(r"\[\s*\{.*\}\s*\]", text, re.S)
    try:
        json.loads(m[-1]); return True
    except Exception:
        return False

frames = {n: frame_at(t) for n, t in [("w1", 4.0), ("w2", 10.0), ("w3", 17.0)]}
mid = "nvidia/Cosmos3-Edge"
proc = AutoProcessor.from_pretrained(mid)
model = AutoModelForImageTextToText.from_pretrained(mid, dtype=torch.bfloat16).to("mps").eval()
for vname, prompt, gen, think in VARIANTS:
    panels = []
    for n, im0 in frames.items():
        im = im0.copy()
        msgs = [{"role": "user", "content": [{"type": "image", "image": im0}, {"type": "text", "text": prompt}]}]
        x = proc.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True, return_dict=True,
                                     return_tensors="pt", enable_thinking=think).to("mps")
        torch.manual_seed(0)
        t = time.perf_counter()
        with torch.inference_mode():
            out = model.generate(**x, max_new_tokens=4096, **gen)
        new = out[0][x["input_ids"].shape[-1]:]
        raw = proc.decode(new, skip_special_tokens=True)
        _, sep, answer = raw.rpartition("</think>")
        if not sep:
            answer = raw
        objs = objects(answer)
        print(f"=== {vname} {n}: {time.perf_counter() - t:.1f} s, {len(new)} tokens, think_closed={bool(sep)}, "
              f"valid_json={clean_json(answer)}, {len(objs)} boxes")
        for o in objs:
            print(f"   {o['label']!s:18} side={o['side']!s:6} steps={o['steps']!s:4} box={o['box']}")
        W, H = im.size
        d = ImageDraw.Draw(im)
        for o in objs:
            x1, y1, x2, y2 = (v * s / 1000 for v, s in zip(o["box"], (W, H, W, H)))
            c = COL.get((o["side"] or "").strip().lower(), (255, 230, 0))
            d.rectangle((x1, y1, x2, y2), outline=c, width=3)
            lab = f"{o['label']} {o['steps']}st"
            d.rectangle((x1, y1 - 16, x1 + d.textlength(lab, font=font) + 6, y1), fill=c)
            d.text((x1 + 3, y1 - 15), lab, fill=(0, 0, 0), font=font)
        d.rectangle((0, 0, 190, 22), fill=(0, 0, 0))
        d.text((6, 3), f"{vname}  {n}  {len(objs)} boxes", fill=(255, 255, 255), font=font)
        panels.append(im)
        print(flush=True)
    grid = Image.new("RGB", (768, 432 * 3))
    for i, p in enumerate(panels):
        grid.paste(p, (0, 432 * i))
    grid.save(f"boxes_{vname}.png")
