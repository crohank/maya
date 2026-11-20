"""Summarise combined-sim logs per settings tag: MOVE timing and direction, DESCRIBE length.

  python experiments/cosmos_combined/score_combined.py v0=combined tagA tagB ...
A bare tag reads results/live/<stem>_cc_<tag>/log.csv; name=dir reads <stem>_<dir>.

MOVE on time: speech starts no later than the object's closest point (largest box).
Toward: the instruction says the same side as the object ("1 step right" for a pole on
the right). Both are mechanical checks; the frames still need a look.
"""
import csv
import glob
import statistics
import sys
from pathlib import Path


def load(tag):
    name, d = tag.split("=", 1) if "=" in tag else (tag, f"cc_{tag}")
    out = {}
    for p in sorted(glob.glob(f"results/live/*_{d}/log.csv")):
        stem = Path(p).parent.name[:-len(d) - 1]
        out[stem] = list(csv.DictReader(open(p)))
    return name, out


def side_of(trigger):
    parts = trigger.split()
    return parts[1] if len(parts) > 1 else ""


def summary(name, runs):
    mv, desc, words, secs = [], [], 0, 0.0
    for stem, rows in runs.items():
        secs += max([float(r["end"]) for r in rows if r["end"]] + [12.0])
        for r in rows:
            if r["status"] == "spoken":
                words += len(r["spoken"].split())
            if r["mode"] == "MOVE":
                mv.append((stem, r))
            elif r["mode"] == "DESCRIBE":
                desc.append(r)
    spoken = [r for _, r in mv if r["status"] == "spoken"]
    late = [r for r in spoken if r["late"] == "True"]
    toward = [r for r in spoken if side_of(r["trigger"]) in ("left", "right")
              and side_of(r["trigger"]) in r["spoken"].lower()]
    lead = [float(r["t_close"]) - float(r["start"]) for r in spoken if r.get("t_close") not in ("", None)]
    ms = [float(r["model_s"]) for _, r in mv if r["model_s"]]
    dsp = [r for r in desc if r["status"] == "spoken"]
    dms = [float(r["model_s"]) for r in desc if r["model_s"]]
    kinds = {}
    for r in spoken:
        k = r["spoken"].lower().strip(".")
        kinds[k] = kinds.get(k, 0) + 1
    return (f"| {name} | {len(runs)} | {len(mv)} | {len(spoken)} | {len(spoken) - len(late)} | {len(toward)} | "
            f"{sum(1 for _, r in mv if r['status'] == 'silent')} | {sum(1 for _, r in mv if r['status'] == 'dropped')} | "
            f"{statistics.median(lead) if lead else float('nan'):+.1f} | {statistics.median(ms) if ms else 0:.2f} | {len(dsp)}/{len(desc)} | "
            f"{statistics.mean([len(r['spoken'].split()) for r in dsp]) if dsp else 0:.1f} | "
            f"{statistics.median(dms) if dms else 0:.2f} | {60 * words / secs:.0f} |\n"
            f"  MOVE lines: {', '.join(f'{k} x{v}' for k, v in sorted(kinds.items(), key=lambda kv: -kv[1]))}")


if __name__ == "__main__":
    print("| run | clips | MOVE asked | spoken | on time | toward object | kept quiet | dropped | median lead s | "
          "MOVE model s | DESCRIBE spoken/asked | DESCRIBE words | DESCRIBE model s | words/min |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for tag in sys.argv[1:]:
        print(summary(*load(tag)))
