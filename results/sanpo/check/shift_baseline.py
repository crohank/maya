"""Chance baseline: the same spoken warnings, moved in time by a fixed shift
(wrapping at clip end), scored against the same labels. If on-time hits stay
high, they come from talking often, not from timing."""
import csv, glob, subprocess, sys
from pathlib import Path
SET = sys.argv[1] if len(sys.argv) > 1 else "sanpo"
LOGS, LABELS = {"sanpo": ("results/sanpo/live/sanpo_*_fastonly2/log.csv", "data/sanpo/labels"),
                 "internet": ("results/live/*_fastonly2/log.csv", "test_videos/labels")}[SET]
out = Path("results/sanpo/check/shifted")
for shift in (7.0, 13.0):
    args = []
    for log in sorted(glob.glob(LOGS)):
        run = Path(log).parent.name
        stem = run[: -len("_fastonly2")]
        rows = list(csv.DictReader(open(log, newline="", encoding="utf-8")))
        L = max(float(r["win_end"]) for r in rows)
        for r in rows:
            if r.get("audio_start"):
                r["audio_start"] = round((float(r["audio_start"]) + shift) % L, 3)
        d = out / f"{stem}_shift{int(shift)}"
        d.mkdir(parents=True, exist_ok=True)
        with open(d / "log.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
        args += ["--labels", f"{LABELS}/{stem}.json", "--log", str(d / "log.csv")]
    subprocess.run([sys.executable, "scripts/score_walk.py", *args,
                    "--out", f"results/sanpo/check/walk_scores_{SET}_shift{int(shift)}.md"], check=True)
