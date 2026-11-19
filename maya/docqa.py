"""Document question answering that refuses when the document does not say.

Default path (doc_mode=quote): the model copies the supporting sentence and a
short answer, or replies NONE. Code then checks that the quote is really in the
document, that the answer is in the quoted passage, that every number in the
question appears there too, and that capitalized names in the question appear
somewhere in the document. Any failed check gives the refusal. Optional second
model call (doc_verify=1) asks whether the passage answers the exact question.
A PDF page with no text layer is transcribed by the VLM (about 27 s per page).

Options (eng.opts, strings):
  doc_mode    quote | plain      plain is the single-call baseline
  doc_rules   1 | 0              number and name checks
  doc_verify  0 | 1              second yes/no model call; off because on the practice pack
                                 it refused one answerable item and caught nothing the rules missed
  doc_style   short | sentence   sentence: speak a one-sentence answer when it adds no new facts
  doc_ext     ''  | pdf | txt    swap the file extension (eval of the PDF copies)
"""
import re
import unicodedata
import zipfile
from pathlib import Path

REFUSAL = "The document does not say."

PLAIN_SYSTEM = ("You answer questions using only the given document. If the document does not "
                f"contain the answer, reply exactly: {REFUSAL}")

QUOTE_SYSTEM = """You answer questions about a document using only that document.

Reply in exactly this format:
QUOTE: <the sentence from the document that states the answer, copied word for word>
ANSWER: <a short answer>{format_sentence}

If the document does not state the answer to this exact question, reply with the single word NONE.
Many questions reuse the document's words but change one detail: a different year, number, name, place, group, or a different relation (opened instead of closed, won instead of lost). If any detail of the question does not match what the document says, reply NONE. Do not use outside knowledge. A guess is wrong; NONE is not.

Example document: "The Harbor Bridge opened in 1932 after eight years of work. Its chief engineer was Ada Lin, who later designed the North Tunnel."
Question: Who was the chief engineer of the Harbor Bridge?
QUOTE: Its chief engineer was Ada Lin, who later designed the North Tunnel.
ANSWER: Ada Lin{example_sentence}
Question: When did the North Tunnel open?
NONE
Question: What year did the Harbor Bridge close?
NONE
Question: How many years of work did the Harbor Bridge take before it opened in 1936?
NONE"""
QUOTE_SYSTEM_SHORT = QUOTE_SYSTEM.format(format_sentence="", example_sentence="")
QUOTE_SYSTEM_SENTENCE = QUOTE_SYSTEM.format(
    format_sentence="\nSENTENCE: <the answer as one short complete sentence>",
    example_sentence="\nSENTENCE: Ada Lin was the chief engineer of the Harbor Bridge.")

VERIFY_SYSTEM = ("You check answers. Reply YES or NO only.")

VERIFY_PROMPT = """Passage: {passage}

Question: {question}
Proposed answer: {answer}

Does the passage state this answer to this exact question? Every detail in the question (dates, numbers, names, places, groups, and what happened) must match the passage. If the question asks about something the passage does not state, or one of its details differs from the passage, reply NO. Reply YES or NO."""

STOP = set("""a an the of in on at to for from by with and or as is are was were be been being
that this these those which who whom whose what when where why how it its their his her
they them he she we you i not no do does did has have had about into than then there
""".split())
NUM_WORDS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
    "fifteen sixteen seventeen eighteen nineteen twenty".split())}
NUM_WORDS.update({w: 10 * i for i, w in enumerate("thirty forty fifty sixty seventy eighty ninety".split(), 3)})
MONTHS = {m[:3]: m for m in "january february march april may june july august september "
          "october november december".split()}


def read_doc(path, eng=None):
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".pdf":
        return _read_pdf(p, eng)
    if ext == ".docx":
        with zipfile.ZipFile(p) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
        xml = re.sub(r"</w:p>", "\n", xml)
        return unicodedata.normalize("NFKC", re.sub(r"<[^>]+>", "", xml))
    text = p.read_text(encoding="utf-8", errors="replace")
    if ext in (".html", ".htm"):
        text = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)
        text = re.sub(r"<[^>]+>", " ", text)
    return text


def _read_pdf(p, eng):
    from pypdf import PdfReader
    reader = PdfReader(str(p))
    pages = []
    for page in reader.pages:
        t = page.extract_text() or ""
        # pypdf keeps justified spacing and hard line breaks; rejoin words split at a line end.
        t = re.sub(r"(\w)-\n(\w)", r"\1\2", t)
        t = re.sub(r"[ \t]+", " ", t)
        if len(t.strip()) < 20 and eng is not None:
            t = _ocr_page(page, eng)
        pages.append(t.strip())
    return "\n\n".join(pages)


def _ocr_page(page, eng):
    """Scanned page: transcribe its embedded images with the VLM."""
    out = []
    for im in page.images:
        content = [{"type": "image", "image": im.image.convert("RGB")},
                   {"type": "text", "text": "Transcribe all text in this image exactly. Output only the text."}]
        text, _ = eng.vlm.chat(content, None, max_new_tokens=1500)
        out.append(text)
    return "\n".join(out)


def norm(s):
    s = unicodedata.normalize("NFKC", s or "").lower()
    s = re.sub(r"[‘’`´]", "'", s)
    s = re.sub(r"(\d),(\d)", r"\1\2", s)
    s = re.sub(r"[^\w\s']|_", " ", s)
    s = s.replace("'", "")
    return re.sub(r"\s+", " ", s).strip()


def stem(w):
    return w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w


def numbers(s, words=False):
    """Digits in s; with words=True also spelled-out numbers ("two-volume" gives 2).

    Questions use words=False: "which one of" must not demand a 1 in the passage.
    """
    out = set(re.findall(r"\d+(?:\.\d+)?", re.sub(r"(\d),(\d)", r"\1\2", s or "")))
    if words:
        out |= {str(NUM_WORDS[w]) for w in re.findall(r"[a-z]+", (s or "").lower()) if w in NUM_WORDS}
    return out


def near(t, vocab):
    """t matches a document word up to inflection or one typo (Setanta vs Sentanta)."""
    if t in vocab or (len(t) >= 5 and any(w.startswith(t[:5]) and t.startswith(w[:5]) for w in vocab)):
        return True
    if len(t) < 5:
        return False
    for w in vocab:
        if abs(len(w) - len(t)) <= 1 and w[0] == t[0]:
            i = next((k for k in range(min(len(w), len(t))) if w[k] != t[k]), min(len(w), len(t)))
            if w[i + 1:] == t[i + 1:] or w[i:] == t[i + 1:] or w[i + 1:] == t[i:]:
                return True
    return False


def sentences(doc):
    parts = re.split(r"(?<=[.!?])[\"')\]]?\s+(?=[\"'(\[]?[A-Z0-9])|\n\s*\n", doc)
    return [re.sub(r"\s+", " ", p).strip() for p in parts if p and p.strip()]


def trigrams(toks):
    return {tuple(toks[i:i + 3]) for i in range(len(toks) - 2)}


def locate(quote, doc_sents):
    """Return (coverage, passage) for a model quote against the document sentences.

    coverage is the share of the quote's word trigrams found in the document.
    passage is the sentence before the first matching sentence plus every
    matching sentence, so a quote that starts with "His role ..." keeps its subject.
    """
    pieces = [norm(x).split() for x in re.split(r"\.\.\.|…", quote)]
    if sum(len(x) for x in pieces) < 3:
        return 0.0, ""
    qg = set().union(*(trigrams(x) for x in pieces)) or {tuple(max(pieces, key=len))}
    sent_g = [trigrams(norm(s).split()) for s in doc_sents]
    hits = [i for i, g in enumerate(sent_g) if len(g & qg) >= min(2, len(qg))]
    if not hits:
        return 0.0, ""
    all_g = set().union(*sent_g)
    # Trigrams across a sentence boundary are missing from all_g; check them on the joined text.
    joined = " " + " ".join(norm(s) for s in doc_sents) + " "
    cov = sum(1 for g in qg if g in all_g or f" {' '.join(g)} " in joined) / len(qg)
    lo = max(0, hits[0] - 1)
    return cov, " ".join(doc_sents[lo:hits[-1] + 1])


def parse(raw):
    if re.match(r"\W*none\b", raw.strip(), re.I) or re.search(r"(?im)^\W*none\W*$", raw):
        if not re.search(r"(?im)^\s*answer\s*:", raw):
            return None, None, None
    q = re.search(r"(?is)quote\s*:\s*(.+?)(?=\n\s*answer\s*:|$)", raw)
    a = re.search(r"(?is)answer\s*:\s*(.+)", raw)
    if not q or not a:
        return None, None, None
    quote = q.group(1).strip().strip('"“”')
    ans = a.group(1).strip().splitlines()[0].strip()
    if re.fullmatch(r"\W*none\W*", ans, re.I) or re.search(r"does not say|not stated|not mentioned", ans, re.I):
        return None, None, None
    m = re.search(r"(?im)^\s*sentence\s*:\s*(.+)$", raw)
    return quote, ans, (m.group(1).strip() if m else "")


def grounded(answer, passage):
    """Every number in the answer and at least half of its content words are in the passage."""
    pt = {stem(w) for w in norm(passage).split()}
    if not numbers(answer) <= numbers(passage, words=True):
        return False
    words = [stem(w) for w in norm(answer).split() if w not in STOP]
    if not words:
        return True
    return sum(w in pt for w in words) * 2 >= len(words)


def sentence_ok(sentence, ans, question, passage, doc):
    """A spoken sentence may replace the short answer only if it adds no new facts:
    its numbers and capitalized words come from the passage, document or question."""
    if not sentence or re.search(r"does not|not stated|not mentioned", sentence, re.I):
        return False
    st = set(norm(sentence).split())
    if any(w not in st for w in norm(ans).split() if w not in STOP):
        return False
    if not numbers(sentence) <= numbers(passage, words=True) | numbers(question):
        return False
    known = {stem(w) for w in norm(doc + " " + question).split()}
    caps = re.findall(r"(?<=\s)[A-Z][\w'’-]*", " " + sentence.split(" ", 1)[-1])
    return all(stem(t) in known for w in caps for t in norm(w).split())


def question_conflict(question, passage, doc):
    """Reason string when a question detail is missing, else ''.

    Numbers in the question must appear in the supporting passage (a changed
    year or count is the usual SQuAD 2.0 trap). Capitalized words after the
    first word must appear somewhere in the document; months may be abbreviated.
    """
    missing = numbers(question) - numbers(passage, words=True)
    if missing:
        return f"number {sorted(missing)} not in passage"
    dt = {stem(w) for w in norm(doc).split()}
    dprefix = {w[:3] for w in dt}
    for w in re.findall(r"(?<=\s)[A-Z][\w'’-]*", " " + question.split(" ", 1)[-1]):
        for t in norm(w).split():
            if t in STOP or near(stem(t), dt):
                continue
            if t[:3] in MONTHS and t[:3] in dprefix:
                continue
            return f"name {w!r} not in document"
    return ""


def opt(eng, key, default):
    return str(getattr(eng, "opts", {}).get(key, default))


def doc_path(eng, path):
    ext = opt(eng, "doc_ext", "")
    return str(Path(path).with_suffix("." + ext)) if ext else path


def load_doc(eng, path):
    """read_doc with a per-file cache, since a scanned PDF costs one VLM call per page."""
    p = Path(doc_path(eng, path))
    key = ("doc", str(p), p.stat().st_mtime)
    cache = getattr(eng, "cache", {})
    if key not in cache:
        cache[key] = read_doc(p, eng)
    return cache[key]


def answer(eng, path, question):
    doc = load_doc(eng, path)
    if opt(eng, "doc_mode", "quote") == "plain":
        prompt = f"Document:\n{doc}\n\nQuestion: {question}\nAnswer in a few words."
        text, info = eng.vlm.text(prompt, PLAIN_SYSTEM, max_new_tokens=64)
        return text, {**info, "route": "document"}

    prompt = (f"Question: {question}\n\nDocument:\n{doc}\n\nQuestion: {question}\n"
              "Reply with QUOTE and ANSWER, or NONE.")
    style = opt(eng, "doc_style", "short")
    system = QUOTE_SYSTEM_SENTENCE if style == "sentence" else QUOTE_SYSTEM_SHORT
    raw, info = eng.vlm.text(prompt, system, max_new_tokens=200)
    info = {**info, "route": "document", "raw": raw}
    quote, ans, sentence = parse(raw)
    if quote is None:
        return REFUSAL, {**info, "why": "model said none"}
    cov, passage = locate(quote, sentences(doc))
    if cov < 0.85:
        return REFUSAL, {**info, "why": f"quote not in document ({cov:.2f})"}
    if not grounded(ans, passage):
        return REFUSAL, {**info, "why": "answer not in quoted passage"}
    if opt(eng, "doc_rules", "1") == "1":
        why = question_conflict(question, passage, doc)
        if why:
            return REFUSAL, {**info, "why": why}
    if opt(eng, "doc_verify", "0") == "1":
        verdict, vinfo = eng.vlm.text(
            VERIFY_PROMPT.format(passage=passage, question=question, answer=ans),
            VERIFY_SYSTEM, max_new_tokens=3)
        info["verify"] = verdict
        info["model_s"] = round(info.get("model_s", 0) + vinfo.get("model_s", 0), 3)
        if not verdict.strip().upper().startswith("YES"):
            return REFUSAL, {**info, "why": "verifier said no"}
    if style == "sentence" and sentence_ok(sentence, ans, question, passage, doc):
        ans = sentence
    ans = ans.rstrip()
    return (ans if ans.endswith((".", "!", "?")) else ans + "."), info
