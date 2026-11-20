"""Can Cosmos3-Edge spot stairs ahead from one frame? rt_18 has stairs (manifest: bottom of the
staircase at 6 s, walking up 9 s, top landing 13.5 s); the other clips have none."""
import sys

import cv2
from PIL import Image

sys.path.insert(0, "/app/scripts")
from walk_scene import CosmosVlm  # noqa: E402

Q = ("This photo is from a camera worn by a pedestrian, facing the way they walk. Are there stairs or "
     "steps within about five steps ahead of them, in their path? Answer one word: up, down, or no.")
if __name__ == "__main__":
    vlm = CosmosVlm()
    for stem in ("rt_18_stairs_crowd", "rt_10_subway_entrance_horn", "rt_06_barriers_scaffold", "rt_12_sidewalk_boards",
                 "rt_13_crossing_headon", "rt_17_crowd_horn"):
        cap = cv2.VideoCapture(f"/main/data/realtest/{stem}.mp4")
        fps, n = cap.get(cv2.CAP_PROP_FPS), int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        out, t = [], 0.0
        while int(t * fps) < n:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
            ok, bgr = cap.read()
            if not ok:
                break
            im = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
            im.thumbnail((448, 448))
            txt, _ = vlm.chat([{"type": "image", "image": im}, {"type": "text", "text": Q}], None, 3)
            w = txt.strip().lower().split()[0].strip(".") if txt.strip() else "?"
            out.append(f"{t:.0f}:{w}")
            t += 1.0
        print(stem, " ".join(out), flush=True)
