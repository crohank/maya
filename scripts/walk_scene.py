"""Walk mode scene cues: curb, crosswalk and moving traffic from Qwen3-VL.

The v3 fast path (scripts/walk_v3.py) only knows tracked objects on a collision
course, so it says nothing when the walker reaches the road edge. This samples
frames, asks Qwen3-VL a fixed yes/no question about the ground a few steps
ahead, and turns the answers into at most a few words per street corner:
"Crosswalk ahead." / "Curb ahead." and "Cars passing." Describes, never
decides: no "stop", no "safe to cross", no light colour (Qwen3-VL read yellow
NYC signal housings as a yellow light on every clip, results 2026-11-19).

Run inside the maya-engine image from the repo root:
  python scripts/walk_scene.py probe --video data/user_clips/nyc_full.mp4 [--fps 2] [--long-side 448]
      # writes results/scene/<stem>[_tag].jsonl, one row per sampled frame (GPU)
  python scripts/walk_scene.py score --video data/user_clips/nyc_full.mp4 [--set key=value]
      # per-second accuracy and cue timing against test_videos/labels/<stem>_scene.json
"""
import argparse
import json
import re
import time
from pathlib import Path

PROMPT = (
    "This photo is from a camera worn by a pedestrian, facing the way they walk. "
    "Judge only the ground in the bottom part of the photo, the next two or three steps, "
    "not the distance.\n"
    "edge: true if the pedestrian is at a curb or the start of a crosswalk, or already "
    "standing in the road.\n"
    "crosswalk: true if crosswalk stripes are on the ground right in front of the pedestrian.\n"
    "traffic: true if a car, van, bus, truck or bike is in the road right in front of the "
    "pedestrian (not parked at the side, not far down the street).\n"
    "Reply with exactly three words, yes or no, in the order edge crosswalk traffic. "
    "Example: yes no no"
)
# A JSON reply took 1.7 to 2.1 s per frame (about 25 new tokens); three words take a few.
KEYS = ("edge", "crosswalk", "traffic")

CUE = dict(
    confirm=2,        # consecutive edge=yes answers before the corner cue
    off_s=5.0,        # edge=no for this long ends the corner episode
    # Qwen3-VL said traffic=yes on 1 of 65 labelled traffic frames; tracks carry it.
    traffic="tracks",  # vlm | tracks | off
    traffic_gap=8.0,  # seconds between "Cars passing." in one episode
    track_bottom=0.55,  # tracks source: vehicle box bottom below this fraction of the frame
    track_motion="crossing",  # tracks source: moving (any non-static label) | crossing
    traffic_needs_edge=1,   # 1: only while the current frame also says edge
)


def parse_sets(sets):
    over = {}
    for s in sets or []:
        k, v = s.split("=", 1)
        if k not in CUE:
            raise SystemExit(f"unknown setting {k}")
        over[k] = type(CUE[k])(v) if not isinstance(CUE[k], str) else v
    return over


def scene_path(stem, tag=""):
    return Path("results/scene") / f"{stem}{'_' + tag if tag else ''}.jsonl"


def probe(args):
    import cv2
    from PIL import Image

    from maya.vlm import Vlm
    vlm = Vlm()
    cap = cv2.VideoCapture(args.video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = fps / args.fps
    out = scene_path(Path(args.video).stem, args.tag)
    out.parent.mkdir(parents=True, exist_ok=True)
    vlm.chat([{"type": "image", "image": Image.new("RGB", (64, 64))},
              {"type": "text", "text": "Hi"}], max_new_tokens=2)
    with open(out, "w") as f:
        i = 0.0
        while int(i) < n:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
            ok, bgr = cap.read()
            if not ok:
                break
            im = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
            im.thumbnail((args.long_side, args.long_side))
            t0 = time.perf_counter()
            text, _ = vlm.chat([{"type": "image", "image": im}, {"type": "text", "text": PROMPT}],
                               None, 8)
            lat = time.perf_counter() - t0
            row = dict(t=round(int(i) / fps, 3), lat=round(lat, 3), raw=text.strip())
            words = re.findall(r"\b(yes|no)\b", text.lower())
            for j, k in enumerate(KEYS):
                row[k] = j < len(words) and words[j] == "yes"
            f.write(json.dumps(row) + "\n")
            print(row["t"], row["lat"], row["edge"], row["crosswalk"], row["traffic"], flush=True)
            i += step
    print("wrote", out)


def vehicles_near(frames, t, cfg, vehicles=("car", "truck", "bus", "motorcycle", "bicycle")):
    """Vehicle track low in the frame (close) and moving the way track_motion asks, in
    any perception frame of the last half second before t."""
    moving = (lambda m: m.startswith("crossing")) if cfg["track_motion"] == "crossing" else \
        (lambda m: m != "static")
    return any(tr["cls"] in vehicles and moving(tr["motion"]) and tr["box"][3] > cfg["track_bottom"]
               for fr in frames if t - 0.5 <= fr["t"] <= t for tr in fr["tracks"])


def scene_cues(rows, cfg, frames=None):
    """Words with the time they could be spoken live (frame time + measured latency).

    Returns [{ready, answer, kind}] with kind corner or traffic.
    """
    cues, run, in_ep, last_yes, last_traffic, corner_at = [], [], False, -99.0, -99.0, -99.0
    for r in rows:
        ready = r["t"] + r["lat"]
        run = (run + [r])[-cfg["confirm"]:]
        if r["edge"]:
            last_yes = r["t"]
        if in_ep and r["t"] - last_yes > cfg["off_s"]:
            in_ep = False
        if not in_ep and len(run) == cfg["confirm"] and all(x["edge"] for x in run):
            in_ep, corner_at = True, ready
            word = "Crosswalk ahead." if any(x["crosswalk"] for x in run) else "Curb ahead."
            cues.append(dict(t=r["t"], ready=ready, answer=word, kind="corner"))
            continue
        # walk_v3.simulate speaks one queued word per slot, so a traffic word right
        # behind the corner word would be dropped.
        if in_ep and cfg["traffic"] != "off" and ready - last_traffic >= cfg["traffic_gap"] \
                and ready - corner_at >= 1.5 and (r["edge"] or not cfg["traffic_needs_edge"]):
            hit = r["traffic"] if cfg["traffic"] == "vlm" else vehicles_near(frames, r["t"], cfg)
            if hit:
                last_traffic = ready
                cues.append(dict(t=r["t"], ready=ready, answer="Cars passing.", kind="traffic"))
    return cues


def in_spans(t, spans, pad=0.0):
    return any(a - pad <= t <= b + 1 + pad for a, b in spans)


def score(args):
    cfg = dict(CUE, **parse_sets(args.set))
    stem = Path(args.video).stem
    lab = json.load(open(f"test_videos/labels/{stem}_scene.json"))
    rows = [json.loads(line) for line in open(scene_path(stem, args.tag))]
    frames = None
    if cfg["traffic"] == "tracks":
        frames = [json.loads(line) for line in open(f"results/perception/{stem}.jsonl")]
    lines = [f"# Scene cues: {stem}{' ' + args.tag if args.tag else ''}", "",
             f"Settings: `{json.dumps(cfg)}`", ""]
    lat = sorted(r["lat"] for r in rows)
    lines.append(f"Frames asked: {len(rows)}, latency median {lat[len(lat) // 2]:.2f} s, "
                 f"p90 {lat[int(len(lat) * 0.9)]:.2f} s")
    for k, spans in (("edge", lab["edge"]), ("traffic", lab["traffic"])):
        tp = sum(r[k] and in_spans(r["t"], spans) for r in rows)
        fp = sum(r[k] and not in_spans(r["t"], spans) for r in rows)
        fn = sum((not r[k]) and in_spans(r["t"], spans) for r in rows)
        lines.append(f"- per frame `{k}`: {tp} right yes, {fp} wrong yes, {fn} missed "
                     f"(precision {tp / max(1, tp + fp):.2f}, recall {tp / max(1, tp + fn):.2f})")
    cues = scene_cues(rows, cfg, frames)
    lines += ["", "| Spoken at (s) | Words | Verdict |", "|---|---|---|"]
    hit_eps = set()
    for c in cues:
        if c["kind"] == "corner":
            ep = next((i for i, (a, b) in enumerate(lab["edge"]) if a - 4 <= c["ready"] <= a + 3), None)
            ok = ep is not None and ep not in hit_eps
            if ok:
                hit_eps.add(ep)
                lead = lab["edge"][ep][0] - c["ready"]
                verdict = f"corner {ep + 1}, {abs(lead):.1f} s {'before' if lead >= 0 else 'after'} reaching the edge"
            else:
                verdict = "repeat inside a corner" if in_spans(c["ready"], lab["edge"]) else "false alarm on the sidewalk"
        else:
            verdict = "traffic there" if in_spans(c["ready"], lab["traffic"], pad=1.0) else \
                "no moving traffic in front" if in_spans(c["ready"], lab["edge"]) else "false alarm on the sidewalk"
        lines.append(f"| {c['ready']:.1f} | {c['answer']} | {verdict} |")
    lines += ["", f"Corners announced on time: {len(hit_eps)}/{len(lab['edge'])}"]
    text = "\n".join(lines) + "\n"
    print(text)
    if args.out:
        Path(args.out).write_text(text)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("probe")
    p.add_argument("--video", required=True)
    p.add_argument("--fps", type=float, default=2.0)
    p.add_argument("--long-side", type=int, default=448)
    p.add_argument("--tag", default="")
    s = sub.add_parser("score")
    s.add_argument("--video", required=True)
    s.add_argument("--tag", default="")
    s.add_argument("--set", action="append")
    s.add_argument("--out")
    args = ap.parse_args()
    probe(args) if args.cmd == "probe" else score(args)
