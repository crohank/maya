"""Demo half for the side-by-side videos: redraw a finished run's boxes and captions over a
blurred, dimmed copy of the clip, from its saved log.csv (no models, no audio).

  python experiments/cosmos_combined/render_blur.py <tag> <out_dir> <stem>...
"""
import csv
import json
import sys

sys.path.insert(0, "/app/scripts")
sys.path.insert(0, "/app/experiments/cosmos_combined")
import live_harness as lh  # noqa: E402
import sim_walk_combined as sim  # noqa: E402
import walk_v3 as w3  # noqa: E402

BLUR = 9.0


def load_sched(path):
    rows = []
    for r in csv.DictReader(open(path)):
        for k in ("start", "end"):
            r[k] = float(r[k]) if r[k] else -1.0
        r["track"] = int(r["track"]) if r["track"].lstrip("-").isdigit() else None
        r["late"] = r["late"] == "True"
        rows.append(r)
    return rows


if __name__ == "__main__":
    tag, out_dir, stems = sys.argv[1], sys.argv[2], sys.argv[3:]
    for stem in stems:
        src = sim.find_video(stem)
        frames = [json.loads(line) for line in open(f"/main/results/perception/{stem}.jsonl")]
        dur = min(frames[-1]["t"], lh.ffprobe_duration(src))
        settings = json.load(open(f"results/live/{stem}_cc_{tag}/settings.json"))
        cfg = dict(w3.BASE, scene=1, scene_tag="v2", sounds=1, steps=settings["steps"], **w3.parse_sets(settings["wset"]))
        w3.annotate(frames, w3.video_aspect(src), cfg)
        sched = load_sched(f"results/live/{stem}_cc_{tag}/log.csv")
        sim.render(src, frames, sched, [], dur, f"{out_dir}/{stem}.mp4", blur=BLUR, video_only=True)
        print("wrote", stem, flush=True)
