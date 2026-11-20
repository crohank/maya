"""Draw the saved detector tracks onto one frame of a clip (side-coloured boxes with labels).

  python draw_tracks_frame.py <clip.mp4> <tracks.jsonl> <time_s> <out.png>

Example (the London boxes image):
  python draw_tracks_frame.py ~/Downloads/<london clip>.mp4 results/perception/london_walking.jsonl 4.0 \
      results/perception/london_boxes_t4.png
"""
import json
import sys

import av
from PIL import ImageDraw, ImageFont

COL = {"left": (255, 170, 0), "ahead": (255, 40, 40), "right": (0, 200, 255)}


def main(src, tracks_path, t_want, out):
    rows = [json.loads(l) for l in open(tracks_path)]
    row = min(rows, key=lambda r: abs(r["t"] - t_want))
    with av.open(src) as c:
        for f in c.decode(video=0):
            if f.time >= row["t"]:
                im = f.to_image()
                break
    im = im.resize((im.width * 2, im.height * 2))
    W, H = im.size
    d = ImageDraw.Draw(im)
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 15)
    for tr in row["tracks"]:
        x1, y1, x2, y2 = tr["box"]
        b = (x1 * W, y1 * H, x2 * W, y2 * H)
        c = COL.get(tr["side"], (255, 255, 255))
        d.rectangle(b, outline=c, width=3)
        ttc = f" ttc {tr['ttc_s']:.1f}s" if tr.get("ttc_s") else ""
        lab = f"#{tr['id']} {tr['cls']} {tr['side']} {tr['motion']}{ttc}"
        d.rectangle((b[0], b[1] - 19, b[0] + d.textlength(lab, font=font) + 6, b[1]), fill=c)
        d.text((b[0] + 3, b[1] - 18), lab, fill=(0, 0, 0), font=font)
    d.rectangle((0, 0, 330, 26), fill=(0, 0, 0))
    d.text((8, 4), f"t = {row['t']:.2f} s   {len(row['tracks'])} tracked boxes", fill=(255, 255, 255), font=font)
    im.save(out)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4])
