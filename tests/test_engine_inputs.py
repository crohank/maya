"""Engine input edge cases, CPU only: the VLM is replaced by fakes that record calls.

Run in the engine image (Linux, PyAV, pypdf, ffmpeg):
  MSYS_NO_PATHCONV=1 docker run --rm --network none -v "$(pwd -W):/app" -w /app \
    -e PYTHONPATH=/app maya-engine python -m pytest tests -q
Mount hf-cache as well and the processor and AST checks run on the real models.
"""
import gc
import shutil
import subprocess
import sys
import weakref
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from maya import code, docqa, image, sandbox, sound, video  # noqa: E402

linux = pytest.mark.skipif(sandbox.resource is None, reason="sandbox limits need Linux")


class FakeVlm:
    """`reply` for every call; `ocr_reply`, when set, for calls that carry an image."""

    def __init__(self, reply="ok", ocr_reply=None):
        self.reply, self.ocr_reply = reply, ocr_reply
        self.calls = []

    def chat(self, content, system=None, max_new_tokens=128, **kw):
        self.calls.append({"content": content, "system": system, "max_new_tokens": max_new_tokens})
        has_image = any(c["type"] == "image" for c in content)
        return (self.ocr_reply if has_image and self.ocr_reply is not None else self.reply), {"model_s": 0.0}

    def text(self, prompt, system=None, max_new_tokens=256, history=None):
        return self.chat([{"type": "text", "text": prompt}], system, max_new_tokens)


class FakeEng:
    def __init__(self, vlm=None, **opts):
        self.opts, self.cache, self._vlm = opts, {}, vlm or FakeVlm()

    @property
    def vlm(self):
        return self._vlm


def ffmpeg(args, tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("no ffmpeg")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args], check=True, cwd=tmp_path)


# 1. one-frame video

def test_one_frame_video_sends_two_frames(tmp_path, monkeypatch):
    ffmpeg(["-f", "lavfi", "-i", "color=red:s=64x48:d=0.04", "-frames:v", "1",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "one.mp4"], tmp_path)
    seen = {}

    def fake_chat(vlm, content, system, max_new, pk):
        seen["content"], seen["pk"] = content, pk
        return "A red screen.", {}

    monkeypatch.setattr(video, "qwen_chat", fake_chat)
    text, info = video.answer(FakeEng(), str(tmp_path / "one.mp4"), "What color is it?")
    frames = seen["content"][0]["video"]
    assert len(frames) == 2 and len(seen["pk"]["video_metadata"][0]["frames_indices"]) == 2
    try:
        from transformers import AutoProcessor
        proc = AutoProcessor.from_pretrained("Qwen/Qwen3-VL-4B-Instruct", local_files_only=True)
    except Exception:
        return
    msgs = [{"role": "user", "content": seen["content"]}]
    out = proc.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True, return_dict=True,
                                   return_tensors="pt", processor_kwargs=seen["pk"])
    assert out["pixel_values_videos"].shape[0] > 0


# 2. rotated phone clip

def test_rotated_clip_decodes_upright(tmp_path):
    # Landscape source, red left half; ffmpeg's own autorotate puts the red half on top
    # for rotate=270 (checked against `ffmpeg -i r.mp4 out.ppm`).
    ffmpeg(["-f", "lavfi", "-i", "color=red:s=32x32:d=0.2", "-f", "lavfi", "-i", "color=blue:s=32x32:d=0.2",
            "-filter_complex", "hstack", "-c:v", "libx264", "-pix_fmt", "yuv420p", "src.mp4"], tmp_path)
    ffmpeg(["-i", "src.mp4", "-c", "copy", "-metadata:s:v:0", "rotate=270", "r.mp4"], tmp_path)
    frames, _ = video.decode(str(tmp_path / "r.mp4"))
    f = frames[0].astype(int)
    assert f.shape[:2] == (64, 32)
    red = f[..., 0] - f[..., 2]
    assert red[:16].mean() > 0 > red[-16:].mean()


# 3. transparent images and read-text token budget

def test_transparent_png_is_white(tmp_path):
    Image.new("RGBA", (40, 40), (0, 0, 0, 0)).save(tmp_path / "a.png")
    p = Image.new("P", (40, 40), 0)
    p.info["transparency"] = 0
    p.save(tmp_path / "p.png", transparency=0)
    for name in ("a.png", "p.png"):
        assert image.load(str(tmp_path / name)).getpixel((5, 5)) == (255, 255, 255), name


def test_read_questions_get_longer_answers(tmp_path):
    Image.new("RGB", (40, 40)).save(tmp_path / "x.jpg")
    vlm = FakeVlm("text")
    eng = FakeEng(vlm)
    image.answer(eng, str(tmp_path / "x.jpg"), "What does the sign say?")
    image.answer(eng, str(tmp_path / "x.jpg"), "What color is the car?")
    assert [c["max_new_tokens"] for c in vlm.calls] == [256, 64]


# 4. documents

def scanned_pdf(path, pages, size=(300, 400)):
    ims = [Image.new("RGB", size, (255, 255, 255)) for _ in range(pages)]
    ims[0].save(path, save_all=True, append_images=ims[1:])


def test_scanned_pdf_ocr_cap_and_note(tmp_path):
    scanned_pdf(tmp_path / "s.pdf", 6)
    vlm = FakeVlm("NONE", ocr_reply="The meeting is on Tuesday at noon in room four.")
    eng = FakeEng(vlm)
    text, info = docqa.answer(eng, str(tmp_path / "s.pdf"), "Where is the meeting?")
    ocr = [c for c in vlm.calls if c["content"][0]["type"] == "image"]
    assert len(ocr) == docqa.OCR_PAGES
    assert info["pages_skipped"] == 2 and "skipped 2" in text


def test_doc_cache_keyed_on_bytes_and_bounded(tmp_path):
    scanned_pdf(tmp_path / "a.pdf", 1)
    shutil.copy(tmp_path / "a.pdf", tmp_path / "b.pdf")
    vlm = FakeVlm("NONE", ocr_reply="Some scanned words on the page.")
    eng = FakeEng(vlm)
    docqa.answer(eng, str(tmp_path / "a.pdf"), "q?")
    docqa.answer(eng, str(tmp_path / "b.pdf"), "q?")
    assert sum(c["content"][0]["type"] == "image" for c in vlm.calls) == 1
    for i in range(docqa.CACHE_DOCS + 5):
        (tmp_path / f"{i}.txt").write_text(f"Document number {i}.")
        docqa.load_doc(eng, str(tmp_path / f"{i}.txt"))
    assert sum(1 for k in eng.cache if k[0] == "doc") == docqa.CACHE_DOCS


def test_empty_document_message(tmp_path):
    scanned_pdf(tmp_path / "blank.pdf", 1)
    eng = FakeEng(FakeVlm("NONE", ocr_reply=""))
    text, _ = docqa.answer(eng, str(tmp_path / "blank.pdf"), "What is the total?")
    assert text == docqa.EMPTY


def test_thin_images_skipped_in_ocr(tmp_path):
    scanned_pdf(tmp_path / "thin.pdf", 1, size=(3000, 10))
    vlm = FakeVlm("NONE", ocr_reply="x")
    docqa.answer(FakeEng(vlm), str(tmp_path / "thin.pdf"), "q?")
    assert not [c for c in vlm.calls if c["content"][0]["type"] == "image"]


def test_long_document_is_cut_to_relevant_passages(tmp_path):
    filler = " ".join(f"Paragraph {i} talks about weather patterns and rainfall in the valley." for i in range(1500))
    needle = "The lighthouse keeper was named Orla Brennan."
    (tmp_path / "long.txt").write_text(filler[:len(filler) // 2] + " " + needle + " " + filler[len(filler) // 2:])
    vlm = FakeVlm("NONE")
    docqa.answer(FakeEng(vlm), str(tmp_path / "long.txt"), "Who was the lighthouse keeper?")
    prompt = vlm.calls[0]["content"][0]["text"]
    assert needle in prompt
    assert len(prompt) < docqa.MAX_DOC_TOKENS * docqa.CHARS_PER_TOKEN + 1000


@pytest.mark.parametrize("q", ["What is this document about?", "Summarize this.", "", "What's the main point?"])
def test_summary_questions_use_plain_mode(tmp_path, q):
    (tmp_path / "d.txt").write_text("The council approved a new library. It opens in May.")
    vlm = FakeVlm("A new library was approved and opens in May.")
    text, info = docqa.answer(FakeEng(vlm), str(tmp_path / "d.txt"), q)
    assert info["summary"] and vlm.calls[0]["system"] == docqa.PLAIN_SYSTEM
    assert text.startswith("A new library")


def test_fact_question_still_uses_quote_mode(tmp_path):
    (tmp_path / "d.txt").write_text("The council approved a new library. It opens in May.")
    vlm = FakeVlm("NONE")
    text, _ = docqa.answer(FakeEng(vlm), str(tmp_path / "d.txt"), "What did the council approve?")
    assert vlm.calls[0]["system"] == docqa.QUOTE_SYSTEM_SHORT and text == docqa.REFUSAL


# 5. coding prompts

FENCED = '''Complete this function.

```python
def add(a, b):
    """Return a + b.

    >>> add(2, 3)
    5
    """
```
'''

PROSE_AFTER = '''def double(x):
    """Return twice x.

    >>> double(4)
    8
    """

Make sure it handles negative numbers too.'''

NO_DEF = """Write a function sum_digits(n) that returns the sum of the digits of n.
Examples:
sum_digits(123) -> 6
sum_digits(40) -> 4"""


def test_prompt_code_fenced_and_prose():
    for q, name, n in ((FENCED, "add", 1), (PROSE_AFTER, "double", 1), (NO_DEF, "sum_digits", 2)):
        got, checks, _, _ = code.checks_from(q)
        assert got == name and len(checks) == n, (q, got, checks)
    src, tree = code.prompt_code(FENCED)
    assert tree is not None and "```" not in src


@linux
def test_fallback_coder_frees_the_vlm(monkeypatch):
    class Model:
        def text(self, *a, **k):
            return "```python\ndef add(a, b):\n    return a - b\n```", {}

    alive = []

    class Eng(FakeEng):
        def __init__(self):
            super().__init__(fallback="qwen25-3b", retries="0")
            self._gpu = {}

        def gpu_model(self, name, loader):
            if name not in self._gpu:
                refs = [weakref.ref(v) for v in self._gpu.values()]
                self._gpu.clear()
                gc.collect()
                alive.append(any(r() is not None for r in refs))
                self._gpu[name] = loader()
            return self._gpu[name]

    class Coder:
        def __init__(self, vlm):
            self.v = vlm
            self.text = Model().text

    def fake_model(eng, name="vlm"):
        return Coder(eng.gpu_model(name, Model))

    monkeypatch.setattr(code, "model", fake_model)
    _, info = code.answer(Eng(), None, FENCED)
    assert info["attempts"] == 2 and alive == [False, False]


@linux
def test_program_waiting_for_input_is_not_a_failure(monkeypatch):
    prog = "name = input('Your name? ')\nprint('Hello', name)"
    r = code.self_check(prog, None, [])
    assert r["defined"] and r["needs_input"]

    class M:
        n = 0

        def text(self, *a, **k):
            M.n += 1
            return f"```python\n{prog}\n```", {}

    monkeypatch.setattr(code, "model", lambda eng, name="vlm": M())
    _, info = code.answer(FakeEng(), None, "Write a program that asks for my name and greets me.")
    assert M.n == 1 and info["needs_input"] and info["note"]


# 6. sandbox

ESCAPES = {
    "fork_exec": "import _posixsubprocess\n_posixsubprocess.fork_exec()",
    "subprocess alias": "import subprocess\nsubprocess._fork_exec()",
    "subprocess run": "import subprocess\nsubprocess.run(['true'])",
    "fresh _posixsubprocess": "import sys\ndel sys.modules['_posixsubprocess']\nimport _posixsubprocess",
    "sqlite3": "import sqlite3\nsqlite3.connect('/tmp/maya_sb_escape.db')",
    "_sqlite3 loader": ("import importlib.util\ns = importlib.util.find_spec('_sqlite3')\n"
                        "importlib.util.module_from_spec(s)"),
    "ctypes": "import ctypes",
    "dbm": "import dbm\ndbm.open('/tmp/maya_sb_escape_dbm', 'c')",
    "mkfifo": "import os\nos.mkfifo('/tmp/maya_sb_escape_fifo')",
    "mknod": "import posix, stat\nposix.mknod('/tmp/maya_sb_escape_node', stat.S_IFREG | 0o600)",
    "fresh posix": "import sys\ndel sys.modules['posix']\nimport posix\nposix.mkfifo('/tmp/maya_sb_escape_fifo')",
    "rebind root": ("import sys\nm = sys.modules['__main__']\nm._root = '/'\nm._inside = lambda p: True\n"
                    "open('/tmp/maya_sb_escape.txt', 'w').write('x')"),
    "write outside": "open('/tmp/maya_sb_escape.txt', 'w').write('x')",
    "gc": "import gc\ngc.get_objects()",
}


@linux
@pytest.mark.parametrize("name", sorted(ESCAPES))
def test_sandbox_refuses(name):
    ok, out, err = sandbox.run_python(ESCAPES[name], timeout_s=10)
    assert not ok and "sandbox:" in err, (name, out, err[-400:])
    for p in Path("/tmp").glob("maya_sb_escape*"):
        p.unlink()
        pytest.fail(f"{name} wrote {p}")


@linux
def test_sandbox_still_runs_ordinary_code():
    # asyncio imports subprocess at load time.
    src = ("import numpy as np, collections, json, re, heapq, fractions, decimal, datetime\n"
           "import asyncio\n"
           "open('scratch.txt', 'w').write('ok')\nprint(int(np.arange(4).sum()), open('scratch.txt').read())")
    ok, out, err = sandbox.run_python(src, timeout_s=20)
    assert ok and out.split() == ["6", "ok"], err[-400:]


# 7. very short audio

def test_ast_pads_short_audio():
    import torch
    lengths = []

    def fx(chunks, sampling_rate, return_tensors):
        lengths.extend(len(c) for c in chunks)
        return {"x": torch.zeros(len(chunks), 1)}

    class M:
        def __call__(self, x):
            return type("Out", (), {"logits": torch.zeros(x.shape[0], 527)})()

    eng = FakeEng()
    eng.cache["ast"] = (fx, M(), ["label"] * 527)
    for n in (0, 200):
        probs, starts = sound.ast_probs(eng, np.zeros(n, dtype=np.float32))
        assert probs.shape == (1, 527)
    assert lengths == [sound.SR, sound.SR]
