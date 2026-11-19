"""Maya web app: one page, POST /ask, GET /health.

Run inside the maya-app container (see scripts/run_app.sh):
  uvicorn app.main:app --host 0.0.0.0 --port 8443 --ssl-keyfile certs/key.pem --ssl-certfile certs/cert.pem
"""
import asyncio
import base64
import contextlib
import logging
import tempfile
import time
from pathlib import Path

import yaml
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import media
from .models import ModelManager
from .router import RoutingLog, media_kind, route
from .safety import safety_filter
from .stt import Stt
from .tts import Tts

ROOT = Path(__file__).resolve().parent
CFG = yaml.safe_load((ROOT / "config.yaml").read_text())
STATIC = ROOT / "static"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
log = logging.getLogger("maya")

STUB_TEXT = {
    "sound_id": "Sound identification is not available yet. Please send a photo or a video instead.",
    "document_qa": "Questions about documents are not available yet. Take a photo of the page and tap Read this.",
    "code_exec": "Running code is not available yet.",
}
NO_MEDIA_TEXT = ("I need a photo or a video to answer that. Tap Ask about what is in front of me, "
                 "or tap Read this.")


class State:
    models: ModelManager = None
    stt: Stt = None
    tts: Tts = None
    routing: RoutingLog = None
    startup_s: dict = {}


S = State()


async def _reaper():
    while True:
        await asyncio.sleep(5)
        try:
            await asyncio.to_thread(S.models.reap_idle)
        except Exception:
            log.exception("idle reaper failed")


@contextlib.asynccontextmanager
async def lifespan(_app):
    S.routing = RoutingLog(CFG["logs"]["routing"])
    S.models = ModelManager(CFG["models"], CFG["logs"]["models"])
    t = time.perf_counter()
    S.tts = await asyncio.to_thread(Tts, CFG["tts"]["repo"], CFG["tts"]["voice"])
    S.startup_s["tts"] = round(time.perf_counter() - t, 2)
    t = time.perf_counter()
    w = CFG["whisper"]
    S.stt = await asyncio.to_thread(Stt, w["size"], w["device"], w["compute_type"], w["cpu_threads"], w["language"])
    S.startup_s["whisper"] = round(time.perf_counter() - t, 2)
    t = time.perf_counter()
    first = "qwen" if CFG["models"]["qwen"].get("preload") else "cosmos"
    await asyncio.to_thread(S.models.warm_up, first)
    S.startup_s[first] = round(time.perf_counter() - t, 2)
    log.info("startup seconds %s", S.startup_s)
    task = asyncio.create_task(_reaper())
    yield
    task.cancel()


app = FastAPI(title="Maya", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


def _speak(text, lat):
    t = time.perf_counter()
    wav = S.tts.wav_bytes(text)
    lat["tts"] = round((time.perf_counter() - t) * 1000)
    return base64.b64encode(wav).decode()


def _display(text):
    # The app font has no em or en dash glyph; model output can contain both.
    return text.replace(" — ", ", ").replace("—", ", ").replace("–", "-")


async def _save(upload, path):
    data = await upload.read()
    Path(path).write_bytes(data)
    return len(data)


def _answer(r, kind, question, file_path, work, lat):
    """Blocking part of /ask: preprocess, model, safety. Runs in a worker thread."""
    to = CFG["timeouts"]["ffmpeg_s"]
    info = {}
    t = time.perf_counter()
    if r.model == "cosmos":
        clip = f"{work}/window.mp4"
        v = CFG["video"]
        media.last_window(file_path, clip, work, v["window_s"], v["fps"], v["long_side"], to)
        lat["preprocess"] = round((time.perf_counter() - t) * 1000)
        raw, info = S.models.ask_video(clip, question)
    else:
        img_path = file_path
        if kind == "video":
            img_path = f"{work}/last.png"
            media.last_frame(file_path, img_path, to)
        image = media.load_image(img_path, CFG["image"]["long_side"])
        lat["preprocess"] = round((time.perf_counter() - t) * 1000)
        raw, info = S.models.ask_image(image, question or "Describe what is in this photo and read any text.")
    lat["load"] = round(info["load_s"] * 1000)
    lat["model"] = round(info["model_s"] * 1000)
    t = time.perf_counter()
    text, flagged = safety_filter(_display(raw))
    lat["safety"] = round((time.perf_counter() - t) * 1000)
    return raw, text, flagged, info["input_tokens"]


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
    return {"status": "ok", "gpu": S.models.status(), "whisper": S.stt is not None,
            "tts": S.tts is not None, "startup_s": S.startup_s}


@app.post("/ask")
async def ask(file: UploadFile | None = File(None), question: str | None = Form(None),
              question_audio: UploadFile | None = File(None)):
    t0 = time.perf_counter()
    lat = {}
    question = (question or "").strip()
    with tempfile.TemporaryDirectory() as work:
        if question_audio is not None and question_audio.filename:
            qa = f"{work}/question{Path(question_audio.filename).suffix or '.webm'}"
            await _save(question_audio, qa)
            t = time.perf_counter()
            heard = await asyncio.to_thread(S.stt.transcribe, qa)
            lat["stt"] = round((time.perf_counter() - t) * 1000)
            question = heard or question

        kind, file_path, size = None, None, 0
        if file is not None and file.filename:
            kind = media_kind(file.filename, file.content_type)
            file_path = f"{work}/upload{Path(file.filename).suffix}"
            size = await _save(file, file_path)
        r = route(kind, question)
        log_extra = dict(kind=kind, question=question, file_bytes=size,
                         content_type=getattr(file, "content_type", None))

        if r.model is None:
            text = NO_MEDIA_TEXT if r.name == "no_media" else STUB_TEXT[r.name]
            status = 400 if r.name == "no_media" else 501
            audio = await asyncio.to_thread(_speak, text, lat)
            lat["total"] = round((time.perf_counter() - t0) * 1000)
            S.routing.write(r, status=status, latency_ms=lat, **log_extra)
            return JSONResponse({"text": text, "route": r.name, "question": question,
                                 "latency_ms": lat, "audio_b64": audio}, status_code=status)

        try:
            raw, text, flagged, n_in = await asyncio.wait_for(
                asyncio.to_thread(_answer, r, kind, question, file_path, work, lat),
                CFG["timeouts"]["request_s"])
        except Exception as e:
            log.exception("ask failed")
            text = "Sorry, something went wrong while looking. Please try again."
            audio = await asyncio.to_thread(_speak, text, lat)
            lat["total"] = round((time.perf_counter() - t0) * 1000)
            S.routing.write(r, status=500, error=repr(e), latency_ms=lat, **log_extra)
            return JSONResponse({"text": text, "route": r.name, "question": question,
                                 "latency_ms": lat, "audio_b64": audio, "error": repr(e)},
                                status_code=500)

        audio = await asyncio.to_thread(_speak, text, lat)
        lat["total"] = round((time.perf_counter() - t0) * 1000)
        S.routing.write(r, status=200, raw=raw, text=text, flagged=flagged,
                        input_tokens=n_in, latency_ms=lat, **log_extra)
        return {"text": text, "route": r.name, "model": r.model, "question": question,
                "flagged": flagged, "latency_ms": lat, "audio_b64": audio}


def _stub(name):
    r = route(None, None)
    r.name, r.reason = name, f"{name}: not built"
    S.routing.write(r, status=501)
    return JSONResponse({"text": STUB_TEXT[name], "route": name}, status_code=501)


@app.post("/document/ask")
def document_ask():
    return _stub("document_qa")


@app.post("/code/run")
def code_run():
    return _stub("code_exec")
