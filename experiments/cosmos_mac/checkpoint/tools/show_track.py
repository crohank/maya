"""Print one track's history and draw its box on the frame nearest a time (used to check the false 'pole').

  python show_track.py <clip.mp4> <tracks.jsonl> <track_id> <time_s> <out.png>

Example (track 102, the 'pole' on the building wall):
  python show_track.py ~/Downloads/<london clip>.mp4 results/perception/london_walking.jsonl 102 11.6 \
      results/live/london_cosmos_sim_short2/pole_track102.png
"""
import json
import sys

import av
from PIL import ImageDraw, ImageFont


def main(src, tracks_path, tid, t_want, out):
    rows = [json.loads(l) for l in open(tracks_path)]
    hits = [(f["t"], tr) for f in rows for tr in f["tracks"] if tr["id"] == tid]
    print(f"track {tid}: {len(hits)} frames, {hits[0][0]} to {hits[-1][0]} s")
    for t, tr in hits[::4]:
        print(round(t, 2), tr["cls"], tr["side"], tr["motion"], tr["ttc_s"], [round(v, 2) for v in tr["box"]],
              "conf", round(tr["conf"], 2))
    t, tr = min(hits, key=lambda h: abs(h[0] - t_want))
    with av.open(src) as c:
        for f in c.decode(video=0):
            if f.time >= t:
                im = f.to_image().convert("RGB")
                break
    W, H = im.size
    x1, y1, x2, y2 = tr["box"]
    d = ImageDraw.Draw(im)
    d.rectangle((x1 * W, y1 * H, x2 * W, y2 * H), outline=(0, 255, 255), width=4)
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 16)
    d.text((x1 * W - 60, y1 * H - 20), f"track {tid} '{tr['cls']}' t={t:.2f}s", fill=(0, 255, 255), font=font)
    im.save(out)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]), float(sys.argv[4]), sys.argv[5])
