"""Cosmos3-Edge stairs check at 1 fps -> /main/results/scene/<stem>_stairs.jsonl (t, lat, answer up/down/no).
Small evidence (cosmos_stairs_test.py): rt_18 stairs "up" every frame, rt_10 far-curb step-up
"up" 0 to 4 s, three sidewalk clips all "no", rt_17 "up" on 4 scattered frames."""
import json
import sys
import time
from pathlib import Path

import cv2
from PIL import Image

sys.path.insert(0, "/app/scripts")
sys.path.insert(0, "/app/experiments/cosmos_combined")
from cosmos_stairs_test import Q  # noqa: E402
from walk_scene import CosmosVlm  # noqa: E402

vlm = CosmosVlm()
for video in sys.argv[1:]:
    cap = cv2.VideoCapture(video)
    fps, n = cap.get(cv2.CAP_PROP_FPS), int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    out = Path(f"/main/results/scene/{Path(video).stem}_stairs.jsonl")
    with open(out, "w") as f:
        t = 0.0
        while int(t * fps) < n:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
            ok, bgr = cap.read()
            if not ok:
                break
            im = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
            im.thumbnail((448, 448))
            t0 = time.perf_counter()
            txt, _ = vlm.chat([{"type": "image", "image": im}, {"type": "text", "text": Q}], None, 3)
            w = txt.strip().lower().split()[0].strip(".") if txt.strip() else "no"
            f.write(json.dumps(dict(t=round(t, 2), lat=round(time.perf_counter() - t0, 3),
                                    answer=w if w in ("up", "down") else "no")) + "\n")
            t += 1.0
    print("wrote", out, flush=True)
