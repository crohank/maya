"""Draw detector boxes on walk-window frames, colored by side, only near boxes (height >= MIN_H)."""
import json, sys
import av
from PIL import Image, ImageDraw, ImageFont
REPO = "/Users/zyrus/Documents/Projects/maya-main"
SRC = "/Users/zyrus/Downloads/bicycle-ride-in-london-canary-wharf-jubilee-plaza-and-reuters-plaza.mp4"
COL = {"left": (255, 140, 0), "ahead": (230, 0, 0), "right": (0, 120, 255)}  # orange, red, blue
MIN_H = 0.15
rows = [json.loads(l) for l in open(f"{REPO}/results/perception/london_walking.jsonl")]
font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 14)

def annotate(im, t):
    r = min(rows, key=lambda r: abs(r["t"] - t))
    d = ImageDraw.Draw(im)
    W, H = im.size
    for tr in r["tracks"]:
        x1, y1, x2, y2 = tr["box"]
        if y2 - y1 < MIN_H:
            continue
        c = COL[tr["side"]]
        d.rectangle((x1 * W, y1 * H, x2 * W, y2 * H), outline=c, width=4)
    return im

def frames(t0, t1, fps=4):
    out, want = [], t0
    with av.open(SRC) as c:
        for f in c.decode(video=0):
            if f.time + 1e-6 >= want and f.time <= t1 + 1e-6:
                out.append((f.time, annotate(f.to_image(), f.time)))
                want += 1 / fps
            if f.time > t1:
                break
    return out

if __name__ == "__main__":
    t0, t1, name = float(sys.argv[1]), float(sys.argv[2]), sys.argv[3]
    fr = frames(t0, t1)
    fr[-1][1].save(f"{name}_last_annotated.png")
    print(len(fr), "frames", [round(t, 2) for t, _ in fr])
