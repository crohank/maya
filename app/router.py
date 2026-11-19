"""Rule-based router. No model call; every decision is one JSON line in the routing log.

File type decides first; the question only splits video (read vs scene) and,
with no file, decides whether the request is a coding prompt.
"""
import json
import re
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path

READ_WORDS = re.compile(
    r"\b(read|reading|sign|signs|text|label|labels|bus number|written|writing|"
    r"what does it say|menu|price)\b",
    re.I,
)
CODE_Q = re.compile(
    r"^\s*(def|class)\s+\w+\s*[(:]|```|\bpython\b|"
    r"\b(write|implement|complete|create|code|fix)\b[^.?!\n]{0,60}\b(function|program|script|method)\b",
    re.I | re.M,
)
DOC_EXT = {".pdf", ".txt", ".md", ".docx", ".html", ".htm"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".bmp", ".gif"}
VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v"}
AUDIO_EXT = {".wav", ".mp3", ".m4a", ".ogg", ".opus", ".aac", ".flac", ".weba"}
CODE_EXT = {".py"}


@dataclass
class Route:
    name: str               # photo | video_read | video_scene | sound | document_qa | code | no_media | unsupported
    modality: str | None    # Engine.answer modality: image | video | audio | text | code; None = no engine call
    reason: str
    last_frame: bool = False


def media_kind(filename, content_type):
    """image | video | audio | document | code | None (unsupported)."""
    ct = (content_type or "").lower()
    ext = Path(filename or "").suffix.lower()
    if ext in CODE_EXT:
        return "code"
    # MediaRecorder on some browsers labels a clip application/octet-stream, so the
    # extension is the fallback. A WebM labelled video/ may hold only audio; main.py
    # probes the streams and reroutes that case.
    for prefix in ("image", "video", "audio"):
        if ct.startswith(prefix + "/"):
            return prefix
    if ct in ("application/pdf", "text/plain") or ext in DOC_EXT:
        return "document"
    if ext in IMAGE_EXT:
        return "image"
    if ext in VIDEO_EXT:
        return "video"
    if ext in AUDIO_EXT:
        return "audio"
    return None


def is_code_prompt(question):
    return bool(CODE_Q.search(question or ""))


def route(kind, question, has_file=None, force=None):
    q = question or ""
    if has_file is None:
        has_file = kind is not None
    if kind == "video":
        m = READ_WORDS.search(q)
        if m:
            return Route("video_read", "image", f"video + reading word '{m.group(0)}': last frame as a photo", True)
        return Route("video_scene", "video", "video + question")
    if kind == "image":
        return Route("photo", "image", "photo + question")
    if kind == "audio":
        return Route("sound", "audio", "audio file, converted to 16 kHz mono WAV")
    if kind == "document":
        return Route("document_qa", "text", "document file + question")
    if kind == "code":
        return Route("code", "code", "Python file: its text is the prompt")
    if has_file:
        return Route("unsupported", None, "file type not recognised")
    if force == "code" and q:
        return Route("code", "code", "POST /code/run")
    if is_code_prompt(q):
        return Route("code", "code", "no file + question looks like a coding prompt")
    return Route("no_media", None, "no file attached and the question is not a coding prompt")


class RoutingLog:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()

    def write(self, r: Route, **extra):
        row = {"ts": round(time.time(), 3), **asdict(r), **extra}
        with self.lock, open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, default=str) + "\n")
