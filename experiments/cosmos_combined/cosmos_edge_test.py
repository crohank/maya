"""Which single-question prompt lets Cosmos3-Edge see the curb approach (v2 combined prompt: 0/4 corners)."""
import json
import sys

import cv2
from PIL import Image

sys.path.insert(0, "/app/scripts")
from walk_scene import CosmosVlm, in_spans  # noqa: E402

PROMPTS = {
    "edge3": ("This photo is from a camera worn by a pedestrian, facing the way they walk. Is the edge of the "
              "sidewalk, a curb, or the start of a crosswalk within about three steps ahead of them? "
              "Answer yes or no."),
    "street_near": ("A pedestrian is walking toward the bottom-center of this photo's view. Will they reach a "
                    "street or crosswalk within the next three steps? Answer yes or no."),
}
vlm = CosmosVlm()
for video, lab in (("/main/data/user_clips/nyc_full.mp4", "/main/test_videos/labels/nyc_full_scene.json"),
                   ("/main/data/walk8/yt_siren1.mp4", "/main/test_videos/labels/yt_siren1_scene.json")):
    spans = json.load(open(lab))["edge"]
    cap = cv2.VideoCapture(video)
    fps, n = cap.get(cv2.CAP_PROP_FPS), int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    res = {k: [] for k in PROMPTS}
    t = 0.0
    while int(t * fps) < n:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
        ok, bgr = cap.read()
        if not ok:
            break
        im = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
        im.thumbnail((448, 448))
        for k, p in PROMPTS.items():
            txt, _ = vlm.chat([{"type": "image", "image": im}, {"type": "text", "text": p}], None, 3)
            res[k].append((t, "yes" in txt.lower()))
        t += 1.0
    for k, rows in res.items():
        tp = sum(y and in_spans(t, spans) for t, y in rows)
        fp = sum(y and not in_spans(t, spans) for t, y in rows)
        fn = sum((not y) and in_spans(t, spans) for t, y in rows)
        firsts = [next((t for t, y in rows if y and a - 5 <= t <= b), None) for a, b in spans]
        print(video.split("/")[-1], k, f"right yes {tp}, wrong yes {fp}, missed {fn}; first yes per corner {firsts} (edge starts {[a for a, _ in spans]})", flush=True)
