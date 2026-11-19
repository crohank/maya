"""Simulated live run: perception fast path + Cosmos3-Edge slow path + Piper.

Fast path: per-frame tracks from scripts/perception.py (precomputed jsonl at
8 fps, each frame ready at t + its measured perception time). A rule turns a
confirmed hazard into a short warning ("Person close ahead, approaching.").
Slow path: Cosmos looks at the last 2 s, is given the current tracks, and is
asked only for what the tracker cannot see (curb, crosswalk, step, sign).
Speaker: one voice; the newest fast warning wins, then the newest Cosmos fact;
stale items are dropped.

Timing caveat: perception was measured on its own; here both paths are assumed
to run concurrently without slowing each other on the GPU.

Run inside the cosmos-tf container:
  python scripts/fused_harness.py --video test_videos/london_walking.mp4
  python scripts/fused_harness.py --video ... --no-vlm      # fast path only
Writes results/live/<stem>_fused/ (or _fastonly/): annotated.mp4, log.csv, summary.md
"""
import argparse
import collections
import csv
import json
import statistics
import tempfile
import time
from pathlib import Path

import live_harness as lh

NAMES = {
    "person": "Person", "bicycle": "Bike", "motorcycle": "Motorbike", "car": "Car",
    "truck": "Truck", "bus": "Bus", "pole": "Pole", "trash can": "Trash can",
    "traffic cone": "Cone", "stroller": "Stroller", "fire hydrant": "Hydrant",
    "bench": "Bench", "cart": "Cart", "wheelchair": "Wheelchair", "scooter": "Scooter",
}
VEHICLES = {"car", "truck", "bus", "motorcycle"}

# Distance from the depth model reads 2 to 3x long on these clips (most tracks
# "far"), so closeness uses image geometry instead: on flat ground a box whose
# bottom edge is low in the frame is close, and TTC comes from box growth, which
# does not depend on the depth scale. Thresholds tuned by eye on the 4 test clips.
CLOSE_BOTTOM = 0.88
CLOSE_HEIGHT = 0.45
TTC_WARN_S = 3.5
MIN_HEIGHT = 0.12
PATH_X = (0.25, 0.75)
CONFIRM, WINDOW = 3, 5
TRACK_COOLDOWN_S = 5.0
SAME_TEXT_COOLDOWN_S = 4.0
FAST_STALE_S = 1.0
SLOW_STALE_S = 2.5

VLM_PROMPT = (
    "Objects already tracked and announced: {tracks}. Name one thing in my walking "
    "path that this list does not cover, such as a curb, step, crosswalk, pole, "
    "sign, or obstacle, and where it is, in under 10 words. If there is nothing "
    "new, reply exactly NONE."
)


def hazard(tr):
    """Return 'close', 'approaching', or None for one track."""
    if tr["cls"] not in NAMES or tr["conf"] < 0.4:
        return None
    x1, y1, x2, y2 = tr["box"]
    h, cx = y2 - y1, (x1 + x2) / 2
    in_path = PATH_X[0] <= cx <= PATH_X[1]
    close = y2 >= CLOSE_BOTTOM or h >= CLOSE_HEIGHT
    fast = (tr["motion"] == "approaching" and tr["ttc_s"] is not None
            and tr["ttc_s"] < TTC_WARN_S and h >= MIN_HEIGHT)
    if tr["cls"] in VEHICLES:
        return "approaching" if fast else None
    if in_path and close:
        return "close"
    if in_path and fast:
        return "approaching"
    return None


def phrase(tr, kind):
    side = {"ahead": "ahead", "left": "on your left", "right": "on your right"}[tr["side"]]
    name = NAMES[tr["cls"]]
    if kind == "close":
        moving = ", approaching" if tr["motion"] == "approaching" else ""
        return f"{name} close {side}{moving}."
    return f"{name} {side}, approaching."


def fast_candidates(frames):
    hist = collections.defaultdict(lambda: collections.deque(maxlen=WINDOW))
    last_warn = {}
    out = []
    for fr in frames:
        t = fr["t"]
        ready = t + sum(fr.get("timing", {}).values()) / 1000.0
        seen = set()
        for tr in fr["tracks"]:
            kind = hazard(tr)
            hist[tr["id"]].append(kind)
            seen.add(tr["id"])
            if kind is None or sum(k is not None for k in hist[tr["id"]]) < CONFIRM:
                continue
            if t - last_warn.get(tr["id"], -99) < TRACK_COOLDOWN_S:
                continue
            last_warn[tr["id"]] = t
            out.append(dict(source="fast", win_start=max(0.0, t - WINDOW / 8), win_end=t,
                            ready=ready, answer=phrase(tr, kind), raw=json.dumps(tr),
                            input_tokens=0, model_s=ready - t))
        for tid in list(hist):
            if tid not in seen:
                hist[tid].append(None)
    return out


def tracks_text(frames, t):
    fr = None
    for f in frames:
        if f["t"] > t:
            break
        fr = f
    if not fr:
        return "none"
    items = sorted((tr for tr in fr["tracks"] if tr["cls"] in NAMES),
                   key=lambda tr: -(tr["box"][3] - tr["box"][1]))[:3]
    return "; ".join(f"{tr['cls']} {tr['side']} {tr['motion']}" for tr in items) or "none"


def slow_candidates(model, proc, args, frames, dur, td):
    out = []
    t_video = args.window
    while t_video < dur:
        ws = max(0.0, t_video - args.window)
        clip = f"{td}/win.mp4"
        lh.cut_window(args.video, ws, t_video, clip, args.fps, args.width)
        tracked = tracks_text(frames, t_video)
        t0 = time.perf_counter()
        raw, n_in = lh.ask(model, proc, clip, VLM_PROMPT.format(tracks=tracked), args.max_new_tokens)
        model_s = time.perf_counter() - t0
        answer, flagged = lh.safety_filter(lh.first_sentences(raw, 1))
        names = [w for w in NAMES if w in tracked]
        drop = "NONE" in raw.upper() or any(n in answer.lower() for n in names)
        out.append(dict(source="vlm", win_start=ws, win_end=t_video, ready=t_video + model_s,
                        answer=answer, raw=raw, input_tokens=n_in, model_s=model_s,
                        status="none" if drop else "", flagged=flagged))
        t_video += max(model_s, args.min_interval)
    return out


def speak(cands, tts, wav_dir):
    cands.sort(key=lambda e: e["ready"])
    for i, e in enumerate(cands):
        e.update(idx=i, status=e.get("status", ""), tts_s=0.0, audio_start=None,
                 audio_dur=0.0, lag=None, age=None, wav="")
    t_free, last_text, last_t = 0.0, "", -99.0
    while True:
        pending = [e for e in cands if not e["status"]]
        if not pending:
            break
        ready = [e for e in pending if e["ready"] <= t_free]
        if not ready:
            t_free = pending[0]["ready"]
            continue
        for e in ready:
            limit = FAST_STALE_S if e["source"] == "fast" else SLOW_STALE_S
            if t_free - e["ready"] > limit:
                e["status"] = "stale"
        fresh = [e for e in ready if not e["status"]]
        if not fresh:
            continue
        fast = [e for e in fresh if e["source"] == "fast"]
        pick = (fast or fresh)[-1]
        for e in fresh:
            if e is not pick and (e["source"] == pick["source"] or pick["source"] == "fast"):
                e["status"] = "stale"
        if pick["answer"].lower() == last_text and pick["ready"] - last_t < SAME_TEXT_COOLDOWN_S:
            pick["status"] = "repeat"
            continue
        pick["wav"] = str(wav_dir / f"{pick['idx']:03d}.wav")
        t1 = time.perf_counter()
        pick["audio_dur"] = tts.say(pick["answer"], pick["wav"])
        pick["tts_s"] = time.perf_counter() - t1
        pick["audio_start"] = max(t_free, pick["ready"]) + pick["tts_s"]
        pick["lag"] = pick["audio_start"] - pick["win_end"]
        pick["age"] = pick["audio_start"] - pick["win_start"]
        pick["status"] = "spoken"
        t_free = pick["audio_start"] + pick["audio_dur"]
        last_text, last_t = pick["answer"].lower(), pick["ready"]
    return cands


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--perception", help="jsonl from scripts/perception.py (default by stem)")
    ap.add_argument("--no-vlm", action="store_true")
    ap.add_argument("--window", type=float, default=2.0)
    ap.add_argument("--fps", type=float, default=4.0)
    ap.add_argument("--width", type=int, default=448)
    ap.add_argument("--min-interval", type=float, default=1.5)
    ap.add_argument("--max-new-tokens", type=int, default=24)
    ap.add_argument("--out", default="results/live")
    args = ap.parse_args()

    stem = Path(args.video).stem
    pfile = args.perception or f"results/perception/{stem}.jsonl"
    frames = [json.loads(line) for line in open(pfile)]
    dur = lh.ffprobe_duration(args.video)
    out_dir = Path(args.out) / f"{stem}_{'fastonly' if args.no_vlm else 'fused'}"
    wav_dir = out_dir / "wav"
    wav_dir.mkdir(parents=True, exist_ok=True)
    tts = lh.Tts()

    cands = fast_candidates(frames)
    with tempfile.TemporaryDirectory() as td:
        if not args.no_vlm:
            from transformers import AutoModelForImageTextToText, AutoProcessor
            proc = AutoProcessor.from_pretrained(lh.PROCESSOR_ID)
            model = AutoModelForImageTextToText.from_pretrained(lh.MODEL_ID, device_map="cuda").eval()
            lh.cut_window(args.video, 0, min(args.window, dur), f"{td}/w.mp4", args.fps, args.width)
            lh.ask(model, proc, f"{td}/w.mp4", "What do you see?", 8)
            cands += slow_candidates(model, proc, args, frames, dur, td)
        cands = speak(cands, tts, wav_dir)
        spoken = [e for e in cands if e["status"] == "spoken"]
        for e in spoken:
            print(f"[{e['source']:4}] saw {e['win_start']:5.1f}-{e['win_end']:5.1f}s  "
                  f"speaks {e['audio_start']:5.1f}s (+{e['lag']:.2f}s)  {e['answer']}", flush=True)
        lh.render(args.video, dur, spoken, str(out_dir / "annotated.mp4"), td)

    keys = ["idx", "source", "win_start", "win_end", "ready", "status", "audio_start",
            "audio_dur", "lag", "age", "model_s", "input_tokens", "answer", "raw"]
    with open(out_dir / "log.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for e in cands:
            w.writerow({k: (round(v, 3) if isinstance(v, float) else v) for k, v in e.items()})

    def med(src, key):
        vals = [e[key] for e in spoken if e["source"] == src and e[key] is not None]
        return f"median {statistics.median(vals):.2f}s, max {max(vals):.2f}s" if vals else "n/a"

    count = collections.Counter((e["source"], e["status"]) for e in cands)
    with open(out_dir / "summary.md", "w") as f:
        f.write(f"# Fused harness: {Path(args.video).name}{' (fast path only)' if args.no_vlm else ''}\n\n")
        f.write(f"Candidates by source and status: {dict(count)}\n\n")
        f.write(f"- Fast warnings, speech start minus newest frame: {med('fast', 'lag')}\n")
        f.write(f"- Cosmos facts, speech start minus newest frame: {med('vlm', 'lag')}\n\n")
        f.write("| Source | Saw (s) | Spoken at (s) | Answer |\n|---|---|---|---|\n")
        for e in spoken:
            f.write(f"| {e['source']} | {e['win_start']:.1f}-{e['win_end']:.1f} | "
                    f"{e['audio_start']:.1f} | {e['answer']} |\n")
    print(f"wrote {out_dir}")


if __name__ == "__main__":
    main()
