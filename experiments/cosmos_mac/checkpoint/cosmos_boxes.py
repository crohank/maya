import json, re, time, torch, av
from PIL import Image, ImageDraw, ImageFont
from transformers import AutoModelForImageTextToText, AutoProcessor

SRC = "/Users/zyrus/Downloads/bicycle-ride-in-london-canary-wharf-jubilee-plaza-and-reuters-plaza.mp4"
PROMPT = """I am blind and I am walking. This photo comes from a phone camera on my chest, facing where I walk. Please be my eyes.

Find every person, vehicle and obstacle near me, within about 5 steps (a sign, bin, pole, bench, step or curb counts as an obstacle). Ignore buildings, the sky and anything far away.

Reply with JSON only, a list like:
[{"label": "person", "bbox_2d": [x1, y1, x2, y2], "side": "left|ahead|right", "steps_away": number}]
bbox_2d is in pixels of this image (x from the left edge, y from the top edge)."""
COL = {"left": (255, 140, 0), "ahead": (230, 0, 0), "right": (0, 120, 255)}
font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 13)

def frame_at(t):
    with av.open(SRC) as c:
        for f in c.decode(video=0):
            if f.time + 1e-6 >= t:
                return f.to_image().convert("RGB")

def parse(text):
    m = re.findall(r"\[\s*\{.*?\}\s*\]", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m[-1])
    except Exception:
        return None

mid = "nvidia/Cosmos3-Edge"
proc = AutoProcessor.from_pretrained(mid)
model = AutoModelForImageTextToText.from_pretrained(mid, dtype=torch.bfloat16).to("mps").eval()
for n, t_end in [("w1", 4.0), ("w2", 10.0), ("w3", 17.0)]:
    im = frame_at(t_end)
    msgs = [{"role": "user", "content": [{"type": "image", "image": im}, {"type": "text", "text": PROMPT}]}]
    x = proc.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True, return_dict=True,
                                 return_tensors="pt").to("mps")
    torch.manual_seed(0)
    t = time.perf_counter()
    with torch.inference_mode():
        out = model.generate(**x, max_new_tokens=4096, do_sample=True)
    new = out[0][x["input_ids"].shape[-1]:]
    raw = proc.decode(new, skip_special_tokens=True)
    think, sep, answer = raw.rpartition("</think>")
    if not sep:
        answer = raw
    boxes = parse(answer) or parse(raw)
    print(f"=== {n} (frame at {t_end} s, image {im.size}) {time.perf_counter() - t:.1f} s, {len(new)} tokens, think_tag={bool(sep)}")
    print("ANSWER:", answer.strip()[-1500:], flush=True)
    d = ImageDraw.Draw(im)
    for b in boxes or []:
        try:
            x1, y1, x2, y2 = [float(v) for v in b["bbox_2d"]]
        except Exception:
            continue
        c = COL.get(str(b.get("side", "")).lower(), (255, 255, 0))
        d.rectangle((x1, y1, x2, y2), outline=c, width=3)
        lab = f"{b.get('label')} {b.get('side')} {b.get('steps_away')}st"
        d.rectangle((x1, y1 - 16, x1 + d.textlength(lab, font=font) + 6, y1), fill=c)
        d.text((x1 + 3, y1 - 15), lab, fill=(0, 0, 0), font=font)
    im.save(f"cosmos_boxes_{n}.png")
    print(f"drew {len(boxes or [])} boxes -> cosmos_boxes_{n}.png\n", flush=True)
