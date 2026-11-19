"""Run practice-pack items through the Maya engine and score them.

Run on the GPU, one job at a time (Git Bash, repo root):
  bash scripts/gpu_job.sh pack python scripts/eval_pack.py --modality image --run image_base
  bash scripts/gpu_job.sh pack python scripts/eval_pack.py --run all_v1        # every item

Writes results/pack/<run>.csv (one row per item) and results/pack/<run>.md.
Scoring (see scripts/pack_keys.json for the hand-written keys):
- code: the answer's function is run against the item's unit test file in a
  subprocess (python -I, 20 s timeout). Pass on exit code 0.
- audio "Transcribe": word error rate against the reference, pass at WER <= 0.10.
- image counting: first number in the answer equals the reference count.
- everything else: every key group matches (case-insensitive substring after
  normalizing). For "first ... last" questions the first group must appear
  before the second. REFUSE passes when the answer says the document does
  not contain it.
The keys are lenient on wording and strict on facts; rows that fail are
worth reading by eye (the .md lists them).
"""
import argparse
import csv
import json
import re
import statistics
import subprocess
import sys
import tempfile
import time
import traceback
import unicodedata
from pathlib import Path

PACK = Path("Kaggle Data")
KEYS = json.loads(Path("scripts/pack_keys.json").read_text())
NUM_WORDS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
    "fifteen sixteen seventeen eighteen nineteen twenty".split())}
REFUSAL = re.compile(r"does not say|doesn't say|not in the document|not_in_document|does not (mention|contain|state|include|specify)|no information", re.I)


def norm(s):
    s = unicodedata.normalize("NFKC", s or "").lower()
    s = s.replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", s).strip()


def first_number(s):
    for tok in re.findall(r"\d+(?:\.\d+)?|[a-z]+", norm(s)):
        if tok[0].isdigit():
            return float(tok)
        if tok in NUM_WORDS:
            return float(NUM_WORDS[tok])
    return None


def wer(ref, hyp):
    r = re.findall(r"[a-z0-9']+", norm(ref))
    h = re.findall(r"[a-z0-9']+", norm(hyp))
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (r[i - 1] != h[j - 1]))
            prev, d[j] = d[j], cur
    return d[len(h)] / max(1, len(r))


def match_groups(groups, answer, question):
    a = norm(answer)
    pos = []
    for g in groups:
        if g == "REFUSE":
            if not REFUSAL.search(a):
                return False
            continue
        hit = None
        for alt in g:
            if alt.startswith("#"):
                n = first_number(a)
                if n is not None and n == float(alt[1:]):
                    hit = 0
            else:
                i = a.find(alt)
                if i >= 0 and (hit is None or i < hit):
                    hit = i
        if hit is None:
            return False
        pos.append(hit)
    if "first" in question.lower() and "last" in question.lower() and len(pos) == 2:
        return pos[0] < pos[1]
    return True


def run_code_test(item_id, answer):
    test = (PACK / "code" / "tests" / f"{item_id}_test.py").read_text()
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "t.py"
        f.write_text(answer + "\n\n" + test)
        try:
            p = subprocess.run([sys.executable, "-I", str(f)], capture_output=True, text=True,
                               timeout=20, cwd=td)
            return p.returncode == 0, (p.stderr or "")[-300:]
        except subprocess.TimeoutExpired:
            return False, "timeout"


def score(item, ref, answer):
    iid, q, mod = item["id"], item["question"] or "", item["modality"]
    if mod == "code":
        ok, err = run_code_test(iid, answer)
        return ok, err
    if mod == "audio" and q.lower().startswith("transcribe"):
        w = wer(ref, answer)
        return w <= 0.10, f"wer={w:.3f}"
    groups = KEYS.get(iid)
    if groups is None and re.match(r"how many", q, re.I):
        groups = [[f"#{int(first_number(ref))}"]]
    if groups is None:
        groups = [[norm(ref).rstrip(".")]]
    if (mod == "text" and groups != ["REFUSE"] and REFUSAL.search(norm(answer))):
        return False, "false_refusal"
    return match_groups(groups, answer, q), ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="name for results/pack/<run>.*")
    ap.add_argument("--modality", action="append", help="image, audio, text, video, code")
    ap.add_argument("--ids", help="comma-separated item ids")
    ap.add_argument("--opt", action="append", default=[],
                    help="handler option key=value, passed to the engine (repeatable)")
    args = ap.parse_args()

    from maya.engine import Engine
    opts = dict(o.split("=", 1) for o in args.opt)
    items = json.loads((PACK / "items.json").read_text())
    refs = {a["id"]: a["reference_answer"] for a in json.loads((PACK / "answers.json").read_text())}
    if args.modality:
        items = [i for i in items if i["modality"] in args.modality]
    if args.ids:
        keep = set(args.ids.split(","))
        items = [i for i in items if i["id"] in keep]

    t0 = time.perf_counter()
    eng = Engine(**opts)
    load_s = time.perf_counter() - t0
    out = Path("results/pack")
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for it in items:
        path = str(PACK / it["file"]) if it["file"] else None
        t = time.perf_counter()
        try:
            answer, info = eng.answer(it["modality"], path, it["question"])
            err = ""
        except Exception as e:
            answer, info, err = "", {}, f"{type(e).__name__}: {e}"
            traceback.print_exc()
        secs = time.perf_counter() - t
        ok, note = score(it, refs[it["id"]], answer) if not err else (False, err)
        rows.append({"id": it["id"], "modality": it["modality"], "pass": int(ok),
                     "seconds": round(secs, 2), "route": info.get("route", ""),
                     "note": note, "question": it["question"][:200] if it["question"] else "",
                     "answer": answer, "reference": str(refs[it["id"]])[:300]})
        print(f"{it['id']} {'PASS' if ok else 'fail'} {secs:5.1f}s  {answer[:100]!r}", flush=True)

    with open(out / f"{args.run}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    lines = [f"# Practice pack run: {args.run}", "",
             f"Options: {opts or 'defaults'}. Engine load {load_s:.1f} s. "
             "Scoring rules in the scripts/eval_pack.py docstring.", "",
             "| Modality | Pass | Median s | Max s |", "|---|---|---|---|"]
    for mod in ["image", "audio", "text", "video", "code"]:
        rs = [r for r in rows if r["modality"] == mod]
        if rs:
            s = [r["seconds"] for r in rs]
            lines.append(f"| {mod} | {sum(r['pass'] for r in rs)}/{len(rs)} | "
                         f"{statistics.median(s):.2f} | {max(s):.2f} |")
    lines.append(f"| all | {sum(r['pass'] for r in rows)}/{len(rows)} | | |")
    lines += ["", "## Failures", "", "| id | answer | reference | note |", "|---|---|---|---|"]
    for r in rows:
        if not r["pass"]:
            lines.append(f"| {r['id']} | {r['answer'][:160].replace('|', '/').replace(chr(10), ' ')} | "
                         f"{r['reference'][:100].replace('|', '/').replace(chr(10), ' ')} | {r['note'][:80].replace('|', '/').replace(chr(10), ' ')} |")
    (out / f"{args.run}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:12]))


if __name__ == "__main__":
    main()
