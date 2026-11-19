# 06 Practice pack: layout, scoring, and eval harness design

Dataset: `bhavyasreepylaa/ieee-ai-hackathon-2026-practice-pack` on Kaggle.
Stated contents (from the task brief, not from the page): 25 image, 20 audio,
20 text (some unanswerable), 20 code with unit tests, 15 video. Total 100 items.

## 1. What public pages show (checked 2026-11-18)

| Source | Result |
| --- | --- |
| Kaggle dataset page (unauthenticated fetch) | Returned only the title "IEEE AI Hackathon 2026 Practice Pack". The page is a JavaScript shell; no file list, data card, license, or size is in the static HTML. |
| Kaggle data explorer / file list | Not visible without JS rendering. Not reachable. |
| Kaggle public API (`/api/v1/datasets/list/...`) | Not attempted to completion: the request was blocked by the local permission policy as unauthorized access. Path stopped there, per instructions. |
| Web search for the slug, "practice pack", Roux Institute, NOT_IN_DOCUMENT | No hits. No indexed discussion, notebook, or GitHub repo uses this dataset. |

Bottom line: **nothing about the file layout or answer format is verified.**
Every layout detail below is an assumption marked UNVERIFIED. The harness is
designed to discover the layout at runtime and fail loudly when it guesses
wrong, so the first real run fixes the assumptions.

## 2. How to get the pack (user does this, not the agent)

1. Sign in at kaggle.com, open Settings, section "API", click "Create New
   Token". This downloads `kaggle.json`.
2. Put the token where the CLI looks for it:
   - Windows: `C:\Users\<you>\.kaggle\kaggle.json`
   - macOS / Linux: `~/.kaggle/kaggle.json`, then `chmod 600 ~/.kaggle/kaggle.json`
   - Or set `KAGGLE_USERNAME` and `KAGGLE_KEY` environment variables instead.
   - Newer CLI versions also accept a single `KAGGLE_API_TOKEN` env var
     (UNVERIFIED for the version you install).
3. Never commit `kaggle.json`. Add `.kaggle/` and `kaggle.json` to `.gitignore`.
4. Install and download:

```
pip install kaggle
kaggle datasets files -d bhavyasreepylaa/ieee-ai-hackathon-2026-practice-pack
kaggle datasets download -d bhavyasreepylaa/ieee-ai-hackathon-2026-practice-pack -p data/practice_pack --unzip
```

5. Run `kaggle datasets files ...` first: it prints the real file list and
   sizes. Paste that output into section 3 of this doc and drop the
   UNVERIFIED tags that it settles.
6. If the dataset has rules or a license that must be accepted, the CLI
   returns 403 until you accept on the website. That click is yours.

Video and audio can make the pack large; check the size from step 5 before
downloading on a slow link.

## 3. Assumed layout (UNVERIFIED)

The harness supports two common Kaggle shapes and picks whichever exists.

Shape A, one manifest (most likely for a mixed pack):

```
data/practice_pack/
  manifest.csv | manifest.jsonl | questions.json     # UNVERIFIED name
  images/  audio/  text/  code/  video/              # UNVERIFIED names
```

Manifest columns assumed (UNVERIFIED): `id, modality, file, question, answer`
plus optional `answer_type`, `keywords`, `tests`, `answerable`.

Shape B, one folder per modality, each with its own `questions.csv` or
`labels.json` (UNVERIFIED).

Per modality, assumed answer formats (all UNVERIFIED):

| Modality | Input | Assumed gold answer |
| --- | --- | --- |
| image (25) | jpg/png + question | short string or number (count, color, OCR text) |
| audio (20) | wav/mp3 + question | transcript snippet or short fact |
| text (20) | txt/pdf/md doc + question | short span; unanswerable items have gold `NOT_IN_DOCUMENT` (or empty / `answerable=false`) |
| code (20) | prompt or .py stub + `test_*.py` | function body that passes the tests |
| video (15) | mp4 + question | short string, or free text describing events |

Column name normalization: the loader lowercases headers and maps synonyms
(`image_path|path|filename -> file`, `gold|label|expected|ground_truth -> answer`,
`type|category -> modality`, `prompt|query -> question`). Unknown columns are
kept in a `meta` dict and written to the CSV so nothing gets silently dropped.

## 4. Backend call

```
POST {BASE}/ask   multipart/form-data
  file:     the item file (omit for code items with no file)
  question: string
-> 200 {"text": str, "route": str, "latency_ms": number}
```

- Timeout 120 s per item (video is slowest). One retry on connection error
  or 5xx, none on 4xx.
- Record two latencies: `latency_ms` from the server and wall-clock
  round trip measured by the client. Report both; they diverge when upload or
  queueing dominates.
- Sequential by default (`--concurrency 1`) so latency numbers reflect the
  single-user demo. Concurrency is a flag, off by default.

## 5. Scoring rules

Normalization `norm(s)`: Unicode NFKC, lowercase, strip, remove surrounding
quotes and trailing punctuation, collapse whitespace, drop leading articles
(a, an, the), number words to digits for zero to twenty, strip thousands
separators.

| Modality | Rule (applied in order, first hit wins) | Hand scoring |
| --- | --- | --- |
| image | 1. exact match on raw strings. 2. `norm(pred) == norm(gold)`. 3. numeric gold: first number in pred equals gold. 4. gold token-contained: `norm(gold)` appears as a whole-word substring of `norm(pred)` and pred is under 30 words. | Items where gold is a sentence, or rule 4 hit (flag `needs_review`). |
| audio | Same as image. If gold is a transcript longer than 8 words, score is word-level recall of gold tokens in pred; pass at 0.8 or higher. | Transcript items below 0.8 but above 0.5. |
| text, answerable | Rules 1 to 4 as image. If `keywords` column exists, pass when all keywords present after `norm`. | Long-span answers. |
| text, unanswerable | Pass if pred contains the literal token `NOT_IN_DOCUMENT` (case-insensitive, after strip). Fail if pred contains any other substantive answer, even with a hedge. | None. |
| text, answerable but model says NOT_IN_DOCUMENT | Automatic fail, logged as `false_refusal`. Tracked as its own count; it is the main failure mode of a strict refusal prompt. | None. |
| code | Extract the first fenced code block (else the whole text). Write `solution.py` into a fresh temp dir next to a copy of the item's test file. Run `python -I -m pytest -q` with a 30 s timeout. Pass only if exit code 0. Record tests passed / total from pytest output. | None. Partial pass is reported, scored as fail. |
| video | Same as image for short gold. Free-text gold (over 8 words) goes straight to hand scoring. | All free-text items. |

Hand scoring: rows flagged `needs_review=1` get `auto_pass` left blank; the
summary reports them separately as "pending review" and never counts them as
passes. A reviewer fills `hand_pass` (0/1) in the CSV and reruns
`--rescore-only` to rebuild the summary without calling the backend.

Code sandbox note: model-written code runs locally. Run it in a temp dir,
with `-I`, a timeout, and no network if possible. Inside the team's Docker
image is safer, but that is a later step, not part of this script.

Metrics recorded: accuracy per modality, overall accuracy (auto + hand),
unanswerable precision and recall (refusal correct vs `false_refusal`),
route distribution per modality (catches misrouting, e.g. video sent to the
image path).

## 6. Latency

Per modality and overall: count, median, p90, max of both server and wall
latency. p90 uses `statistics.quantiles(xs, n=10)[8]` when n is 10 or more,
else max. Failed requests are excluded from latency and counted as errors.

## 7. Failure logging

- `results/practice_pack_failures.jsonl`: one line per item that errored or
  failed scoring: id, modality, question, gold, pred, route, http status,
  exception text, pytest stdout tail (last 40 lines) for code.
- Errors never stop the run. A failing item gets `status=error` and the loop
  continues.
- Loader writes a warning line for every item whose file is missing on disk
  and skips it, so a wrong layout guess shows up as "N items skipped" at the
  top of the summary instead of as silent zero accuracy.

## 8. Outputs

`results/practice_pack_results.csv` columns:

```
id, modality, file, question, gold, pred, route, server_ms, wall_ms,
status, auto_pass, rule, needs_review, hand_pass, false_refusal,
tests_passed, tests_total, error
```

`results/practice_pack_summary.md`, example shape:

```
| modality | n | pass | pending | acc | median ms | p90 ms | errors |
| --- | --- | --- | --- | --- | --- | --- | --- |
| image | 25 | 19 | 2 | 0.76 | 1840 | 3100 | 0 |
| ...   |    |    |   |      |      |      |   |
| all   | 100 | . | . | . | . | . | . |

Unanswerable text: correct refusals x/y, false refusals z.
Routes: image -> vision 25/25, video -> video 14/15 (1 to vision).
```

## 9. Python skeleton (about 60 lines)

```python
"""Run the Kaggle practice pack against POST /ask and score it."""
import argparse, csv, json, re, statistics, subprocess, sys, tempfile, time, unicodedata
from pathlib import Path
import requests

NOT_IN_DOC = "NOT_IN_DOCUMENT"
SYN = {"image_path": "file", "path": "file", "filename": "file", "gold": "answer",
       "label": "answer", "expected": "answer", "type": "modality", "prompt": "question"}

def load_items(root: Path):
    # UNVERIFIED layout: try one manifest first, then per-modality folders.
    for name in ("manifest.csv", "questions.csv", "manifest.jsonl", "questions.json"):
        for p in root.rglob(name):
            rows = (list(csv.DictReader(p.open(encoding="utf-8"))) if p.suffix == ".csv"
                    else [json.loads(l) for l in p.open()] if p.suffix == ".jsonl"
                    else json.load(p.open()))
            for r in rows:
                r = {SYN.get(k.lower().strip(), k.lower().strip()): v for k, v in r.items()}
                r["file_path"] = (p.parent / r["file"]) if r.get("file") else None
                yield r
            return
    sys.exit(f"no manifest under {root}; run `kaggle datasets files` and update load_items")

def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", str(s)).lower().strip().strip("\"'").rstrip(".!?")
    s = re.sub(r"^(a|an|the)\s+", "", re.sub(r"\s+", " ", s))
    return s.replace(",", "")

def score(item, pred):
    gold, mod = str(item.get("answer", "")), item["modality"]
    if mod == "text" and (norm(gold) in ("", norm(NOT_IN_DOC)) or item.get("answerable") == "false"):
        return int(NOT_IN_DOC.lower() in pred.lower()), "refusal", 0
    if mod == "text" and NOT_IN_DOC.lower() in pred.lower():
        return 0, "false_refusal", 0
    if mod == "code":
        return run_tests(item, pred), "pytest", 0
    if len(gold.split()) > 8:
        return None, "long_gold", 1
    if pred.strip() == gold.strip() or norm(pred) == norm(gold):
        return 1, "exact_or_norm", 0
    if re.search(rf"\b{re.escape(norm(gold))}\b", norm(pred)) and len(pred.split()) < 30:
        return 1, "contains", 1
    return 0, "miss", 0

def run_tests(item, pred):
    m = re.search(r"```(?:python)?\n(.*?)```", pred, re.S)
    with tempfile.TemporaryDirectory() as d:
        Path(d, "solution.py").write_text(m.group(1) if m else pred, encoding="utf-8")
        Path(d, "test_item.py").write_text(Path(item["tests"]).read_text(), encoding="utf-8")
        r = subprocess.run([sys.executable, "-I", "-m", "pytest", "-q", d],
                           cwd=d, capture_output=True, text=True, timeout=30)
        return int(r.returncode == 0)

def ask(base, item):
    files = {"file": open(item["file_path"], "rb")} if item.get("file_path") else None
    t0 = time.perf_counter()
    r = requests.post(f"{base}/ask", data={"question": item["question"]}, files=files, timeout=120)
    r.raise_for_status()
    return r.json(), (time.perf_counter() - t0) * 1000

def p90(xs):
    return statistics.quantiles(xs, n=10)[8] if len(xs) >= 10 else max(xs, default=0)
```

Not shown in the skeleton (straightforward to add): the main loop that writes
each CSV row as it goes, the failures JSONL, `--rescore-only`, `--modality`
filter, retry on 5xx, and the Markdown summary writer grouping by modality
with `statistics.median` and `p90`.

## 10. Open questions to settle after the first download

1. Real manifest name and columns (UNVERIFIED).
2. How unanswerable text items are marked: literal `NOT_IN_DOCUMENT`, empty
   gold, or a boolean column (UNVERIFIED).
3. Whether code items ship a prompt only, or a stub plus tests, and what
   module name the tests import (`solution`? the stub's filename?). The
   skeleton assumes `solution.py`; change it to whatever the tests import
   (UNVERIFIED).
4. Whether video gold answers are short strings or free text (UNVERIFIED).
5. Whether the official evaluation uses the same rules as this harness. The
   practice pack scores are a proxy for the 30% evaluation component, not a
   prediction of it.
