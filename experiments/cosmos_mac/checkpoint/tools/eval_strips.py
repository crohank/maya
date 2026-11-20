"""Frame strips for hand-grading a simulated walk run: one row per Cosmos call.

Each row shows 3 frames: 2 s before the request, at the request, and when the answer would be spoken.
Detector boxes are coloured by side, and the box of the track the call was about is drawn thick.

  python eval_strips.py <clip.mp4> <tracks.jsonl> <run_dir_with_log.csv> <out_dir> [--min-conf 0.7] [--only describe,last]
"""
import argparse
import csv
import json
import os

import av
from PIL import Image, ImageDraw, ImageFont

COL = {"left": (255, 140, 0), "ahead": (230, 0, 0), "right": (0, 120, 255)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clip")
    ap.add_argument("tracks")
    ap.add_argument("run_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--min-conf", type=float, default=0.0, help="hide boxes below this detector confidence")
    ap.add_argument("--only", default="", help="'describe,last' = describe calls plus the last call, on one sheet")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    log = list(csv.DictReader(open(os.path.join(a.run_dir, "log.csv"))))
    rows = [json.loads(l) for l in open(a.tracks)]
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 16)
    frames = []
    with av.open(a.clip) as c:
        for f in c.decode(video=0):
            frames.append((f.time, f.to_image().convert("RGB")))

    def at(t, focus):
        t = min(t, frames[-1][0])
        im = min(frames, key=lambda x: abs(x[0] - t))[1].copy()
        W, H = im.size
        d = ImageDraw.Draw(im)
        fr = min(rows, key=lambda r: abs(r["t"] - t))
        for tr in fr["tracks"]:
            x1, y1, x2, y2 = tr["box"]
            if y2 - y1 < 0.12 or tr["conf"] < a.min_conf:
                continue
            d.rectangle((x1 * W, y1 * H, x2 * W, y2 * H), outline=COL.get(tr["side"], (255, 255, 0)),
                        width=7 if str(tr["id"]) == focus else 2)
        d.rectangle((0, 0, 150, 24), fill=(0, 0, 0))
        d.text((6, 3), f"t={t:.2f}s", fill=(255, 255, 0), font=font)
        return im.resize((512, 288))

    def row_img(i, r):
        req, sp = float(r["request_t"]), float(r["speech_start"])
        strip = Image.new("RGB", (512 * 3, 288 + 30), (0, 0, 0))
        for j, t in enumerate([req - 2, req, sp]):
            strip.paste(at(t, r["track"]), (512 * j, 30))
        ImageDraw.Draw(strip).text(
            (6, 6), f"call {i + 1} {r['mode']} asked {req:.1f}s -> spoken {sp:.1f}s | {r['trigger']} | "
                    f"says: {r['spoken'][:80]}", fill=(255, 255, 255), font=font)
        return strip

    if a.only:
        picks = [i for i, r in enumerate(log) if r["mode"] == "DESCRIBE"] + [len(log) - 1]
        sheet = Image.new("RGB", (1536, 318 * len(picks)), (0, 0, 0))
        for k, i in enumerate(picks):
            sheet.paste(row_img(i, log[i]), (0, 318 * k))
        sheet.save(os.path.join(a.out_dir, "eval_sheet.png"))
    else:
        for i, r in enumerate(log):
            row_img(i, r).save(os.path.join(a.out_dir, f"eval_call{i + 1}.png"))
    print("wrote", a.out_dir)


if __name__ == "__main__":
    main()
