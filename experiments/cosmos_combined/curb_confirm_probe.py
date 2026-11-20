"""Cosmos3-Edge yes/no check on frames where stripes.py saw a crosswalk, to drop stripe hits
that are not a curb in front of the walker (2026-11-20 frame check: 5 of 15 curb words were
mid-crossing, a side crosswalk, a bike-lane marking or plain paving)
-> /main/results/scene/<stem>_curbq.jsonl with one answer per prompt."""
import json
import sys
import time
from pathlib import Path

import cv2
from PIL import Image

sys.path.insert(0, "/app/scripts")
from walk_scene import CosmosVlm  # noqa: E402

PROMPTS = {
    "where": ("This photo is from a camera held by a person walking. Where is that person standing? "
              "Answer with one letter. A: on the sidewalk at the edge of a street, with a crosswalk in front. "
              "B: already in the street, on the crosswalk. C: on the sidewalk, no crosswalk in front."),
    "ahead": ("Is a painted crosswalk directly in front of the camera, starting a few steps ahead, "
              "with the camera still on the sidewalk? Answer yes or no."),
}

if __name__ == "__main__":
    vlm = CosmosVlm()
    for video in sys.argv[1:]:
        stem = Path(video).stem
        hits = [json.loads(l) for l in open(f"/main/results/scene/{stem}_stripes.jsonl")]
        hits = [r["t"] for r in hits if r["stripes"]]
        cap = cv2.VideoCapture(video)
        fps = cap.get(cv2.CAP_PROP_FPS)
        with open(f"/main/results/scene/{stem}_curbq.jsonl", "w") as f:
            for t in hits:
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
                ok, bgr = cap.read()
                if not ok:
                    break
                im = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
                im.thumbnail((448, 448))
                row = dict(t=t)
                for k, q in PROMPTS.items():
                    t0 = time.perf_counter()
                    txt, _ = vlm.chat([{"type": "image", "image": im}, {"type": "text", "text": q}], None, 4)
                    row[k] = txt.strip()
                    row[k + "_s"] = round(time.perf_counter() - t0, 3)
                f.write(json.dumps(row) + "\n")
        print(stem, len(hits), flush=True)
