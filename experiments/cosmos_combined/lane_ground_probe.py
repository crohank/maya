"""One Cosmos3-Edge call per second on the lane crop for both the ground (street or sidewalk)
and an obstacle in the path -> /main/results/scene/<stem>_lg.jsonl, with the fields
walk_scene.scene_cues and the sim's path words read. Fits the live budget (0.17 to 0.25 s per
call next to tracking at about 0.42 s per second of video)."""
import json
import sys
import time
from pathlib import Path

import cv2
from PIL import Image

sys.path.insert(0, "/app/scripts")
sys.path.insert(0, "/app/experiments/cosmos_combined")
from cosmos_lane_ground_test import Q2  # noqa: E402
from cosmos_path_test import crop  # noqa: E402
from path_probe import WORDS  # noqa: E402
from walk_scene import CosmosVlm  # noqa: E402

if __name__ == "__main__":
    vlm = CosmosVlm()
    for video in sys.argv[1:]:
        cap = cv2.VideoCapture(video)
        fps, n = cap.get(cv2.CAP_PROP_FPS), int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        out = Path(f"/main/results/scene/{Path(video).stem}_lg.jsonl")
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
                txt, _ = vlm.chat([{"type": "image", "image": im}, {"type": "text", "text": Q2}], None, 6)
                w = txt.strip().lower().replace(",", " ").split() + ["", ""]
                road = w[0].startswith(("street", "cross", "road"))
                ob = w[1].strip(".")
                f.write(json.dumps(dict(t=round(t, 2), lat=round(time.perf_counter() - t0, 3), raw=txt.strip(),
                                        road=road, edge=road, crosswalk=False, traffic=False, curb_up=False,
                                        obstacle=None, obstacle_side="ahead", name=WORDS.get(ob))) + "\n")
                t += 1.0
        print("wrote", out, flush=True)
