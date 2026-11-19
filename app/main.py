"""Maya web app: one page, POST /ask (plus /document/ask, /code/run), GET /health.

Every answer comes from one maya.engine.Engine, which keeps at most one model on
the GPU. Run inside the maya-engine container (see docs/app.md):
  uvicorn app.main:app --host 0.0.0.0 --port 8443 --ssl-keyfile certs/key.pem --ssl-certfile certs/cert.pem
"""
import asyncio
import base64
import contextlib
import json
import logging
import re
import subprocess
import tempfile
import threading
import time
from pathlib import Path

import yaml
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps

from . import media
from .router import RoutingLog, media_kind, route
from .safety import safety_filter

ROOT = Path(__file__).resolve().parent
CFG = yaml.safe_load((ROOT / "config.yaml").read_text())
STATIC = ROOT / "static"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
log = logging.getLogger("maya")

DEFAULT_Q = {
    "image": "Describe what is in this photo and read any text.",
    "video": "What is happening in this video?",
    "text": "What is this document about?",
    "audio": "",   # maya/audio.py picks transcribe or describe from the audio itself
}
LIVE_Q = "What is in front of me?"
MSG = {
    "no_media": ("I need something to look at or listen to. Send a photo, a recording, a document "
                 "or a video, or type a coding question."),
    "unsupported": "I can't open that kind of file. Send a photo, a recording, a document or a video.",
    "too_short": "The recording had only just started. Hold the phone steady for two seconds, then ask again.",
    "unreadable": "I couldn't open that file. Please try sending it again.",
    "no_doc": "Attach a text or PDF document, then ask your question.",
    "error": "Sorry, something went wrong. Please try again.",
    "timeout": "Sorry, that took too long. Please try again.",
}


class BadMedia(Exception):
    def __init__(self, key, detail=""):
        super().__init__(detail or key)
        self.key = key


class State:
    engine = None
    engine_lock = threading.Lock()
    stt = None
    tts = None
    routing: RoutingLog = None
    startup_s: dict = {}


S = State()


@contextlib.asynccontextmanager
async def lifespan(_app):
    # Anything already set (tests put fakes here) is kept.
    if S.routing is None:
        S.routing = RoutingLog(CFG["logs"]["routing"])
    if S.tts is None:
        from .tts import Tts
        t = time.perf_counter()
        S.tts = await asyncio.to_thread(Tts, CFG["tts"]["repo"], CFG["tts"]["voice"])
        S.startup_s["tts"] = round(time.perf_counter() - t, 2)
    if S.stt is None:
        from .stt import Stt
        t = time.perf_counter()
        w = CFG["whisper"]
        S.stt = await asyncio.to_thread(Stt, w["size"], w["device"], w["compute_type"],
                                        w["cpu_threads"], w["language"])
        S.startup_s["whisper"] = round(time.perf_counter() - t, 2)
    if S.engine is None:
        from maya.engine import Engine
        S.engine = Engine(**{k: str(v) for k, v in (CFG["engine"].get("opts") or {}).items()})
        if CFG["engine"].get("preload"):
            t = time.perf_counter()
            parts = await asyncio.to_thread(S.engine.warm)
            S.startup_s["engine_warm"] = round(time.perf_counter() - t, 2)
            S.startup_s.update({f"warm_{k}": v for k, v in parts.items()})
    log.info("startup seconds %s", S.startup_s)
    yield


app = FastAPI(title="Maya", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


def _ffmpeg(args, timeout):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True,
                   capture_output=True, timeout=timeout)


def _probe(path, timeout):
    """(stream codec types, video codec name, container format names)."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
        capture_output=True, text=True, timeout=timeout)
    if out.returncode != 0:
        return set(), None, ""
    d = json.loads(out.stdout or "{}")
    streams = d.get("streams", [])
    video = [s for s in streams if s.get("codec_type") == "video"]
    vcodec = video[0].get("codec_name") if video else None
    # Phone MP4s store portrait as a rotation tag; PyAV in maya/video.py ignores it,
    # so a rotated clip is re-encoded (ffmpeg applies the rotation).
    rotated = any(str(s.get("tags", {}).get("rotate", "0")) not in ("0", "")
                  or any(sd.get("rotation") for sd in s.get("side_data_list", []))
                  for s in video)
    if rotated:
        vcodec = f"{vcodec}+rotated"
    return {s.get("codec_type") for s in streams}, vcodec, d.get("format", {}).get("format_name", "")


def to_wav16k(src, dst, timeout):
    _ffmpeg(["-i", src, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", dst], timeout)


def to_mp4(src, dst, long_side, timeout):
    vf = (f"scale={long_side}:{long_side}:force_original_aspect_ratio=decrease:"
          "force_divisible_by=2")
    _ffmpeg(["-i", src, "-an", "-vf", vf, "-c:v", "libx264", "-preset", "ultrafast",
             "-pix_fmt", "yuv420p", dst], timeout)


def normalize_image(src, dst, long_side):
    """EXIF-rotated RGB copy; maya/image.py opens the file without applying EXIF orientation."""
    try:
        im = Image.open(src)
        im.load()
    except Exception:
        # HEIC and other formats PIL cannot open here: let ffmpeg decode them.
        alt = f"{dst}.ffmpeg.png"
        _ffmpeg(["-i", src, "-frames:v", "1", alt], CFG["timeouts"]["ffmpeg_s"])
        im = Image.open(alt)
    with im:
        im = ImageOps.exif_transpose(im)
        if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
            # Transparent pixels are black once alpha is dropped, which hides dark text.
            rgba = im.convert("RGBA")
            bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
            out = Image.alpha_composite(bg, rgba).convert("RGB")
        else:
            out = im.convert("RGB")
    out.thumbnail((long_side, long_side))
    out.save(dst, quality=95)


def prepare(r, kind, src, work, live, lat):
    """Convert the upload to what Engine expects. Returns (route, path for Engine)."""
    to = CFG["timeouts"]["ffmpeg_s"]
    t = time.perf_counter()
    try:
        if kind == "video":
            types, vcodec, fmt = _probe(src, to)
            if "video" not in types and "audio" in types:
                # Audio-only WebM, often labelled video/webm by MediaRecorder.
                kind = "audio"
                r = route("audio", "")
                r.reason = "video container with only an audio stream"
            elif "video" not in types:
                raise BadMedia("unreadable", "no video or audio stream")
        if kind == "audio":
            path = f"{work}/audio.wav"
            to_wav16k(src, path, to)
        elif r.name == "video_read":
            path = f"{work}/last.ppm"
            media.last_frame(src, path, to)
        elif kind == "video" and live:
            v = CFG["video"]
            path = f"{work}/window.mp4"
            media.last_window(src, path, work, v["window_s"], v["fps"], v["long_side"], to)
        elif kind == "video":
            if vcodec == "h264" and "mp4" in fmt:
                path = src
            else:
                path = f"{work}/video.mp4"
                to_mp4(src, path, CFG["video"]["mp4_long_side"], to)
        elif kind == "image":
            path = f"{work}/image.jpg"
            normalize_image(src, path, CFG["image"]["long_side"])
        else:
            path = src
    except BadMedia:
        raise
    except Exception as e:
        # Includes PIL.Image.DecompressionBombError, which is not an OSError.
        raise BadMedia("unreadable", repr(e)) from e
    lat["preprocess"] = round((time.perf_counter() - t) * 1000)
    return r, path


def _display(text):
    # The app font has no em or en dash glyph; model output can contain both.
    text = text.replace(" — ", ", ").replace("—", ", ").replace("―", ", ")
    return re.sub("[‒–−]", "-", text)


def code_summary(info):
    n, p = info.get("self_checks"), info.get("self_checks_passed")
    if not isinstance(n, int) or not isinstance(p, int):
        return "Here is the function."
    if n == 0:
        return "Here is the function. The prompt had no examples to check it against."
    if p == n:
        return ("Here is the function. It passed its own example." if n == 1 else
                f"Here is the function. It passed all {n} of its own examples.")
    return f"Here is the function. It passed {p} of its {n} own examples, so check it before use."


def run_engine(modality, path, question, lat):
    t = time.perf_counter()
    with S.engine_lock:
        lat["wait"] = round((time.perf_counter() - t) * 1000)
        t = time.perf_counter()
        text, info = S.engine.answer(modality, path, question)
    lat["engine"] = round((time.perf_counter() - t) * 1000)
    if isinstance(info, dict) and isinstance(info.get("model_s"), (int, float)):
        lat["model"] = round(info["model_s"] * 1000)
    return text or "", info if isinstance(info, dict) else {}


def _jsonable(info):
    return json.loads(json.dumps(info, default=str))


def _speak(text, lat):
    t = time.perf_counter()
    wav = S.tts.wav_bytes(text)
    lat["tts"] = round((time.perf_counter() - t) * 1000)
    return base64.b64encode(wav).decode()


async def _save(upload, path):
    data = await upload.read()
    Path(path).write_bytes(data)
    return len(data)


async def _reply(r, status, text, question, lat, t0, log_extra, spoken=None, **body):
    spoken = spoken or text
    audio = await asyncio.to_thread(_speak, spoken, lat)
    lat["total"] = round((time.perf_counter() - t0) * 1000)
    S.routing.write(r, status=status, text=text, spoken=spoken, latency_ms=lat, **log_extra,
                    **{k: v for k, v in body.items() if k != "code"})
    out = {"text": text, "spoken": spoken, "route": r.name, "modality": r.modality,
           "question": question, "latency_ms": lat, "audio_b64": audio, **body}
    return out if status == 200 else JSONResponse(out, status_code=status)


async def handle(file, question, question_audio, force=None):
    t0 = time.perf_counter()
    lat = {}
    question = (question or "").strip()
    with tempfile.TemporaryDirectory() as work:
        live = False
        if question_audio is not None and question_audio.filename:
            qa = f"{work}/question{Path(question_audio.filename).suffix or '.webm'}"
            qsize = await _save(question_audio, qa)
            live = True
            if qsize >= CFG["guards"]["min_media_bytes"]:
                t = time.perf_counter()
                try:
                    heard = await asyncio.to_thread(S.stt.transcribe, qa)
                except Exception:
                    log.exception("question transcription failed")
                    heard = ""
                lat["stt"] = round((time.perf_counter() - t) * 1000)
                question = heard or question

        kind, src, size = None, None, 0
        has_file = file is not None and bool(file.filename)
        if has_file:
            kind = media_kind(file.filename, file.content_type)
            src = f"{work}/upload{Path(file.filename).suffix.lower()}"
            size = await _save(file, src)
        log_extra = dict(kind=kind, file_bytes=size, question=question, endpoint=force or "ask",
                         content_type=getattr(file, "content_type", None) if has_file else None)

        # /document/ask with a photo or recording still answers it by its own type.
        if force == "document" and not has_file:
            return await _reply(route(None, "", False), 400, MSG["no_doc"], question, lat, t0, log_extra)
        if kind == "code":
            code_text = Path(src).read_text(encoding="utf-8", errors="replace")
            question = (question + "\n\n" if question else "Complete this Python function:\n\n") + code_text
        r = route(kind, question, has_file, force)

        if r.modality is None:
            status = 415 if r.name == "unsupported" else 400
            return await _reply(r, status, MSG[r.name], question, lat, t0, log_extra)
        if kind in ("video", "audio") and size < CFG["guards"]["min_media_bytes"]:
            return await _reply(r, 422, MSG["too_short"], question, lat, t0, log_extra,
                                error="recording too short")

        try:
            if src is not None and r.modality != "code":
                r, path = await asyncio.to_thread(prepare, r, kind, src, work, live, lat)
            else:
                path = None
        except BadMedia as e:
            log.warning("unreadable upload: %s", e)
            return await _reply(r, 422, MSG[e.key], question, lat, t0, log_extra, error=str(e))

        q = question or (LIVE_Q if live and r.modality == "video" else DEFAULT_Q.get(r.modality, ""))
        limit = CFG["timeouts"]["code_request_s" if r.modality == "code" else "request_s"]
        try:
            raw, info = await asyncio.wait_for(
                asyncio.to_thread(run_engine, r.modality, path, q, lat), limit)
        except asyncio.TimeoutError:
            log.error("engine timed out after %s s", limit)
            return await _reply(r, 504, MSG["timeout"], question, lat, t0, log_extra,
                                error=f"timeout after {limit} s")
        except Exception as e:
            log.exception("engine failed")
            return await _reply(r, 500, MSG["error"], question, lat, t0, log_extra, error=repr(e))

        info = _jsonable(info)
        if r.modality == "code":
            # Code is returned exactly as generated and never read aloud.
            return await _reply(r, 200, raw, question, lat, t0, log_extra,
                                spoken=code_summary(info), code=raw, flagged=False, info=info)
        t = time.perf_counter()
        text = _display(raw.strip()) or "I don't have an answer for that."
        flagged = False
        # A transcript repeats what the recording says ("go ahead" included); the
        # filter is for Maya's own advice, so verbatim transcripts skip it.
        if "transcri" not in str(info.get("route", "")):
            text, flagged = safety_filter(text)
        lat["safety"] = round((time.perf_counter() - t) * 1000)
        return await _reply(r, 200, text, question, lat, t0, log_extra, flagged=flagged,
                            raw=raw, info=info)


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/ca.crt")
def ca_cert():
    path = Path(CFG["server"]["ca_certfile"])
    if not path.exists():
        return JSONResponse({"error": "No local CA certificate on the server."}, status_code=404)
    return FileResponse(path, media_type="application/x-x509-ca-cert", filename="maya-local-ca.crt")


@app.get("/health")
def health():
    gpu = {"loaded": sorted(getattr(S.engine, "_gpu", {}) or {})}
    try:
        import torch
        if torch.cuda.is_available():
            free, _total = torch.cuda.mem_get_info()
            gpu.update(free_gib=round(free / 2**30, 2),
                       allocated_gib=round(torch.cuda.memory_allocated() / 2**30, 2))
    except Exception:
        pass
    return {"status": "ok", "engine": S.engine is not None, "gpu": gpu,
            "whisper": S.stt is not None, "tts": S.tts is not None, "startup_s": S.startup_s}


@app.post("/ask")
async def ask(file: UploadFile | None = File(None), question: str | None = Form(None),
              question_audio: UploadFile | None = File(None)):
    return await handle(file, question, question_audio)


@app.post("/document/ask")
async def document_ask(file: UploadFile | None = File(None), question: str | None = Form(None),
                       question_audio: UploadFile | None = File(None)):
    return await handle(file, question, question_audio, force="document")


@app.post("/code/run")
async def code_run(question: str | None = Form(None), file: UploadFile | None = File(None)):
    return await handle(file, question, None, force="code")
