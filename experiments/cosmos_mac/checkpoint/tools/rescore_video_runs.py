"""Rescore every saved practice-pack video run (results/pack/vid_*.csv) with the current keys. No model is run.

This showed the Cosmos video runs were understated: for example, vid_c1_cosmos_cv2 rescores from 6/15 to 11/15.
Run from the repo root with any Python 3:
  python experiments/cosmos_mac/checkpoint/tools/rescore_video_runs.py
"""
import csv
import glob
import os
import re
import sys

sys.path.insert(0, "scripts")
import eval_pack as ev  # noqa: E402


def main():
    for f in sorted(glob.glob("results/pack/vid_*.csv")):
        run = os.path.basename(f)[:-4]
        rows = list(csv.DictReader(open(f, encoding="utf-8")))
        md = f[:-4] + ".md"
        opts = re.search(r"Options: (\{.*?\})", open(md).read()) if os.path.exists(md) else None
        old = sum(int(r["pass"]) for r in rows)
        new = sum(int(ev.score({"id": r["id"], "question": r["question"], "modality": "video"},
                               r["reference"], r["answer"])[0]) for r in rows)
        print(f"{run:22s} saved {old:2d}/{len(rows)}  rescored {new:2d}/{len(rows)}  {opts.group(1) if opts else ''}")


if __name__ == "__main__":
    main()
