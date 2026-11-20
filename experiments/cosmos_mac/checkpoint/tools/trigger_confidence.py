"""Detector confidence for each walk v3 trigger (used to pick the 0.7 cutoff).

  python trigger_confidence.py results/perception/london_walking.jsonl results/live/london_walking_v3/log.csv
"""
import csv
import json
import statistics
import sys


def main(tracks_path, v3_log):
    rows = [json.loads(l) for l in open(tracks_path)]
    conf = {}
    for f in rows:
        for tr in f["tracks"]:
            conf.setdefault(tr["id"], []).append((f["t"], tr["conf"]))
    for x in csv.DictReader(open(v3_log)):
        if not (x["source"] == "fast" or x["kind"] == "new"):
            continue
        tid, t = int(x["track"]), float(x["ready"])
        c = conf[tid]
        at = min(c, key=lambda v: abs(v[0] - t))[1]
        upto = [v[1] for v in c if v[0] <= t]
        print(f"t={t:5.2f} track {tid:3d} {x['cls']:6s} {x['side']:5s} conf_at={at:.2f} "
              f"median_so_far={statistics.median(upto):.2f} n={len(upto)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
