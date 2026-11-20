"""Grid over stripes.py thresholds on the two labelled clips (2 fps)."""
import itertools
import json
import sys

import cv2

sys.path.insert(0, "/app/experiments/cosmos_combined")
import stripes as S  # noqa: E402

clips = [("data/user_clips/nyc_full.mp4", "test_videos/labels/nyc_full_scene.json"),
         ("data/walk8/yt_siren1.mp4", "test_videos/labels/yt_siren1_scene.json")]
frames = []
for v, lab in clips:
    spans = json.load(open(lab))["edge"]
    cap = cv2.VideoCapture(v)
    fps, n = cap.get(cv2.CAP_PROP_FPS), int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    t = 0.0
    while int(t * fps) < n:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
        ok, bgr = cap.read()
        if not ok:
            break
        frames.append((bgr, any(a <= t <= b + 1 for a, b in spans), any(a - 4 <= t <= b + 1 for a, b in spans)))
        t += 0.5
res = []
for rm, gm, dv, mb in itertools.product([0.25, 0.32, 0.4], [0.15, 0.25], [125, 150, 175], [2, 3]):
    tp = fp = fn = 0
    for bgr, at, near in frames:
        k, _ = S.bands(bgr, rm, gm, dv)
        y = k >= mb
        tp += y and near
        fp += y and not near
        fn += (not y) and at
    res.append((tp / max(1, tp + fn), fp, rm, gm, dv, mb, tp))
for r in sorted(res, key=lambda r: (-(r[0] - r[1] / 60)))[:8]:
    print(f"recall at corner {r[0]:.2f}  yes on sidewalk {r[1]}  row_min {r[2]} gap_max {r[3]} dark_v {r[4]} min_bands {r[5]}")
