"""Build extra dev and held-out packs under data/extra/<set>/ in the practice-pack format.

Each set gets items.json and answers.json (same schema as Kaggle Data/), keys.json
(scripts/pack_keys.json format, read by eval_pack.py --pack), media files and SOURCE.md.
Items in the practice pack are excluded (ids from Kaggle Data/answers.json source_ids).

Run in a CPU container with network, from the repo root (Git Bash). pyarrow and fpdf2
are not in the image, so they live in a pip --target folder mounted at /pylib:
  docker run --rm -v <lib>:/pylib maya-engine pip install --no-deps --target /pylib \
      pyarrow fpdf2 fonttools defusedxml
  MSYS_NO_PATHCONV=1 docker run --rm -e HF_HOME=/app/data/extra/_raw/hf -v <lib>:/pylib \
      -v "$(pwd -W):/app" -w /app maya-engine python -I scripts/make_extra_data.py squad
Sets: squad, humaneval, mbpp, vizwiz, librispeech, esc50. Then, with --network none:
  ... python -I scripts/make_extra_data.py check humaneval mbpp squad
Raw downloads go to data/extra/_raw/<set>/ and are deleted after conversion.
"""
import io
import json
import random
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import urllib.request
from collections import Counter
from pathlib import Path

sys.path.insert(0, "/pylib")

SEED = 20261118
PACK = Path("Kaggle Data")
OUT = Path("data/extra")
RAW = OUT / "_raw"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REVISIONS = {
    "rajpurkar/squad_v2": "3ffb306f725f7d2ce8394bc1873b24868140c412",
    "openai/openai_humaneval": "7dce6050a7d6d172f3cc5c32aa97f52fa1a2e544",
    "google-research-datasets/mbpp": "4bb6404fdc6cacfda99d4ac4205087b89d32030c",
    "lmms-lab/VizWiz-VQA": "d428a2dae984f79cf1b9d99467dfa883e0c30686",
    "openslr/librispeech_asr": "71cacbfb7e2354c4226d01e70d77d5fca3d04ba1",
}
ESC50_COMMIT = "33c8ce9eb2cf0b1c2f8bcf322eb349b6be34dbb6"
KEYS_DOC = ("Acceptance keys, same format as scripts/pack_keys.json: each item is a list of groups; "
            "every group must match; a group is a list of alternatives (lowercase substrings after "
            "normalizing). 'REFUSE' means the answer must say the document does not contain it. "
            "Items not listed use WER (transcription), the unit tests (code) or the raw reference.")


def norm(s):
    # Same normalization as scripts/eval_pack.py:norm, so keys match what the scorer compares.
    s = unicodedata.normalize("NFKC", s or "").lower()
    s = s.replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", s).strip()


def pack_source_ids():
    return [a.get("source_ids", {}) for a in json.loads((PACK / "answers.json").read_text())]


def hf_file(repo, filename, sub):
    from huggingface_hub import hf_hub_download
    return hf_hub_download(repo, filename, repo_type="dataset", revision=REVISIONS[repo],
                           local_dir=str(RAW / sub))


def read_parquet(path, columns=None):
    import pyarrow.parquet as pq
    return pq.read_table(path, columns=columns).to_pylist()


def in_memory(path):
    # Reads of the 400 MB VizWiz shards on the Docker Desktop bind mount fail with ENOMEM at
    # random offsets while the host is busy (pyarrow's one large read always failed); small
    # reads with retries get through.
    import os
    import time
    import pyarrow as pa
    buf = bytearray(os.path.getsize(path))
    view = memoryview(buf)
    with open(path, "rb", buffering=0) as f:
        n = 0
        while n < len(buf):
            for attempt in range(60):
                try:
                    f.seek(n)
                    got = f.readinto(view[n:n + (1 << 18)])
                    break
                except OSError as e:
                    if e.errno != 12 or attempt == 59:
                        raise
                    time.sleep(1)
            n += got
    return pa.BufferReader(pa.py_buffer(buf))


def write_set(name, items, answers, keys, source_md):
    d = OUT / name
    (d / "items.json").write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (d / "answers.json").write_text(json.dumps(answers, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (d / "keys.json").write_text(json.dumps({"_doc": KEYS_DOC, **keys}, indent=2, ensure_ascii=False) + "\n",
                                 encoding="utf-8")
    (d / "SOURCE.md").write_text(source_md.strip() + "\n", encoding="utf-8")
    print(f"{name}: {len(items)} items -> {d}")


def fresh_dir(name, *subs):
    d = OUT / name
    if d.exists():
        shutil.rmtree(d)
    for s in subs:
        (d / s).mkdir(parents=True, exist_ok=True)
    return d


def write_crlf(path, text):
    # The practice pack's .txt and test files use CRLF line endings.
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(text)


def clean_raw(sub):
    shutil.rmtree(RAW / sub, ignore_errors=True)


# SQuAD 2.0 dev documents and questions

SQUAD_DOCS = 15
SQUAD_ANSWERABLE_PER_DOC = 3
SQUAD_MIN_CHARS, SQUAD_MAX_CHARS = 2500, 5000
SQUAD_MAX_SPAN_WORDS = 5
STOP = set("the a an of in on at to for by with from and or is was were are be been what which who whom whose "
           "when where why how did does do that this these those as its it his her their they he she than "
           "into after before during not no".split())
# Unanswerable questions read by eye against their whole joined window and rejected because the
# window answers them (SQuAD marks them unanswerable only for their own paragraph).
SQUAD_REJECT = {
    "5a6690d6f038b7001ab0bff2": "the monopoly's reaction to Roberts is stated (AT&T, not BBN)",
    "5ad24600d7d075001a428aca": "Paris and provinces death tolls are both given",
    "5ad04b2377cf76001a686f94": "says most districts are in northern San Diego",
    "5a7b325021c2de001afe9daa": "African-American community is named for the neighborhood beside Downtown",
    "5ad54e7c5b96ef001a10ac79": "garbled question text",
    "5ad0403c77cf76001a686eed": "same document answers who the bill is submitted to",
    "5ad051be77cf76001a686fd0": "rugby is growing in southern California schools",
    "5a580d05770dc0001aeeff99": "magma chamber evolution is mentioned",
    "5ad40bd9604f3c001a400039": "the 1294 experiment is described as doomed",
    "5ad56c6b5b96ef001a10ae6f": "garbled question text",
    "5a8359c1e60761001a2eb5f6": "the bands of cilia are called ctenes",
    "5ad29b43d7d075001a429bca": "start and end of the Ice Ages are both given",
    "5ad3fb6e604f3c001a3ffb60": "the Marches came under William's barons",
    "5ad40cac604f3c001a40008b": "names the Yuan loyalist commander",
}
# Spans that make a useless substring key ("not" from a yes/no question).
SQUAD_BAD_SPANS = {"no", "not", "yes", "none"}


def squad_alts(r):
    """Key alternatives for an answerable question, or None if no fair key is left."""
    spans = r["answers"]["text"]
    if min(len(t.split()) for t in spans) > SQUAD_MAX_SPAN_WORDS or {norm(t) for t in spans} & SQUAD_BAD_SPANS:
        return None
    q = norm(r["question"])
    # A span that is part of the question ("ctenophores" for "Ctenophores and cnidarians are
    # classified as what?") matches any answer that repeats the question.
    alts = {a for a in (norm(t).rstrip(".,;") for t in spans) if a and a not in q}
    # A span like "1368–1644" (en dash) is also accepted with "-" or " to " in its place.
    alts |= {a.replace("–", sep) for a in alts if "–" in a for sep in ("-", " to ")}
    return sorted(alts) or None


def content_words(s):
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP and len(w) > 2}


def font_chars():
    from fontTools.ttLib import TTFont
    return set(TTFont(FONT).getBestCmap()) & set(TTFont(FONT_BOLD).getBestCmap())


def write_pdf(path, title, paras):
    import datetime
    from fpdf import FPDF
    pdf = FPDF(format="letter", unit="pt")
    pdf.set_creation_date(datetime.datetime(2026, 11, 18, tzinfo=datetime.timezone.utc))
    pdf.set_margins(72, 72, 72)
    pdf.set_auto_page_break(True, 72)
    pdf.add_font("DejaVu", "", FONT)
    pdf.add_font("DejaVu", "B", FONT_BOLD)
    pdf.add_page()
    pdf.set_font("DejaVu", "B", 14)
    pdf.multi_cell(0, 18, title, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    pdf.set_font("DejaVu", "", 11)
    for p in paras:
        pdf.multi_cell(0, 15, p, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(7)
    pdf.output(str(path))
    return pdf.pages_count


def build_squad():
    rows = read_parquet(hf_file("rajpurkar/squad_v2", "squad_v2/validation-00000-of-00001.parquet", "squad"))
    pack_titles = {s["title"] for s in pack_source_ids() if s.get("dataset") == "squad"}
    pack_qids = {s["qid"] for s in pack_source_ids() if s.get("dataset") == "squad"}
    articles = {}
    for r in rows:
        paras = articles.setdefault(r["title"], {})
        paras.setdefault(r["context"], []).append(r)
    glyphs = font_chars()
    rng = random.Random(SEED)
    titles = sorted(t for t in articles if t not in pack_titles)
    rng.shuffle(titles)
    d = fresh_dir("squad", "text")
    items, answers, keys, notes = [], [], {}, []
    n_doc = 0
    for title in titles:
        if n_doc == SQUAD_DOCS:
            break
        ctxs = list(articles[title])
        starts = list(range(len(ctxs)))
        # One stream per article, so a SQUAD_REJECT entry changes only its own document.
        rng = random.Random(f"{SEED}-{title}")
        rng.shuffle(starts)
        chosen = None
        for s in starts:
            win, total = [], 0
            for k in range(s, len(ctxs)):
                if total + len(ctxs[k]) > SQUAD_MAX_CHARS:
                    break
                win.append(k)
                total += len(ctxs[k]) + 2
            if total < SQUAD_MIN_CHARS or len(win) < 2:
                continue
            doc_chars = set("".join(ctxs[k] for k in win) + title)
            if any(ord(c) not in glyphs for c in doc_chars if not c.isspace()):
                continue
            ans, unans = [], []
            for k in win:
                others = [content_words(ctxs[j]) for j in win if j != k]
                for r in articles[title][ctxs[k]]:
                    if r["id"] in pack_qids:
                        continue
                    spans = r["answers"]["text"]
                    if spans:
                        if squad_alts(r):
                            ans.append((k, r))
                    elif r["id"] not in SQUAD_REJECT:
                        cw = content_words(r["question"])
                        # A question written against paragraph k may be answered by another paragraph
                        # of the window; drop it when most of its content words sit in one of them.
                        if cw and max(len(cw & o) / len(cw) for o in others) < 0.5:
                            unans.append((k, r))
            by_para = {}
            for k, r in ans:
                by_para.setdefault(k, []).append(r)
            if len(by_para) < 2 or len(ans) < SQUAD_ANSWERABLE_PER_DOC or not unans:
                continue
            pick = []
            paras_order = list(by_para)
            rng.shuffle(paras_order)
            while len(pick) < SQUAD_ANSWERABLE_PER_DOC:
                for k in paras_order:
                    left = [r for r in by_para[k] if r not in [p for _, p in pick]]
                    if left and len(pick) < SQUAD_ANSWERABLE_PER_DOC:
                        pick.append((k, rng.choice(left)))
            pick.append(rng.choice(unans))
            chosen = (win, pick)
            break
        if chosen is None:
            notes.append(f"article '{title}' skipped: no window fits the limits")
            continue
        n_doc += 1
        win, pick = chosen
        doc_id = f"xs_txt_doc_{n_doc:02d}"
        human_title = title.replace("_", " ")
        paras = [ctxs[k].strip() for k in win]
        text = human_title + "\n\n" + "\n\n".join(paras) + "\n"
        write_crlf(d / "text" / f"{doc_id}.txt", text)
        pages = write_pdf(d / "text" / f"{doc_id}.pdf", human_title, paras)
        print(f"{doc_id} {title} paragraphs {win[0]}-{win[-1]} chars {len(text)} pages {pages}")
        for k, r in pick:
            iid = f"xs_txt_{len(items) + 1:03d}"
            spans = r["answers"]["text"]
            items.append({"id": iid, "modality": "text", "file": f"text/{doc_id}.txt",
                          "question": r["question"].strip()})
            answers.append({
                "id": iid, "modality": "text",
                "reference_answer": spans[0] if spans else "The document does not say.",
                "answerable": bool(spans), "difficulty": "unrated",
                "source": f"SQuAD 2.0 dev, article '{title}', paragraph {k}, question id {r['id']}",
                "license": "CC BY-SA 4.0",
                "attribution": f"Wikipedia article \"{human_title}\" via SQuAD 2.0",
                "transform": "original SQuAD question" + ("" if spans else "; unanswerable"),
                "source_ids": {"dataset": "squad", "title": title, "qid": r["id"], "doc": doc_id}})
            if spans:
                keys[iid] = [squad_alts(r)]
            else:
                keys[iid] = ["REFUSE"]
    clean_raw("squad")
    n_un = sum(1 for a in answers if not a["answerable"])
    write_set("squad", items, answers, keys, f"""
# Extra pack: SQuAD 2.0 dev documents

{n_doc} documents, {len(items)} questions ({n_un} unanswerable, gold answer "The document does not say.").

- Source: SQuAD 2.0 dev set, https://huggingface.co/datasets/rajpurkar/squad_v2 (validation split,
  revision {REVISIONS['rajpurkar/squad_v2'][:12]}). Rajpurkar et al., ACL 2018. Text from Wikipedia.
- License: CC BY-SA 4.0. Derivatives of these documents must be shared under the same license.
- Format: same as `Kaggle Data/text/`: a `.txt` (title line, blank line, paragraphs separated by blank
  lines) and a `.pdf` of the same text with embedded text (DejaVu Sans, US Letter, made with fpdf2).
- Picking (seed {SEED}, scripts/make_extra_data.py): articles used by the practice pack are excluded
  entirely. For each of {SQUAD_DOCS} shuffled articles, a random run of consecutive paragraphs between
  {SQUAD_MIN_CHARS} and {SQUAD_MAX_CHARS} characters (all at most 3 PDF pages). Per document
  {SQUAD_ANSWERABLE_PER_DOC} answerable questions spread over different paragraphs, with a gold span of at
  most {SQUAD_MAX_SPAN_WORDS} words (so a substring key is fair), and 1 unanswerable question.
- Unanswerable questions: SQuAD marks them unanswerable for their own paragraph only. Questions whose
  content words mostly (50 percent or more) appear in another paragraph of the same document are dropped,
  and the picks were read by eye against the joined text; rejects are listed in `SQUAD_REJECT` in the script.
- Keys: one group per answerable question with every gold answer span (lowercased) as alternatives;
  `REFUSE` for unanswerable ones. The scorer also fails a refusal on an answerable question. Spans
  that appear inside the question are left out of the key (they match any answer that repeats the
  question), and questions with a yes/no style span ("not") are not used. A span with an en dash
  also accepts a hyphen or "to" in its place.
{chr(10).join('- ' + n for n in notes)}
""")


# HumanEval and MBPP

def pack_question_prefix():
    q = next(i["question"] for i in json.loads((PACK / "items.json").read_text()) if i["modality"] == "code")
    return "Complete this Python function:\n\n"if q.startswith("Complete this Python function:\n\n") else None


def build_humaneval():
    prefix = pack_question_prefix()
    assert prefix, "practice pack code phrasing changed"
    rows = read_parquet(hf_file("openai/openai_humaneval", "openai_humaneval/test-00000-of-00001.parquet",
                                "humaneval"))
    pack_items = {i["id"]: i for i in json.loads((PACK / "items.json").read_text())}
    pack_tasks = {}
    for a in json.loads((PACK / "answers.json").read_text()):
        if a.get("source_ids", {}).get("dataset") == "humaneval":
            pack_tasks[a["source_ids"]["task_id"]] = a["id"]

    def test_file(r):
        return r["test"].rstrip("\n") + f"\n\n\ncheck({r['entry_point']})\n"

    # The pack's own items must come out byte-identical, or the format here is wrong.
    for r in rows:
        if r["task_id"] in pack_tasks:
            pid = pack_tasks[r["task_id"]]
            assert pack_items[pid]["question"] == prefix + r["prompt"], pid
            pack_test = (PACK / "code" / "tests" / f"{pid}_test.py").read_bytes().decode()
            assert pack_test.replace("\r\n", "\n") == test_file(r), pid
    d = fresh_dir("humaneval", "code/tests")
    items, answers = [], []
    for r in sorted(rows, key=lambda r: int(r["task_id"].split("/")[1])):
        if r["task_id"] in pack_tasks:
            continue
        iid = f"xh_code_{len(items) + 1:03d}"
        items.append({"id": iid, "modality": "code", "file": None, "question": prefix + r["prompt"]})
        answers.append({
            "id": iid, "modality": "code", "reference_answer": r["prompt"] + r["canonical_solution"],
            "entry_point": r["entry_point"], "difficulty": "unrated",
            "source": f"HumanEval {r['task_id']}", "license": "MIT",
            "attribution": "OpenAI HumanEval (Chen et al. 2021)",
            "transform": "prompt verbatim; tests are the original HumanEval tests",
            "source_ids": {"dataset": "humaneval", "task_id": r["task_id"]}})
        write_crlf(d / "code" / "tests" / f"{iid}_test.py", test_file(r))
    clean_raw("humaneval")
    write_set("humaneval", items, answers, {}, f"""
# Extra pack: HumanEval

{len(items)} code items: every HumanEval problem except the {len(pack_tasks)} in the practice pack.

- Source: https://huggingface.co/datasets/openai/openai_humaneval (test split, revision
  {REVISIONS['openai/openai_humaneval'][:12]}). Chen et al., "Evaluating Large Language Models Trained on
  Code", 2021.
- License: MIT.
- Format: same as the practice pack. `question` is "Complete this Python function:" plus a blank line plus
  the original prompt; `code/tests/<id>_test.py` is the original test code followed by
  `check(<entry_point>)`. The script checks that this recipe reproduces the 20 pack items byte for byte.
- `reference_answer` is the prompt plus the canonical solution; every reference passes its test file
  (`make_extra_data.py check humaneval`).
- No keys: eval_pack.py scores code by running the test file.
""")


MBPP_COUNT = 30


def build_mbpp():
    prefix = pack_question_prefix()
    rows = read_parquet(hf_file("google-research-datasets/mbpp", "sanitized/test-00000-of-00001.parquet", "mbpp"))
    rng = random.Random(SEED)
    rng.shuffle(rows)
    d = fresh_dir("mbpp", "code/tests")
    items, answers, skipped = [], [], Counter()
    for r in rows:
        if len(items) == MBPP_COUNT:
            break
        defs = re.findall(r"^def\s+(\w+)\s*\((.*?)\)\s*(?:->[^:]*)?:", r["code"], re.M)
        if len(defs) != 1:
            skipped["not exactly one top-level function"] += 1
            continue
        name, args = defs[0]
        tests = list(r["test_list"])
        if not all(re.search(rf"\b{re.escape(name)}\s*\(", t) for t in tests):
            skipped["tests do not call the function"] += 1
            continue
        text = r["prompt"].strip()
        example = tests[0].strip()
        if example.startswith("assert "):
            example = example[len("assert "):]
        if '"""' in text + example or "\\" in text + example:
            skipped["quotes or backslashes in the docstring"] += 1
            continue
        imports = [l for l in r["code"].splitlines() if re.match(r"(import|from)\s", l)]
        prompt = ("\n".join(imports) + "\n\n" if imports else "") + \
            f"\ndef {name}({args}):\n    \"\"\"{text}\n    Example: {example}\n    \"\"\"\n"
        body = "\n".join("    " + re.sub(rf"\b{re.escape(name)}\s*\(", "candidate(", t.strip()) for t in tests)
        test = "".join(i + "\n" for i in r["test_imports"]) + \
            f"\n\ndef check(candidate):\n{body}\n\n\ncheck({name})\n"
        iid = f"xm_code_{len(items) + 1:03d}"
        items.append({"id": iid, "modality": "code", "file": None, "question": prefix + prompt})
        answers.append({
            "id": iid, "modality": "code", "reference_answer": r["code"], "entry_point": name,
            "difficulty": "unrated", "source": f"MBPP (sanitized) task_id {r['task_id']}",
            "license": "CC BY 4.0", "attribution": "Google Research MBPP (Austin et al. 2021)",
            "transform": "description and first test as a docstring under the reference signature; "
                         "the original asserts wrapped in check(candidate)",
            "source_ids": {"dataset": "mbpp", "task_id": int(r["task_id"])}})
        write_crlf(d / "code" / "tests" / f"{iid}_test.py", test)
    clean_raw("mbpp")
    skip_txt = ", ".join(f"{v} {k}" for k, v in skipped.items()) or "none"
    write_set("mbpp", items, answers, {}, f"""
# Extra pack: MBPP

{len(items)} code items from MBPP, converted to the practice pack's HumanEval-style format.

- Source: https://huggingface.co/datasets/google-research-datasets/mbpp (config `sanitized`, test split,
  revision {REVISIONS['google-research-datasets/mbpp'][:12]}). Austin et al., "Program Synthesis with Large
  Language Models", 2021.
- License: CC BY 4.0.
- Conversion: `question` is "Complete this Python function:" plus a blank line plus a prompt built from
  the reference solution's imports and signature, with the task description and the first test (as an
  example) in the docstring. The test file wraps the original asserts in `check(candidate)` and ends with
  `check(<entry_point>)`, like `Kaggle Data/code/tests/`. MBPP tests are fewer and the first one is shown
  in the prompt, so this set is easier to pass by accident than HumanEval.
- Picking: seed {SEED} shuffle of the 257 sanitized test tasks, first {MBPP_COUNT} that convert cleanly.
  Skipped on the way: {skip_txt}.
- Every reference solution passes its test file (`make_extra_data.py check mbpp`).
""")


# VizWiz-VQA val photos

VIZWIZ_COUNT = 80
# One val shard holds about 72 qualifying questions, so two are needed for 80.
VIZWIZ_SHARDS = ["data/val-00000-of-00005-7775fd61bc6a3d98.parquet",
                 "data/val-00001-of-00005-18e4fb673cfdd7cb.parquet"]


def clean_vqa(a):
    return re.sub(r"\s+", " ", a.strip().lower()).rstrip(".")


def vizwiz_alts(question, counts):
    """Key alternatives, or None when no fair substring key exists."""
    q = norm(question)
    alts = set()
    for a, c in counts.most_common():
        if c < 3 or a in ("unanswerable", "unsuitable", "unsuitable image"):
            continue
        a = norm(a)
        if a.isdigit():
            alts |= {a, f"#{int(a)}"}
        # "t" or "on" match nearly any answer; "caffeinated" sits inside "caffeinated or
        # decaffeinated?", which an answer may repeat.
        elif len(a) >= 3 and a not in q:
            alts.add(a)
    return sorted(alts) or None


def build_vizwiz():
    from PIL import Image
    import pyarrow.parquet as pq
    paths = [hf_file("lmms-lab/VizWiz-VQA", s, "vizwiz") for s in VIZWIZ_SHARDS]
    pack_q = {s["question_id"] for s in pack_source_ids() if s.get("dataset") == "vizwiz"}
    cands, n_rows, n_weak = [], 0, 0
    for s, path in enumerate(paths):
        meta = read_parquet(path, columns=["question_id", "question", "answers", "category"])
        n_rows += len(meta)
        for i, r in enumerate(meta):
            if r["question_id"] in pack_q or r["category"] in ("yes/no", "unanswerable"):
                continue
            counts = Counter(clean_vqa(a) for a in r["answers"])
            top, n = counts.most_common(1)[0]
            if n < 6 or top in ("unanswerable", "unsuitable", "unsuitable image", ""):
                continue
            alts = vizwiz_alts(r["question"], counts)
            if alts is None:
                n_weak += 1
                continue
            cands.append(((s, i), r, counts, alts))
    rng = random.Random(SEED)
    pick = sorted(rng.sample(cands, VIZWIZ_COUNT), key=lambda c: c[1]["question_id"])
    want = {c[0] for c in pick}
    images = {}
    for s, path in enumerate(paths):
        base = 0
        for batch in pq.ParquetFile(in_memory(path)).iter_batches(batch_size=32, columns=["image"]):
            col = batch.column("image").to_pylist()
            for j, im in enumerate(col):
                if (s, base + j) in want:
                    images[(s, base + j)] = im["bytes"]
            base += len(col)
    d = fresh_dir("vizwiz", "image")
    items, answers, keys = [], [], {}
    for n_item, (i, r, counts, alts) in enumerate(pick, 1):
        iid = f"xv_img_{n_item:03d}"
        im = Image.open(io.BytesIO(images[i])).convert("RGB")
        if max(im.size) > 1280:
            s = 1280 / max(im.size)
            im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
        im.save(d / "image" / f"{iid}.jpg", "JPEG", quality=90)
        top, n = counts.most_common(1)[0]
        items.append({"id": iid, "modality": "image", "file": f"image/{iid}.jpg", "question": r["question"]})
        answers.append({
            "id": iid, "modality": "image", "reference_answer": top, "difficulty": "unrated",
            "source": f"VizWiz-VQA val {r['question_id']} ({n}/10 annotators agree)",
            "license": "CC BY 4.0",
            "attribution": f"VizWiz-VQA, Gurari et al. 2018 (lmms-lab/VizWiz-VQA revision "
                           f"{REVISIONS['lmms-lab/VizWiz-VQA'][:12]})",
            "transform": "resized to at most 1280 px on the long side, JPEG quality 90, metadata stripped",
            "source_ids": {"dataset": "vizwiz", "question_id": r["question_id"], "category": r["category"],
                           "answers": r["answers"]}})
        keys[iid] = [alts]
    clean_raw("vizwiz")
    cats = Counter(c[1]["category"] for c in pick)
    write_set("vizwiz", items, answers, keys, f"""
# Extra pack: VizWiz-VQA val photos

{VIZWIZ_COUNT} photos taken by blind users, with their original questions. Categories: {dict(cats)}.

- Source: https://huggingface.co/datasets/lmms-lab/VizWiz-VQA, val split, the first two of five
  shards ({n_rows} of the 4319 val questions), revision {REVISIONS['lmms-lab/VizWiz-VQA'][:12]}, the same revision as the
  practice pack. Gurari et al., "VizWiz Grand Challenge", CVPR 2018.
- License: CC BY 4.0.
- Picking (seed {SEED}): practice-pack question ids excluded; yes/no and unanswerable categories skipped;
  the most common answer (lowercased, trailing period dropped) must be given by at least 6 of 10
  annotators and not be "unanswerable" or "unsuitable". {len(cands)} questions qualified, {VIZWIZ_COUNT}
  sampled. {n_weak} more were dropped because no fair substring key was left (see Keys).
- Transform: RGB, long side at most 1280 px (Lanczos, no upscaling), JPEG quality 90, no metadata.
- Keys: one group with the majority answer plus every other answer given by at least 3 annotators.
  Answers that are digits also accept `#N` (first number in the reply). Answers shorter than 3
  characters ("t", "on") and answers that appear inside the question ("caffeinated" for "Is this
  caffeinated or decaffeinated?") are not used as keys; an item with no key left is skipped.
  `source_ids.answers` keeps all 10 raw annotations for reading failures by eye.
""")


# LibriSpeech test-clean speech

LIBRI_TRANSCRIBE = 20
# Content questions written by hand from the transcripts printed by `librispeech --list`.
# utterance id -> (question, reference answer, key groups)
LIBRI_QUESTIONS = {
    "1188-133604-0044": ("What do they fly instead of kites?", "Falcons.", [["falcon"]]),
    "4446-2271-0004": ("Who looked with perplexity up into the top of the hansom?", "Alexander Mainhall.",
                       [["mainhall", "main hall", "alexander"]]),
    "6930-75918-0009": ("What is the name of the person being told they are mistaken?", "Raoul.",
                        [["raoul", "raul"]]),
    "260-123288-0002": ("What is the atmosphere charged with?", "Vapours.", [["vapo"]]),
    "1580-141084-0048": ("Where was the listener left, according to the speaker?", "In the room.", [["room"]]),
    "4970-29093-0007": ("What kind of foundation does the ambition usually have?", "A shallow foundation.",
                        [["shallow"]]),
    "3570-5695-0003": ("In which class is this point found at present?", "The lower middle class.",
                       [["lower middle"]]),
    "4077-13751-0006": ("Toward what were their eyes turned in anticipation?", "Toward the evening sun.",
                        [["evening sun", "west"]]),
    "237-134493-0003": ("How many farmhouses can one count from the graveyard gate?", "A dozen.",
                        [["dozen", "twelve", "#12"]]),
    "8230-279154-0043": ("What kind of judgment is mentioned in the recording?", "A judgment of recognition.",
                         [["recognition"]]),
    "5105-28241-0011": ("To which country did his thoughts speed away?", "France.", [["france"]]),
    "8463-294828-0031": ("Where did one of the sailors lead the speaker?", "To the afterdeck.",
                         [["afterdeck", "after deck", "after-deck"]]),
    "5683-32879-0010": ("What did Rachel's nature recoil from?", "Deceit.", [["deceit", "decept"]]),
    "5142-33396-0019": ("Where does the speaker say it is better to live?", "On the sea.", [["sea"]]),
    "2300-131720-0009": ("On what kind of circuits was it not found feasible to operate motors?",
                         "Alternating current circuits.", [["alternating"]]),
    "8555-292519-0000": ("What are the bands of color compared to?", "Rainbow veils upon a bubble's dome.",
                         [["rainbow", "veil", "bubble"]]),
    "4507-16021-0049": ("How many days out of a hundred are wholly joyous and sunny?", "Hardly one.",
                        [["#1", "hardly one", "only one", "barely one", "one day"]]),
    "1221-135766-0007": ("Who is the loving mother of this one child?", "Hester Prynne.",
                         [["hester", "prynne"]]),
    "2830-3980-0048": ("What was done to him before he died?", "He was crucified.", [["crucif"]]),
    "1284-1180-0008": ("What did Unc and Ojo eat at noon?", "The last of the bread.", [["bread"]]),
}


def libri_sentence(t):
    return t.lower().capitalize() + "."


def build_librispeech(list_only=False):
    import numpy as np
    import soundfile as sf
    import pyarrow.parquet as pq
    path = hf_file("openslr/librispeech_asr", "all/test.clean/0000.parquet", "librispeech")
    pack_u = {s["utterance"] for s in pack_source_ids() if s.get("dataset") == "librispeech"}
    meta = [r for r in read_parquet(path, columns=["id", "text", "speaker_id", "chapter_id"])]
    rng = random.Random(SEED)
    pool = [r for r in meta if r["id"] not in pack_u]
    rng.shuffle(pool)
    # Transcribe items: first 20 of the shuffle with 6 to 35 words, one per speaker.
    trans, seen = [], set()
    for r in pool:
        if len(trans) < LIBRI_TRANSCRIBE and r["speaker_id"] not in seen and 6 <= len(r["text"].split()) <= 35:
            trans.append(r)
            seen.add(r["speaker_id"])
    if list_only:
        used = {r["id"] for r in trans}
        for r in pool:
            if r["id"] not in used and r["speaker_id"] not in seen and 15 <= len(r["text"].split()) <= 60:
                print(r["id"], "|", libri_sentence(r["text"]))
                seen.add(r["speaker_id"])
        return
    qrows = [r for r in meta if r["id"] in LIBRI_QUESTIONS]
    assert len(qrows) == len(LIBRI_QUESTIONS), "unknown utterance id in LIBRI_QUESTIONS"
    assert not {r["id"] for r in qrows} & {r["id"] for r in trans}
    want = {r["id"] for r in trans + qrows}
    audio = {}
    pf = pq.ParquetFile(in_memory(path))
    for batch in pf.iter_batches(batch_size=64, columns=["id", "audio"]):
        for x in batch.to_pylist():
            if x["id"] in want:
                audio[x["id"]] = x["audio"]["bytes"]
    d = fresh_dir("librispeech", "audio")
    items, answers, keys, durs = [], [], {}, []
    for kind, rows in (("transcribe", trans), ("question", qrows)):
        for r in rows:
            iid = f"xl_aud_{len(items) + 1:03d}"
            x, sr = sf.read(io.BytesIO(audio[r["id"]]), dtype="float32")
            assert sr == 16000 and x.ndim == 1, (r["id"], sr, x.shape)
            durs.append(len(x) / sr)
            sf.write(d / "audio" / f"{iid}.wav", np.clip(x, -1, 1), 16000, subtype="PCM_16")
            sent = libri_sentence(r["text"])
            if kind == "transcribe":
                q, ref = "Transcribe this audio.", sent
            else:
                q, ref, groups = LIBRI_QUESTIONS[r["id"]]
                keys[iid] = groups
            items.append({"id": iid, "modality": "audio", "file": f"audio/{iid}.wav", "question": q})
            answers.append({
                "id": iid, "modality": "audio", "reference_answer": ref, "transcript": sent,
                "difficulty": "unrated",
                "source": f"LibriSpeech test-clean {r['id']} (speaker {r['speaker_id']})",
                "license": "CC BY 4.0",
                "attribution": "LibriSpeech, Panayotov et al. 2015 (LibriVox public-domain recording)",
                "transform": "converted from FLAC to 16 kHz mono PCM WAV",
                "source_ids": {"dataset": "librispeech", "speaker": str(r["speaker_id"]), "utterance": r["id"]}})
    clean_raw("librispeech")
    write_set("librispeech", items, answers, keys, f"""
# Extra pack: LibriSpeech test-clean speech

{len(items)} utterances: {len(trans)} "Transcribe this audio." and {len(qrows)} content questions.
Durations {min(durs):.1f} to {max(durs):.1f} s.

- Source: LibriSpeech test-clean, https://huggingface.co/datasets/openslr/librispeech_asr
  (`all/test.clean/0000.parquet`, revision {REVISIONS['openslr/librispeech_asr'][:12]}), the same audio
  as openslr.org resource 12. Panayotov et al., ICASSP 2015.
- License: CC BY 4.0 (LibriVox recordings are public domain).
- Picking (seed {SEED}): practice-pack utterances excluded, a shuffle of the rest. Transcribe items: the
  first {LIBRI_TRANSCRIBE} with 6 to 35 words, one per speaker. Question items: utterances of other speakers
  with 15 to 60 words, read by hand; a question was written only where the transcript answers it plainly.
- Transform: FLAC decoded to 16 kHz mono 16-bit PCM WAV.
- Reference transcripts are the LibriSpeech text lowercased with the first letter capitalized and a final
  period, like the practice pack. Transcribe items are scored by WER (pass at 0.10 or less).
- Keys (question items only): hand-written keyword groups, every group must appear in the answer.
""")


# ESC-50 environmental sounds

ESC_PER_CLASS = 2
# class -> (reference answer, key alternatives). Alternatives are substrings, chosen to avoid the
# obvious collisions with other ESC-50 classes (crow vs rooster crowing, fire vs fireworks,
# saw vs chainsaw, hen inside "when").
ESC_CLASSES = {
    "dog": ("Dog barking.", ["dog", "bark", "puppy"]),
    "rooster": ("Rooster crowing.", ["rooster", "cockerel", "cock-a-doodle"]),
    "pig": ("Pig oinking.", ["pig", "oink", "hog", "swine"]),
    "cow": ("Cow mooing.", ["cow", "mooing", "moo.", "cattle"]),
    "frog": ("Frog croaking.", ["frog", "croak", "toad"]),
    "cat": ("Cat meowing.", ["cat", "meow", "kitten"]),
    "hen": ("Hen clucking.", ["chicken", "cluck", " hen", "hen."]),
    "insects": ("Insects buzzing.", ["insect", "buzz", "bees", " bee", "mosquito", " fly", "flies"]),
    "sheep": ("Sheep bleating.", ["sheep", "bleat", "baa", "lamb"]),
    "crow": ("Crow cawing.", ["crow ", "crow.", "crows", "caw", "raven"]),
    "rain": ("Rain.", ["rain", "downpour", "drizzl"]),
    "sea_waves": ("Ocean waves.", ["ocean", "sea", "wave", "surf"]),
    "crackling_fire": ("Crackling fire.", ["crackl", "fire ", "fire.", "fireplace", "campfire", "flame", "burning"]),
    "crickets": ("Crickets chirping.", ["cricket"]),
    "chirping_birds": ("Birds chirping.", ["bird", "tweet"]),
    "water_drops": ("Water dripping.", ["drip", "droplet", "water drop", "drops"]),
    "wind": ("Wind blowing.", ["wind", "gust", "breeze"]),
    "pouring_water": ("Water pouring.", ["pour"]),
    "toilet_flush": ("Toilet flushing.", ["toilet", "flush"]),
    "thunderstorm": ("Thunderstorm.", ["thunder"]),
    "crying_baby": ("Baby crying.", ["baby", "infant", "crying"]),
    "sneezing": ("Sneezing.", ["sneez"]),
    "clapping": ("Clapping.", ["clap", "applause"]),
    "breathing": ("Breathing.", ["breath", "inhal", "exhal", "panting"]),
    "coughing": ("Coughing.", ["cough"]),
    "footsteps": ("Footsteps.", ["footstep", "walking", "steps"]),
    "laughing": ("Laughing.", ["laugh", "giggl", "chuckl"]),
    "brushing_teeth": ("Brushing teeth.", ["teeth", "tooth"]),
    "snoring": ("Snoring.", ["snor"]),
    "drinking_sipping": ("Drinking or sipping.", ["drink", "sip", "slurp", "gulp", "swallow"]),
    "door_wood_knock": ("Knocking on a door.", ["knock"]),
    "mouse_click": ("Mouse clicking.", ["mouse", "click"]),
    "keyboard_typing": ("Keyboard typing.", ["typing", "keyboard", "typewriter"]),
    "door_wood_creaks": ("Door creaking.", ["creak", "squeak"]),
    "can_opening": ("Can opening.", ["can open", "can being open", "opening a can", "opening of a can",
                                     "soda", "beer can", "tin can", "pull tab", "fizz", "carbonat"]),
    "washing_machine": ("Washing machine.", ["washing machine", "washer", "laundry", "spin cycle"]),
    "vacuum_cleaner": ("Vacuum cleaner.", ["vacuum", "hoover"]),
    "clock_alarm": ("Alarm clock ringing.", ["alarm"]),
    "clock_tick": ("Clock ticking.", ["tick"]),
    "glass_breaking": ("Glass breaking.", ["glass", "shatter", "smash"]),
    "helicopter": ("Helicopter.", ["helicopter", "chopper"]),
    "chainsaw": ("Chainsaw.", ["chainsaw", "chain saw"]),
    "siren": ("Siren.", ["siren", "ambulance", "police car", "fire truck", "fire engine"]),
    "car_horn": ("Car horn.", ["horn", "honk"]),
    "engine": ("Engine running.", ["engine", "motor", "idling"]),
    "train": ("Train.", ["train", "railway", "locomotive"]),
    "church_bells": ("Church bells ringing.", ["bell", "chime"]),
    "airplane": ("Airplane.", ["airplane", "plane", "aircraft", "jet"]),
    "fireworks": ("Fireworks.", ["firework"]),
    "hand_saw": ("Hand saw.", ["hand saw", "handsaw", "sawing", " saw ", " saw."]),
}


def build_esc50():
    import csv
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly
    raw = RAW / "esc50"
    raw.mkdir(parents=True, exist_ok=True)
    base = f"https://raw.githubusercontent.com/karolpiczak/ESC-50/{ESC50_COMMIT}"
    meta_path = raw / "esc50.csv"
    urllib.request.urlretrieve(f"{base}/meta/esc50.csv", meta_path)
    rows = list(csv.DictReader(open(meta_path, encoding="utf-8")))
    assert set(r["category"] for r in rows) == set(ESC_CLASSES), "class list mismatch"
    pack = [s for s in pack_source_ids() if s.get("dataset") in ("esc10", "esc50")]
    pack_src = {s["src_file"] for s in pack}
    rng = random.Random(SEED)
    pick = []
    for cls in sorted(ESC_CLASSES):
        # Clips cut from a Freesound recording used by the pack are near duplicates, so skip them too.
        pool = sorted((r for r in rows if r["category"] == cls and r["src_file"] not in pack_src),
                      key=lambda r: r["filename"])
        rng.shuffle(pool)
        got, srcs = [], set()
        for r in pool:
            if r["src_file"] not in srcs:
                got.append(r)
                srcs.add(r["src_file"])
            if len(got) == ESC_PER_CLASS:
                break
        pick += got
    rng.shuffle(pick)
    d = fresh_dir("esc50", "audio")
    items, answers, keys = [], [], {}
    for n, r in enumerate(pick, 1):
        iid = f"xe_aud_{n:03d}"
        src = raw / r["filename"]
        urllib.request.urlretrieve(f"{base}/audio/{r['filename']}", src)
        x, sr = sf.read(src, dtype="float32")
        if x.ndim > 1:
            x = x.mean(axis=1)
        assert sr == 44100, (r["filename"], sr)
        y = resample_poly(x, 160, 441)
        sf.write(d / "audio" / f"{iid}.wav", np.clip(y, -1, 1), 16000, subtype="PCM_16")
        ref, alts = ESC_CLASSES[r["category"]]
        esc10 = r["esc10"] == "True"
        items.append({"id": iid, "modality": "audio", "file": f"audio/{iid}.wav", "question": "What sound is this?"})
        answers.append({
            "id": iid, "modality": "audio", "reference_answer": ref, "difficulty": "unrated",
            "source": f"ESC-50 {r['filename']} (class {r['category']}, Freesound src_file {r['src_file']})",
            "license": "CC BY 3.0" if esc10 else "CC BY-NC 3.0",
            "attribution": f"Freesound recording {r['src_file']} (https://freesound.org/s/{r['src_file']}/), "
                           "via ESC-50 (Piczak 2015)",
            "transform": "resampled from 44.1 kHz to 16 kHz mono PCM WAV",
            "source_ids": {"dataset": "esc10" if esc10 else "esc50", "src_file": r["src_file"],
                           "filename": r["filename"], "category": r["category"]}})
        keys[iid] = [alts]
    clean_raw("esc50")
    n10 = sum(1 for a in answers if a["license"] == "CC BY 3.0")
    write_set("esc50", items, answers, keys, f"""
# Extra pack: ESC-50 environmental sounds

{len(items)} clips, {ESC_PER_CLASS} from each of the 50 ESC-50 classes, question "What sound is this?".

- Source: ESC-50 from the authors' GitHub, https://github.com/karolpiczak/ESC-50 (commit
  {ESC50_COMMIT[:12]}, `meta/esc50.csv` and `audio/*.wav`). Piczak, "ESC: Dataset for Environmental Sound
  Classification", ACM Multimedia 2015. Recordings from Freesound, credited per clip in answers.json.
- License: the {n10} clips in the ESC-10 subset are CC BY 3.0. The other {len(items) - n10} are
  CC BY-NC 3.0 (non-commercial): fine for our internal evaluation, not for redistribution or for
  anything shipped. Keep this folder local.
- Picking (seed {SEED}): per class, a shuffle of the clips, skipping practice-pack clips and any clip cut
  from a Freesound recording the pack uses, at most one clip per recording.
- Transform: 44.1 kHz to 16 kHz with a polyphase filter (scipy resample_poly 160/441), mono 16-bit PCM.
- Keys: the class name plus plain synonyms as substrings, in `ESC_CLASSES` in the script. They are
  lenient on wording; a few rare cross-class matches remain possible (for example "rain" inside "train").
""")


# Reference checks (run with --network none)

def check(name):
    d = OUT / name
    items = json.loads((d / "items.json").read_text())
    ans = {a["id"]: a for a in json.loads((d / "answers.json").read_text())}
    keys = json.loads((d / "keys.json").read_text())
    assert [i["id"] for i in items] == list(ans), "items and answers out of order"
    bad = 0
    for it in items:
        a = ans[it["id"]]
        if it["file"]:
            assert (d / it["file"]).exists(), it["file"]
        if it["modality"] == "code":
            test = (d / "code" / "tests" / f"{it['id']}_test.py").read_text()
            with tempfile.TemporaryDirectory() as td:
                f = Path(td) / "t.py"
                f.write_text(a["reference_answer"] + "\n\n" + test)
                p = subprocess.run([sys.executable, "-I", str(f)], capture_output=True, text=True,
                                   timeout=20, cwd=td)
            if p.returncode:
                bad += 1
                print("FAIL", it["id"], p.stderr[-300:])
        elif it["modality"] == "text":
            from pypdf import PdfReader
            pdf = d / it["file"].replace(".txt", ".pdf")
            r = PdfReader(str(pdf))
            words = lambda s: re.findall(r"\w+", norm(s))
            got, want = words(" ".join(p.extract_text() for p in r.pages)), words((d / it["file"]).read_text())
            if got != want or len(r.pages) > 3:
                bad += 1
                print("PDF MISMATCH", pdf, len(r.pages), len(got), len(want))
            g = keys[it["id"]]
            doc = norm((d / it["file"]).read_text())
            if g != ["REFUSE"] and not any(alt in doc for alt in g[0]):
                bad += 1
                print("KEY NOT IN DOC", it["id"])
    print(f"{name}: {len(items)} items, {bad} problems")


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    if args[0] == "check":
        for n in args[1:]:
            check(n)
        return
    builders = {"squad": build_squad, "humaneval": build_humaneval, "mbpp": build_mbpp,
                "vizwiz": build_vizwiz, "esc50": build_esc50,
                "librispeech": lambda: build_librispeech("--list" in args)}
    builders[args[0]]()


if __name__ == "__main__":
    main()
