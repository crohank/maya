# 05. Document QA and code execution

Research for the two text capabilities: (A) answer questions about an uploaded
PDF/TXT and say when the answer is not there, (B) write Python from a prompt,
run it, report the result. Hardware and model context: `docs/decisions.md`
(D1, D5). Nothing here was run on the GPU; numbers are from papers, model cards
and file listings unless marked otherwise. UNVERIFIED marks anything not checked
against a primary source in this session.

## Summary of recommendations

| | Recommendation |
|---|---|
| A. Model | `Qwen/Qwen3-VL-4B-Instruct` (Apache-2.0), already used for image reading (D5), NF4, 3.6 GiB peak. Non-thinking (Instruct) variant, not Thinking. |
| A. PDF library | `pypdf` (BSD-3-Clause). Not PyMuPDF (AGPL-3.0). `pypdfium2` (Apache-2.0 or BSD-3-Clause) as a fallback if pypdf extraction is poor on a test file. |
| A. Retrieval | If the document is under about 3,000 tokens, skip retrieval and send the whole text. Otherwise sentence-aware chunks of about 250 tokens, 1 sentence overlap, BM25 top-k 5, sent in document order. |
| A. Abstention | Sentinel `NOT_IN_DOCUMENT`, quote-first answer format, then a code check that the quote appears in the document (normalized match). Failed check means `NOT_IN_DOCUMENT`. BM25 score only as a hard floor (no query term matched at all). |
| B. Model | `Qwen/Qwen3-VL-4B-Instruct` for code too (no second model). Fallback: `Qwen/Qwen2.5-Coder-1.5B-Instruct` (Apache-2.0, about 1.2 GiB NF4, UNVERIFIED estimate). Drop the 7B plan: it does not fit. |
| B. Sandbox | Separate runner container with `--network none`, non-root, read-only root, tmpfs work dir, pids/memory caps; inside it, subprocess with RLIMIT_AS / RLIMIT_CPU / RLIMIT_NPROC / RLIMIT_FSIZE, 10 s wall timeout, `python -I`, an AST deny-list and an audit hook as speed bumps. |

## A. Document QA

### A1. PDF library licenses (checked)

| Library | License | Notes |
|---|---|---|
| PyMuPDF (`pymupdf`, `fitz`) | AGPL-3.0, or paid commercial license from Artifex | AGPL obliges you to release the source of the whole application under AGPL terms if you distribute it or serve it over a network. Fine only if the Maya repo itself is AGPL-3.0. |
| pypdf | BSD-3-Clause | Pure Python, no native deps. Text extraction is decent for born-digital PDFs; weaker on multi-column layouts. |
| pdfplumber | MIT (UNVERIFIED in this session; the search did not cover it) | Built on pdfminer.six (MIT). Good for layout and tables, slower. |
| pypdfium2 | Apache-2.0 or BSD-3-Clause (UNVERIFIED in this session); bundles PDFium (BSD-3) | Fast, good extraction quality, binary wheels. |

**Choice: pypdf.** A public repo under MIT or Apache-2.0 cannot include PyMuPDF
without becoming AGPL. pypdf has no native dependency, which keeps the Docker
image simple. If a practice PDF extracts badly (run-together words, broken
columns), try `pypdfium2` next. Scanned PDFs have no text layer; route those to
the D5 image path (Qwen3-VL OCR per page) instead of failing.

### A2. Chunk size and top-k for short documents

The practice pack documents are short. Two facts decide the design:

- Qwen3-VL-4B has a long native context (256K per the model card, UNVERIFIED for
  NF4 quality at that length). The limit here is VRAM and latency, not context.
- KV cache cost, from Qwen3-4B's text config (36 layers, 8 KV heads, head dim
  128, UNVERIFIED for the VL variant): 2 x 36 x 8 x 128 x 2 bytes = 144 KiB per
  token in bf16. 3,000 tokens is about 0.42 GiB on top of the 3.6 GiB peak.

Recommendation:

1. **Document under about 3,000 tokens: no retrieval.** Send the whole text.
   Retrieval can only lose the answer; it cannot add one. "Lost in the middle"
   (Liu et al., TACL 2024, arXiv 2307.03172) shows degradation with long
   contexts, but its effect is small at a few thousand tokens.
2. **Longer documents: chunk and retrieve.**
   - Split on sentences (a regex on `[.!?]\s+` plus newline blocks is enough),
     pack sentences into chunks of about 250 tokens (about 180 words), overlap 1
     sentence. Smaller chunks (100 to 300 tokens) help BM25 precision for
     factoid questions; larger ones help multi-sentence answers. 250 is a
     middle value, not a measured optimum for this pack (UNVERIFIED; tune on the
     20 practice items with 150 / 250 / 400).
   - BM25 (`rank_bm25.BM25Okapi`, Apache-2.0) over lowercased tokens with
     stopwords removed and simple stemming (or none). Top-k 5, which is about
     1,250 tokens of context.
   - Re-sort the selected chunks into document order before prompting, and tag
     each with its page number so the spoken answer can say "page 3".
   - Also add the neighbor chunk of the top-1 hit if it fits; answers often
     straddle a chunk boundary.

### A3. Making a 4B model abstain

Relevant literature:

- **SQuAD 2.0** (Rajpurkar, Jia, Liang, ACL 2018, "Know What You Don't Know",
  arXiv 1806.03822): 50k unanswerable questions written to look answerable
  against the same paragraph. Established that plausible-but-absent answers are
  the hard case; systems that were strong on SQuAD 1.1 dropped sharply.
- **RGB** (Chen et al., AAAI 2024, arXiv 2309.01431): "negative rejection"
  test where retrieved passages contain no answer. LLMs often answered anyway;
  rejection rates were low even for large models (exact rates UNVERIFIED).
- **FaithEval** (Ming et al., 2024, arXiv 2410.03727): unanswerable,
  inconsistent and counterfactual contexts; models frequently answer from prior
  knowledge instead of the context, and size does not fix it.
- **AbstentionBench** (Kirichenko et al., 2025, arXiv 2506.09038): reasoning
  fine-tuning makes abstention worse (reported average degradation about 24%,
  UNVERIFIED). Practical reading: use the Instruct model, not Thinking, for this
  task.

Prompt pattern that works best with small models (from the above plus standard
practice; the exact gain on this pack is UNVERIFIED until measured):

- Put the sentinel in the system prompt and make it the default: "If the
  document does not state the answer, reply with exactly NOT_IN_DOCUMENT. Do not
  use outside knowledge. A guess is wrong; NOT_IN_DOCUMENT is not."
- **Quote first, answer second.** Fixed format:
  ```
  QUOTE: <one sentence copied word for word from the document>
  ANSWER: <short answer>
  ```
  or the single line `NOT_IN_DOCUMENT`. Forcing the model to produce evidence
  before the answer reduces answers that have no evidence.
- Include two short few-shot examples in the prompt: one answerable, one
  unanswerable where the document mentions the topic but not the asked fact
  (the SQuAD 2.0 style trap). The unanswerable example matters more.
- Greedy decoding (`do_sample=False`), `max_new_tokens` about 120.
- Put the question both before and after the document text; small models weigh
  the end of the prompt most.

### A4. BM25 threshold vs. quote verification

**BM25 threshold: weak.** BM25 scores are not normalized; they scale with query
length, term rarity and document length, so one threshold does not transfer
between documents or questions. A question about a topic the document mentions
but does not answer (the hard case) scores high anyway. Use BM25 only as a
floor: if no query content word appears in the document at all (max score 0),
reply `NOT_IN_DOCUMENT` without calling the model.

**Quote verification: strong and cheap.** After generation:

1. Parse `QUOTE:`. Missing or empty quote with a non-sentinel answer means
   `NOT_IN_DOCUMENT`.
2. Normalize both quote and document (lowercase, unify quotes and hyphens,
   collapse whitespace, strip punctuation). Accept if the normalized quote is a
   substring of the normalized document, or if a fuzzy partial match is at least
   90 (`rapidfuzz.fuzz.partial_ratio`, MIT) to tolerate PDF hyphenation and
   line breaks.
3. Optionally check that the answer's content words occur in the quote; if not,
   the model quoted a related sentence and answered from memory. Treat as
   `NOT_IN_DOCUMENT` or retry once with "Your quote does not contain the
   answer."

This catches the main failure of small models (inventing a fluent answer with
a made-up or paraphrased "quote"). It cannot catch a real quote that does not
support the answer, which step 3 only partly covers.

A second-pass "Does this sentence answer the question? yes/no" call is an
option if step 3 is too loose, at the cost of one more generation (about 0.3 to
0.5 s for a few tokens, UNVERIFIED on this GPU).

### A5. Expected accuracy (UNVERIFIED, estimates until run on the pack)

- Answerable items, full-document mode: 85 to 95% for factoid questions on a
  short clean PDF.
- Unanswerable items: 60 to 75% correct abstention with prompt only; 80 to 90%
  with the quote check. The quote check also turns some correct answers into
  false abstentions (expect 0 to 2 of the answerable items); tune the fuzzy
  threshold on the practice pack.

### A6. Reference (verification step)

```python
import re
from rapidfuzz import fuzz

SENTINEL = "NOT_IN_DOCUMENT"

def norm(s: str) -> str:
    s = s.lower().replace("­", "").replace("-\n", "")
    s = re.sub(r"[‘’“”]", "'", s)
    s = re.sub(r"[^\w\s']", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def check(raw: str, doc: str) -> dict:
    if SENTINEL in raw:
        return {"answer": SENTINEL}
    q = re.search(r"QUOTE:\s*(.+)", raw)
    a = re.search(r"ANSWER:\s*(.+)", raw)
    if not q or not a:
        return {"answer": SENTINEL}
    nq, nd = norm(q.group(1)), norm(doc)
    if len(nq) < 12:
        return {"answer": SENTINEL}
    if nq not in nd and fuzz.partial_ratio(nq, nd) < 90:
        return {"answer": SENTINEL}
    return {"answer": a.group(1).strip(), "quote": q.group(1).strip()}
```

`partial_ratio` over a whole long document is slow; for documents over about
20k characters run it per chunk.

## B. Code generation and execution

### B1. Does Qwen2.5-Coder-7B-Instruct NF4 fit next to Cosmos? No.

- Config (`Qwen/Qwen2.5-Coder-7B-Instruct/config.json`, checked): 28 layers,
  hidden 3584, 4 KV heads, vocab 152064, `tie_word_embeddings: false`.
- bitsandbytes leaves `embed_tokens` and `lm_head` in bf16: 2 x 152064 x 3584 x
  2 bytes = 2.03 GiB before any transformer layer.
- The prequantized NF4 checkpoint `unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit`
  is 5.55 GB (5.17 GiB) of weights (checked, HF file listing).
- Budget: about 5.2 GB free on the dGPU (D1); Cosmos resident takes 2.4 GiB,
  leaving about 2.8 GiB. 5.2 GiB of weights plus KV and activations does not fit
  next to Cosmos, and does not fit alone either. Ruled out.

### B2. Candidate models

| Model ID | License | HumanEval | HumanEval+ | MBPP | MBPP+ | Other | NF4 VRAM (weights) |
|---|---|---|---|---|---|---|---|
| `Qwen/Qwen2.5-Coder-0.5B-Instruct` | Apache-2.0 (UNVERIFIED) | 61.6 | 57.3 | 52.4 | 43.7 | | about 0.5 GiB (est.) |
| `Qwen/Qwen2.5-Coder-1.5B-Instruct` | Apache-2.0 (checked) | 70.7 | 66.5 | 69.2 | 59.4 | | about 1.2 GiB (est.) |
| `Qwen/Qwen2.5-Coder-3B-Instruct` | **Qwen Research License** (`qwen-research`, checked): research / non-commercial terms | 84.1 | 80.5 | 73.6 | 62.4 | | about 2.0 GiB (est.) |
| `Qwen/Qwen2.5-Coder-7B-Instruct` | Apache-2.0 (checked) | 88.4 | 84.1 | 83.5 | 71.7 | | 5.17 GiB (checked) |
| `Qwen/Qwen3-4B` (non-thinking) | Apache-2.0 | n/r | | | | LiveCodeBench v6 26.4, MultiPL-E 66.6 | about 2.6 GiB (est.) |
| `Qwen/Qwen3-4B-Instruct-2507` | Apache-2.0 (checked) | n/r | | | | LiveCodeBench v6 35.1, MultiPL-E 76.8 | about 2.6 GiB (est.) |
| `Qwen/Qwen3-VL-4B-Instruct` | Apache-2.0 (checked) | n/r | | | | LiveCodeBench v6 37.9 | 3.6 GiB peak (measured, D5) |

Sources: Qwen2.5-Coder Technical Report (Hui et al., arXiv 2409.12186, instruct
table); Qwen3-4B-Instruct-2507 model card; Qwen3-VL Technical Report (arXiv
2511.21631, pure-text instruct table). n/r = not reported in those sources. For
the base models, the Qwen3 report gives EvalPlus 63.53 for Qwen3-4B-Base vs
62.18 for Qwen2.5-7B-Base and 46.28 for Qwen2.5-3B-Base. NF4 sizes marked
"est." are parameter-count arithmetic with bf16 embeddings, not measured.

Qwen3-Coder: the open releases I know of start at `Qwen3-Coder-30B-A3B-Instruct`
(about 17 GB even at 4 bit). No small Qwen3-Coder (UNVERIFIED that none was
released by Nov 2026). Not an option on 8 GB.

Qwen2.5-Coder-3B is the best score per GiB, but its license is not Apache. Avoid
it unless the hackathon rules accept research-only licenses for a public repo.

### B3. Is Qwen3-VL-4B good enough at code? Yes, for this task.

- On LiveCodeBench v6 (harder than HumanEval, contamination-controlled) it
  scores 37.9, above Qwen3-4B-Instruct-2507 (35.1) and well above Qwen3-4B
  non-thinking (26.4). Qwen3-4B-Base already matches Qwen2.5-7B-Base on EvalPlus.
- No published HumanEval/MBPP for Qwen3-VL-4B. Inference from the above:
  HumanEval-level pass@1 in the low to mid 80s (UNVERIFIED), between
  Qwen2.5-Coder-3B and 7B. The practice items look HumanEval/MBPP-sized
  (single function plus unit tests), where 2 retries with the error message
  typically add 3 to 8 points (UNVERIFIED for this model).
- It is already loaded on demand for D5 and for doc QA, so code needs no extra
  VRAM and no model swap. One model also means one prompt format and one NF4
  path to debug.
- NF4 costs some accuracy vs bf16 (often 1 to 3 points on code, UNVERIFIED for
  this model). The D5 Conv3d fix does not matter for text-only calls.

**Expected on the 20 practice items:** 15 to 18 pass first try, 17 to 19
after 2 retries (UNVERIFIED). If below 15, A/B test
`Qwen/Qwen2.5-Coder-1.5B-Instruct` (fits next to Cosmos at about 1.2 GiB,
UNVERIFIED) before anything bigger.

Prompt notes: ask for a single fenced ```python block, a top-level function
with the exact name the test expects, standard library only unless told
otherwise, and `print` of the final result for free-form requests. Greedy
decoding. On retry send the code, the last 30 lines of stderr, and the failing
test name.

### B4. Sandboxing in Docker on WSL2

Threat model: the model writes buggy or odd code (infinite loops, huge
allocations, `rm -rf`, network calls), not an expert attacker. The container is
the boundary; in-process checks are speed bumps.

**Network.** `unshare -n` needs CAP_SYS_ADMIN or unprivileged user namespaces;
Docker's default seccomp profile blocks `unshare` without CAP_SYS_ADMIN, so it
will fail inside the normal app container (UNVERIFIED on this exact Docker
Desktop/WSL2 build). Do not grant CAP_SYS_ADMIN to the app container to make it
work. Use a separate runner container instead:

```
docker run -d --name maya-runner --network none --read-only \
  --tmpfs /work:rw,size=64m,mode=1777 --tmpfs /tmp:rw,size=16m \
  --cap-drop ALL --security-opt no-new-privileges --pids-limit 64 \
  --memory 512m --cpus 1 --user 65534:65534 \
  -v maya-jobs:/jobs maya-runner:latest
```

The app and the runner share only the `maya-jobs` volume: the app writes
`job_<id>.py` plus tests, the runner executes and writes `job_<id>.json`. No
docker socket in the app container, no network on the runner, no shared network
needed at all. (Compose: `network_mode: none` on the runner service.)

**Inside the runner, per job:** fresh temp dir under `/work`, `python -I -S`
(isolated mode, no user site, no cwd on path), empty env except `PATH`, rlimits:

- `RLIMIT_CPU` 10 s (CPU time), plus a 10 s wall clock via `timeout=` for
  `sleep`-style hangs
- `RLIMIT_AS` 1 GiB (numpy/OpenBLAS reserve large virtual ranges; set
  `OPENBLAS_NUM_THREADS=1` or raise to 2 GiB if numpy is allowed)
- `RLIMIT_NPROC` 32, `RLIMIT_FSIZE` 16 MiB, `RLIMIT_NOFILE` 64, `RLIMIT_CORE` 0
- `start_new_session=True` and kill the process group on timeout, so forked
  children die too

**Dangerous imports, reasonably.** Python has no safe in-process sandbox; these
only reject obvious mistakes before they cost a 10 s timeout and give a clear
message for the retry:

- AST pass before running: reject imports of `socket`, `subprocess`, `ctypes`,
  `multiprocessing`, `shutil`, `urllib`, `http`, `requests`, `ftplib`,
  `telnetlib`, `pty`, `signal`, and calls to `os.system`, `os.popen`,
  `os.exec*`, `os.fork`, `os.kill`, `os.remove`, `os.rmdir`, `__import__`,
  `eval`, `exec`, `compile`. Reply "Blocked: uses subprocess" so the retry
  rewrites it.
- Audit hook preamble (PEP 578, `sys.addaudithook`) that raises on
  `subprocess.Popen`, `os.system`, `os.exec`, `os.fork`, `socket.connect`,
  `ctypes.dlopen`, and `open` for write outside the job dir. PEP 578 says
  audit hooks are not a sandbox; they are a second speed bump.
- Real protection is the container flags above plus the non-root user and
  read-only root filesystem.

### B5. Reference runner (about 35 lines)

```python
import ast, json, os, resource, subprocess, sys, tempfile

BLOCKED_MODULES = {"socket", "subprocess", "ctypes", "multiprocessing", "shutil",
                   "urllib", "http", "requests", "ftplib", "pty", "signal"}
BLOCKED_CALLS = {"system", "popen", "fork", "kill", "remove", "rmdir", "execv",
                 "execvp", "__import__", "eval", "exec", "compile"}

def lint(code):
    for n in ast.walk(ast.parse(code)):
        mods = [a.name for a in n.names] if isinstance(n, ast.Import) else \
               [n.module or ""] if isinstance(n, ast.ImportFrom) else []
        bad = [m for m in mods if m.split(".")[0] in BLOCKED_MODULES]
        if bad: return f"Blocked: imports {bad[0]}"
        if isinstance(n, ast.Call):
            name = getattr(n.func, "attr", getattr(n.func, "id", ""))
            if name in BLOCKED_CALLS: return f"Blocked: calls {name}"

def limits():
    for r, v in [(resource.RLIMIT_CPU, 10), (resource.RLIMIT_AS, 1 << 30),
                 (resource.RLIMIT_NPROC, 32), (resource.RLIMIT_FSIZE, 16 << 20),
                 (resource.RLIMIT_NOFILE, 64), (resource.RLIMIT_CORE, 0)]:
        resource.setrlimit(r, (v, v))

def run(code, tests="", timeout=10):
    if (msg := lint(code)): return {"ok": False, "stderr": msg}
    with tempfile.TemporaryDirectory(dir="/work") as d:
        open(os.path.join(d, "main.py"), "w").write(code + "\n\n" + tests)
        try:
            p = subprocess.run([sys.executable, "-I", "-S", "main.py"], cwd=d,
                capture_output=True, text=True, timeout=timeout, preexec_fn=limits,
                start_new_session=True, env={"PATH": "/usr/bin:/bin"})
        except subprocess.TimeoutExpired:
            return {"ok": False, "stderr": f"Timed out after {timeout} s"}
        return {"ok": p.returncode == 0, "stdout": p.stdout[-4000:],
                "stderr": p.stderr[-4000:]}
```

Notes on it:
- `subprocess.run` with `timeout` kills only the direct child. With
  `start_new_session=True`, add `os.killpg(p.pid, 9)` via `Popen` plus
  `communicate(timeout=)` if the code is allowed to fork at all; with
  `RLIMIT_NPROC` and `fork` blocked this is a minor gap.
- `RLIMIT_NPROC` counts all processes of the UID, so run the runner as a
  dedicated UID (65534 above) that owns nothing else.
- `preexec_fn` is not thread-safe; the runner should be a single-threaded loop
  over `/jobs`.
- Tests are appended as plain `assert` lines, so a failing assert gives a
  traceback with the line, which is what the retry prompt needs.
- `-S` removes `site-packages` too. If the pack needs numpy or similar, drop
  `-S` and keep `-I`.

### B6. Retry loop

Up to 2 retries (3 attempts total). Retry on: non-zero exit, timeout, lint
block, missing code block. Each retry prompt: original request, previous code,
last 30 lines of stderr. Stop early if the same error repeats twice. Report to
the user: what the code does in one sentence, pass/fail, and the printed result
or the last error line, read aloud short.

## Open items

- Measure A on the 20 practice text items: full-document vs BM25 (chunk 150 /
  250 / 400), with and without the quote check.
- Measure B on the 20 code items with Qwen3-VL-4B NF4: pass@1 and pass after
  retries, latency per item.
- Confirm `unshare` behavior in the app container only if the sidecar design
  runs into trouble; the sidecar does not need it.
- Confirm the hackathon allows Apache-2.0 models only, or also the Qwen Research
  License (affects Qwen2.5-Coder-3B).

## Sources

- Qwen2.5-Coder Technical Report, arXiv 2409.12186 (instruct HumanEval/MBPP table)
- Qwen3 Technical Report, arXiv 2505.09388 (base EvalPlus, Qwen3-4B code numbers)
- Qwen3-VL Technical Report, arXiv 2511.21631 (pure-text instruct table)
- https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct (license `qwen-research`)
- https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct (Apache-2.0)
- https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct/raw/main/config.json
- https://huggingface.co/unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit/tree/main (5.55 GB)
- https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507 (Apache-2.0, coding table)
- https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct (Apache-2.0)
- PyMuPDF licensing: https://pymupdf.readthedocs.io/en/latest/about.html (AGPL-3.0 or Artifex commercial)
- Rajpurkar et al., SQuAD 2.0, arXiv 1806.03822; Chen et al., RGB, arXiv 2309.01431;
  Ming et al., FaithEval, arXiv 2410.03727; Kirichenko et al., AbstentionBench,
  arXiv 2506.09038; Liu et al., Lost in the Middle, arXiv 2307.03172
- PEP 578 (Python runtime audit hooks)
