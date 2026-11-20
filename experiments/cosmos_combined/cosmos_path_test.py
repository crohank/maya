"""Cosmos3-Edge on a crop of the walking lane (centre 50% width, bottom 60% height): which
object stands in the path? For the obstacles the detector has no class for (v4 review: 24
missed: sandwich boards, planters, bollards, barriers, a scissor lift)."""
import sys

import cv2
from PIL import Image

sys.path.insert(0, "/app/scripts")
from walk_scene import CosmosVlm  # noqa: E402

Q = ("This photo shows the walking path just ahead of a pedestrian, about the next five steps. "
     "Is there an object standing in this path that they could walk into, such as a sign board, "
     "planter, bollard, barrier, pole, trash can, cart, table or machine? People and cars do not count. "
     "Answer with one word naming it, or none.")
CLIPS = ["rt_06_barriers_scaffold", "rt_07_scaffold_wheelbarrow", "rt_09_narrow_scaffold_obstacles",
         "rt_12_sidewalk_boards", "rt_17_crowd_horn", "rt_14_barrels_crowd_cross", "rt_02_taxi_front_curb",
         "rt_03_bike_front_crowd_crossing", "rt_18_stairs_crowd", "rt_05_taxi_turn_crossing"]


def crop(bgr):
    h, w = bgr.shape[:2]
    return bgr[int(h * 0.4):, int(w * 0.25):int(w * 0.75)]


if __name__ == "__main__":
    vlm = CosmosVlm()
    for stem in CLIPS:
        cap = cv2.VideoCapture(f"/main/data/realtest/{stem}.mp4")
        fps, n = cap.get(cv2.CAP_PROP_FPS), int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        out, t = [], 0.0
        while int(t * fps) < n:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
            ok, bgr = cap.read()
            if not ok:
                break
            im = Image.fromarray(cv2.cvtColor(crop(bgr), cv2.COLOR_BGR2RGB))
            im.thumbnail((448, 448))
            txt, _ = vlm.chat([{"type": "image", "image": im}, {"type": "text", "text": Q}], None, 4)
            w = (txt.strip().lower().split() or ["?"])[0].strip(".")
            out.append(f"{t:.0f}:{w}")
            t += 1.0
        print(stem, " ".join(out), flush=True)
