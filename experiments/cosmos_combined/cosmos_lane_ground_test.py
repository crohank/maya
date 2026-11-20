"""One Cosmos call per second for both ground and lane obstacle (live budget): tracking about
0.42 s, street check 0.25 s and lane check 0.3 s per second of video do not fit one GPU in
real time. Same lane crop as cosmos_path_test.py; two words back."""
import sys

import cv2
from PIL import Image

sys.path.insert(0, "/app/scripts")
sys.path.insert(0, "/app/experiments/cosmos_combined")
from cosmos_path_test import CLIPS, crop  # noqa: E402
from walk_scene import CosmosVlm  # noqa: E402

Q2 = ("This photo shows the walking path just ahead of a pedestrian, about the next five steps. "
      "First word: street if the ground at the bottom is road or crosswalk stripes, sidewalk if it is "
      "paving. Second word: an object standing in this path that they could walk into (sign board, "
      "planter, bollard, barrier, pole, trash can, cart, table, machine), or none. People and cars do "
      "not count. Answer with exactly two words, like: sidewalk none")

if __name__ == "__main__":
    vlm = CosmosVlm()
    for stem in CLIPS:
        cap = cv2.VideoCapture(f"/main/data/realtest/{stem}.mp4")
        fps, n = cap.get(cv2.CAP_PROP_FPS), int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        out, lat, t = [], [], 0.0
        while int(t * fps) < n:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
            ok, bgr = cap.read()
            if not ok:
                break
            im = Image.fromarray(cv2.cvtColor(crop(bgr), cv2.COLOR_BGR2RGB))
            im.thumbnail((448, 448))
            txt, info = vlm.chat([{"type": "image", "image": im}, {"type": "text", "text": Q2}], None, 6)
            lat.append(info["model_s"])
            w = txt.strip().lower().replace(",", " ").split()
            out.append(f"{t:.0f}:{(w[0] if w else '?')[:4]}/{w[1] if len(w) > 1 else '?'}")
            t += 1.0
        print(stem, f"median {sorted(lat)[len(lat) // 2]:.2f}s", " ".join(out), flush=True)
