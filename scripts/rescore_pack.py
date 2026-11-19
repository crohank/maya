"""Re-score a saved results/pack/<run>.csv with the current scoring rules (no model).

  python scripts/rescore_pack.py <run> [--pack folder]
Code items are re-run against their tests.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import eval_pack as ev  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("run")
ap.add_argument("--pack", default="Kaggle Data")
a = ap.parse_args()
ev.PACK = Path(a.pack)
if (ev.PACK / "keys.json").exists():
    ev.KEYS = json.loads((ev.PACK / "keys.json").read_text())
items = {i["id"]: i for i in json.loads((ev.PACK / "items.json").read_text())}
refs = {r["id"]: r["reference_answer"] for r in json.loads((ev.PACK / "answers.json").read_text())}
rows = list(csv.DictReader(open(f"results/pack/{a.run}.csv", encoding="utf-8")))
by_mod = {}
for r in rows:
    ok, _ = ev.score(items[r["id"]], refs[r["id"]], r["answer"])
    m = by_mod.setdefault(r["modality"], [0, 0, 0])
    m[0] += int(r["pass"])
    m[1] += int(ok)
    m[2] += 1
for mod, (old, new, n) in by_mod.items():
    print(f"{a.run} {mod}: old {old}/{n}, rescored {new}/{n}")
