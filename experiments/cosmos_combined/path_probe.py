"""Cosmos3-Edge walking-lane obstacle check at 1 fps -> /main/results/scene/<stem>_path.jsonl.
cosmos_path_test.py on 10 real clips: sandwich boards ("sign") at the manifest times in rt_06
and rt_12, the scissor lift ("machine") 0 to 8 s in rt_09, the wheelbarrow ("cart") in rt_07,
bollards in rt_17, nothing in rt_18; misses the orange barrels in rt_14. Ground features
(manhole, pothole, crosswalk) come back too and are dropped by WORDS."""
import json
import sys
import time
from pathlib import Path

import cv2
from PIL import Image

sys.path.insert(0, "/app/scripts")
sys.path.insert(0, "/app/experiments/cosmos_combined")
from cosmos_path_test import Q, crop  # noqa: E402
from walk_scene import CosmosVlm  # noqa: E402

WORDS = {"sign": "Sign board", "signboard": "Sign board", "board": "Sign board", "machine": "Machine",
         "cart": "Cart", "trash": "Trash can", "bin": "Trash can", "pole": "Pole", "bollard": "Bollard",
         "planter": "Planter", "scaffolding": "Scaffolding", "barrier": "Barrier", "barrel": "Barrel",
         "table": "Table", "bench": "Bench", "fire": "Hydrant", "hydrant": "Hydrant", "cone": "Cone"}

if __name__ == "__main__":
    vlm = CosmosVlm()
    for video in sys.argv[1:]:
        cap = cv2.VideoCapture(video)
        fps, n = cap.get(cv2.CAP_PROP_FPS), int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        out = Path(f"/main/results/scene/{Path(video).stem}_path.jsonl")
        with open(out, "w") as f:
            t = 0.0
            while int(t * fps) < n:
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
                ok, bgr = cap.read()
                if not ok:
                    break
                im = Image.fromarray(cv2.cvtColor(crop(bgr), cv2.COLOR_BGR2RGB))
                im.thumbnail((448, 448))
                t0 = time.perf_counter()
                txt, _ = vlm.chat([{"type": "image", "image": im}, {"type": "text", "text": Q}], None, 4)
                w = (txt.strip().lower().split() or ["none"])[0].strip(".")
                f.write(json.dumps(dict(t=round(t, 2), lat=round(time.perf_counter() - t0, 3), raw=w,
                                        name=WORDS.get(w))) + "\n")
                t += 1.0
        print("wrote", out, flush=True)
