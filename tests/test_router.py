import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.router import is_code_prompt, media_kind, route  # noqa: E402

PACK = Path(__file__).resolve().parents[1] / "Kaggle Data" / "items.json"


@pytest.mark.parametrize("name, ct, kind", [
    ("p.jpg", "image/jpeg", "image"),
    ("p.png", None, "image"),
    ("frame.jpg", "application/octet-stream", "image"),
    ("a.wav", "audio/wav", "audio"),
    ("a.wav", "audio/x-wav", "audio"),
    ("question.webm", "audio/webm", "audio"),
    ("a.m4a", None, "audio"),
    ("a.mp3", "audio/mpeg", "audio"),
    ("clip.webm", "video/webm", "video"),
    ("clip.webm", "application/octet-stream", "video"),
    ("v.mp4", "video/mp4", "video"),
    ("v.mov", "video/quicktime", "video"),
    ("d.txt", "text/plain", "document"),
    ("d.txt", None, "document"),
    ("d.pdf", "application/pdf", "document"),
    ("d.pdf", "application/octet-stream", "document"),
    ("f.py", "text/x-python", "code"),
    ("f.py", "text/plain", "code"),
    ("x.xyz", "application/octet-stream", None),
    ("noext", None, None),
])
def test_media_kind(name, ct, kind):
    assert media_kind(name, ct) == kind


@pytest.mark.parametrize("kind, q, name, modality", [
    ("image", "How many people?", "photo", "image"),
    ("video", "What happens in this video?", "video_scene", "video"),
    ("video", "What does the sign say?", "video_read", "image"),
    ("video", "", "video_scene", "video"),
    ("audio", "Transcribe this audio.", "sound", "audio"),
    ("document", "Who wrote it?", "document_qa", "text"),
    ("code", "", "code", "code"),
    (None, "Write a function that reverses a string.", "code", "code"),
    (None, "def add(a, b):\n    \"\"\"Add two numbers.\"\"\"\n", "code", "code"),
    (None, "What is the weather today?", "no_media", None),
    (None, "", "no_media", None),
])
def test_route(kind, q, name, modality):
    r = route(kind, q)
    assert (r.name, r.modality) == (name, modality)


def test_file_type_beats_question():
    # A photo with a coding-looking question is still a photo question.
    assert route("image", "Write a function for what is on this screen").name == "photo"
    assert route("document", "Complete this Python function").name == "document_qa"


def test_unknown_file_is_unsupported_even_with_code_question():
    assert route(None, "Write a function", has_file=True).name == "unsupported"


def test_force_code():
    assert route(None, "reverse a list in place", force="code").name == "code"
    assert route(None, "", force="code").name == "no_media"


@pytest.mark.parametrize("q", [
    "Write a Python function that returns the n-th Fibonacci number.",
    "Can you write a function to check if a word is a palindrome?",
    "Implement a function is_prime(n).",
    "def f(x):\n    pass",
    "```python\ndef f(): ...\n```",
])
def test_code_prompts(q):
    assert is_code_prompt(q)


@pytest.mark.parametrize("q", [
    "How many people are in this image?",
    "What is happening in this video?",
    "Who defeated Montcalm at Quebec?",
    "What kind of day was it, according to the recording?",
    "Transcribe this audio.",
    "Read the text",
])
def test_not_code_prompts(q):
    assert not is_code_prompt(q)


@pytest.mark.skipif(not PACK.exists(), reason="practice pack not present")
def test_practice_pack_code_detection():
    """Every pack code prompt reads as code; no other pack question does."""
    items = json.loads(PACK.read_text(encoding="utf-8"))
    code = [i for i in items if i["modality"] == "code"]
    other = [i for i in items if i["modality"] != "code"]
    assert code and all(is_code_prompt(i["question"]) for i in code)
    assert [i["id"] for i in other if is_code_prompt(i["question"])] == []
