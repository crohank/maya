"""Crosswalk stripes ahead, from pixels only (no model): the curb-approach cue for a
Cosmos-only walk stack. Cosmos3-Edge missed the approach on every labelled corner
(results/scene_cosmos_edge.md), Qwen3-VL is out of this branch's stack.

A painted crosswalk seen from the sidewalk is a stack of bright, low-saturation,
roughly horizontal bands across the lower half of the frame. Per frame: in the band
between y0 and y1 (fractions of height), mark pixels with V > V_MIN and S < S_MAX, take
the bright fraction of each row, smooth it, and count runs of rows above ROW_MIN that
span at least WIDTH_MIN of the row width. bands >= MIN_BANDS means stripes ahead;
`nearest` is the lowest band's bottom edge (1.0 = at the walker's feet).

  python experiments/cosmos_combined/stripes.py <video> [fps]   -> results/scene/<stem>_stripes.jsonl
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

Y0, Y1 = 0.45, 1.0
X0, X1 = 0.0, 1.0   # columns searched; the walking lane is about 0.25 to 0.75 (cosmos_path_test.py)
V_MIN, S_MAX = 170, 45
ROW_MIN = 0.32
GAP_MAX = 0.25
DARK_V = 175
MIN_BANDS = 3


def bands(bgr, row_min=ROW_MIN, gap_max=GAP_MAX, dark_v=DARK_V):
    h, w = bgr.shape[:2]
    roi = bgr[int(h * Y0):int(h * Y1), int(w * X0):int(w * X1)]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    bright = (hsv[..., 2] > V_MIN) & (hsv[..., 1] < S_MAX)
    frac = np.convolve(bright.mean(axis=1), np.ones(3) / 3, mode="same")
    # median V of the non-bright pixels per row: asphalt between stripes is dark,
    # concrete sidewalk between slab joints is not
    v = hsv[..., 2].astype(float)
    dark = np.array([np.median(v[i][~bright[i]]) if (~bright[i]).any() else 255 for i in range(len(v))])
    runs, start, gap_ok = [], None, False
    for i, val in enumerate(list(frac) + [0.0]):
        if val > row_min and start is None:
            start = i
        elif val <= row_min and start is not None:
            if i - start >= 2:
                runs.append((start, i))
            start = None
    # keep bands separated by a real gap: low bright fraction and dark ground
    kept = []
    for a, b in runs:
        if kept:
            g = slice(kept[-1][1], a)
            if not (len(frac[g]) and frac[g].min() < gap_max and np.median(dark[g]) < dark_v):
                continue
        kept.append((a, b))
    n = len(kept)
    nearest = (Y0 + (kept[-1][1] / len(frac)) * (Y1 - Y0)) if kept else None
    return n, nearest


def main():
    global X0, X1
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("fps", nargs="?", type=float, default=2.0)
    ap.add_argument("--x0", type=float, default=X0)
    ap.add_argument("--x1", type=float, default=X1)
    ap.add_argument("--tag", default="stripes")
    a = ap.parse_args()
    video, fps_out, X0, X1 = a.video, a.fps, a.x0, a.x1
    cap = cv2.VideoCapture(video)
    fps, n = cap.get(cv2.CAP_PROP_FPS), int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    out = Path("results/scene") / f"{Path(video).stem}_{a.tag}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        t = 0.0
        while int(t * fps) < n:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
            ok, bgr = cap.read()
            if not ok:
                break
            k, near = bands(bgr)
            f.write(json.dumps(dict(t=round(t, 2), bands=k, nearest=round(near, 3) if near else None,
                                    stripes=k >= MIN_BANDS)) + "\n")
            t += 1.0 / fps_out
    print("wrote", out)


if __name__ == "__main__":
    main()
