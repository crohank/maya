"""Rule-based router. No model call; every decision is one JSON line in the routing log."""
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
DOC_EXT = {".pdf", ".doc", ".docx", ".txt", ".ppt", ".pptx"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".bmp", ".gif"}
VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v"}
AUDIO_EXT = {".wav", ".mp3", ".m4a", ".ogg", ".opus", ".aac", ".flac", ".weba"}


@dataclass
class Route:
    name: str            # video_scene | video_read | photo | sound_id | document_qa | no_media
    model: str | None    # cosmos | qwen | None (stub or nothing to look at)
    reason: str
    last_frame: bool = False


def media_kind(filename, content_type):
    ct = (content_type or "").lower()
    ext = Path(filename or "").suffix.lower()
    # MediaRecorder on some browsers labels a video clip application/octet-stream.
    for prefix in ("image", "video", "audio"):
        if ct.startswith(prefix + "/"):
            return prefix
    if ct == "application/pdf" or ext in DOC_EXT:
        return "document"
    if ext in IMAGE_EXT:
        return "image"
    if ext in VIDEO_EXT:
        return "video"
    if ext in AUDIO_EXT:
        return "audio"
    return None


def route(kind, question):
    q = question or ""
    if kind == "video":
        m = READ_WORDS.search(q)
        if m:
            return Route("video_read", "qwen", f"video + reading word '{m.group(0)}': last frame to Qwen3-VL", True)
        return Route("video_scene", "cosmos", "video + question: Cosmos3-Edge")
    if kind == "image":
        return Route("photo", "qwen", "photo + question: Qwen3-VL")
    if kind == "audio":
        return Route("sound_id", None, "audio file: sound identification is not built")
    if kind == "document":
        return Route("document_qa", None, "document file: document Q&A is not built")
    return Route("no_media", None, "no photo or video attached")


class RoutingLog:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()

    def write(self, r: Route, **extra):
        row = {"ts": round(time.time(), 3), **asdict(r), **extra}
        with self.lock, open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
