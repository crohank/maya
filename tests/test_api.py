"""/ask, /document/ask and /code/run with a fake Engine, TTS and STT (CPU only, no models)."""
import json
import subprocess
import sys
import time
import wave
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app import main  # noqa: E402
from app.router import RoutingLog  # noqa: E402
from app.safety import SAFE_SUFFIX  # noqa: E402


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "stream=codec_type,codec_name,sample_rate,channels:format=format_name,duration",
                          "-of", "json", str(path)], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


class FakeEngine:
    """Records each call and what the file looked like while it still existed."""

    def __init__(self):
        self.calls = []
        self.reply = ("A dog on a sofa.", {"route": "fake", "model_s": 0.01})
        self.error = None
        self.sleep = 0

    def answer(self, modality, path, question):
        seen = {}
        if path is not None:
            p = Path(path)
            seen["suffix"] = p.suffix
            seen["bytes"] = p.read_bytes()
            if p.suffix == ".wav":
                with wave.open(str(p)) as w:
                    seen["wav"] = (w.getnchannels(), w.getframerate(), w.getsampwidth())
            elif p.suffix == ".mp4":
                seen["probe"] = probe(p)
            elif p.suffix in (".jpg", ".ppm"):
                with Image.open(p) as im:
                    seen["size"] = im.size
        self.calls.append({"modality": modality, "path": path, "question": question, **seen})
        if self.sleep:
            time.sleep(self.sleep)
        if self.error:
            raise self.error
        return self.reply


class FakeTts:
    def __init__(self):
        self.said = []

    def wav_bytes(self, text):
        self.said.append(text)
        return b"RIFFfake"


class FakeStt:
    def __init__(self, text="What is ahead of me?"):
        self.text = text
        self.calls = 0

    def transcribe(self, path):
        self.calls += 1
        return self.text


@pytest.fixture
def env(monkeypatch, tmp_path):
    eng, tts, stt = FakeEngine(), FakeTts(), FakeStt()
    monkeypatch.setattr(main.S, "engine", eng)
    monkeypatch.setattr(main.S, "tts", tts)
    monkeypatch.setattr(main.S, "stt", stt)
    monkeypatch.setattr(main.S, "routing", RoutingLog(tmp_path / "routing.jsonl"))
    with TestClient(main.app) as client:
        yield client, eng, tts, stt, tmp_path


def ff(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *map(str, args)], check=True)


@pytest.fixture(scope="module")
def media(tmp_path_factory):
    d = tmp_path_factory.mktemp("media")
    src = ["-f", "lavfi", "-i", "testsrc=size=320x240:rate=10:duration=5"]
    tone = ["-f", "lavfi", "-i", "sine=frequency=440:duration=3"]
    ff(*tone, "-ac", "2", "-ar", "44100", d / "stereo44k.wav")
    ff(*tone, "-c:a", "libopus", d / "voice.webm")
    ff(*tone, "-c:a", "aac", d / "voice.m4a")
    ff(*src, "-c:v", "libvpx", "-b:v", "300k", d / "clip.webm")
    ff(*src, "-c:v", "libvpx", "-b:v", "300k", "-f", "webm", "-live", "1", d / "live.webm")
    ff(*src, "-c:v", "libx264", "-pix_fmt", "yuv420p", d / "clip.mp4")
    ff(*src, "-c:v", "mpeg4", d / "clip.mov")
    im = Image.new("RGB", (40, 20), "red")
    exif = Image.Exif()
    exif[0x0112] = 6   # Orientation: rotate 90 CW on display
    im.save(d / "rotated.jpg", exif=exif)
    Image.new("RGB", (30, 30), "blue").save(d / "plain.png")
    (d / "doc.txt").write_text("The bridge opened in 1932.", encoding="utf-8")
    (d / "doc.pdf").write_bytes(b"%PDF-1.4 fake")
    (d / "stub.py").write_text('def add(a, b):\n    """>>> add(1, 2)\n    3\n    """\n', encoding="utf-8")
    return d


def post(client, path="/ask", file=None, ct=None, question=None, qaudio=None, name=None):
    files = {}
    if file is not None:
        files["file"] = (name or Path(file).name, Path(file).read_bytes(), ct or "application/octet-stream")
    if qaudio is not None:
        files["question_audio"] = ("question.webm", Path(qaudio).read_bytes(), "audio/webm")
    data = {"question": question} if question is not None else {}
    return client.post(path, files=files or None, data=data)


def test_photo_exif_rotated_and_safety_filtered(env, media):
    client, eng, tts, _, _ = env
    eng.reply = ("A crosswalk — wide. It is safe to cross.", {"model_s": 0.5})
    res = post(client, file=media / "rotated.jpg", ct="image/jpeg", question="What is this?")
    assert res.status_code == 200
    body = res.json()
    call = eng.calls[0]
    assert (call["modality"], call["question"], call["suffix"]) == ("image", "What is this?", ".jpg")
    assert call["size"] == (20, 40)
    assert body["route"] == "photo" and body["flagged"] is True
    assert "safe to cross" not in body["text"] and body["text"].endswith(SAFE_SUFFIX)
    assert "—" not in body["text"]
    assert tts.said == [body["text"]] and body["audio_b64"]
    assert body["latency_ms"]["model"] == 500


def test_photo_default_question(env, media):
    client, eng, _, _, _ = env
    res = post(client, file=media / "plain.png", ct="image/png")
    assert res.status_code == 200
    assert eng.calls[0]["question"] == main.DEFAULT_Q["image"]


@pytest.mark.parametrize("name, ct", [("stereo44k.wav", "audio/wav"), ("voice.webm", "audio/webm"),
                                      ("voice.m4a", "audio/mp4"),
                                      # MediaRecorder audio-only WebM labelled as video.
                                      ("voice.webm", "video/webm")])
def test_audio_converted_to_16k_mono_wav(env, media, name, ct):
    client, eng, _, _, _ = env
    res = post(client, file=media / name, ct=ct, question="Transcribe this audio.")
    assert res.status_code == 200, res.text
    call = eng.calls[0]
    assert call["modality"] == "audio" and call["wav"] == (1, 16000, 2)
    assert res.json()["route"] == "sound"


def test_audio_without_question_passes_empty(env, media):
    client, eng, _, _, _ = env
    assert post(client, file=media / "stereo44k.wav", ct="audio/wav").status_code == 200
    assert eng.calls[0]["question"] == ""


@pytest.mark.parametrize("name, ct", [("clip.webm", "video/webm"), ("clip.mov", "video/quicktime"),
                                      ("clip.webm", "application/octet-stream")])
def test_video_converted_to_h264_mp4(env, media, name, ct):
    client, eng, _, _, _ = env
    res = post(client, file=media / name, ct=ct, question="What happens?")
    assert res.status_code == 200, res.text
    call = eng.calls[0]
    assert call["modality"] == "video" and call["suffix"] == ".mp4"
    p = call["probe"]
    assert "mp4" in p["format"]["format_name"]
    assert [s["codec_name"] for s in p["streams"]] == ["h264"]
    # Uploaded videos go whole, not cut to the live window.
    assert float(p["format"]["duration"]) > 4.5


def test_h264_mp4_passed_through(env, media):
    client, eng, _, _, _ = env
    res = post(client, file=media / "clip.mp4", ct="video/mp4", question="What happens?")
    assert res.status_code == 200
    assert eng.calls[0]["bytes"] == (media / "clip.mp4").read_bytes()


def test_video_read_question_sends_last_frame(env, media):
    client, eng, _, _, _ = env
    res = post(client, file=media / "clip.webm", ct="video/webm", question="What does the sign say?")
    assert res.status_code == 200
    call = eng.calls[0]
    assert (call["modality"], call["suffix"]) == ("image", ".ppm")
    assert res.json()["route"] == "video_read"


def test_live_clip_with_spoken_question_is_windowed(env, media):
    client, eng, _, stt, _ = env
    res = post(client, file=media / "live.webm", ct="video/webm", qaudio=media / "voice.webm")
    assert res.status_code == 200, res.text
    assert stt.calls == 1 and res.json()["question"] == "What is ahead of me?"
    call = eng.calls[0]
    assert call["modality"] == "video" and call["question"] == "What is ahead of me?"
    assert float(call["probe"]["format"]["duration"]) <= main.CFG["video"]["window_s"] + 0.3
    assert "stt" in res.json()["latency_ms"]


def test_tiny_question_audio_skips_whisper(env, media, tmp_path):
    client, eng, _, stt, _ = env
    tiny = tmp_path / "q.webm"
    tiny.write_bytes(b"\x1aE\xdf\xa3\x00")
    res = post(client, file=media / "plain.png", ct="image/png", question="Read this", qaudio=tiny)
    assert res.status_code == 200 and stt.calls == 0
    assert eng.calls[0]["question"] == "Read this"


@pytest.mark.parametrize("name, ct", [("doc.txt", "text/plain"), ("doc.pdf", "application/pdf")])
def test_document(env, media, name, ct):
    client, eng, _, _, _ = env
    res = post(client, file=media / name, ct=ct, question="When did the bridge open?")
    assert res.status_code == 200
    call = eng.calls[0]
    assert call["modality"] == "text" and call["suffix"] == Path(name).suffix
    assert call["bytes"] == (media / name).read_bytes()


def test_document_endpoint(env, media):
    client, eng, _, _, _ = env
    res = post(client, "/document/ask", file=media / "doc.txt", ct="text/plain", question="When?")
    assert res.status_code == 200 and eng.calls[0]["modality"] == "text"
    res = post(client, "/document/ask", question="When?")
    assert res.status_code == 400 and res.json()["audio_b64"]
    assert len(eng.calls) == 1


CODE = 'def add(a, b):\n    # sum — of two\n    return a + b\n'


def test_code_text_only(env):
    client, eng, tts, _, _ = env
    eng.reply = (CODE, {"route": "code", "self_checks": 3, "self_checks_passed": 3, "self_check_ok": True})
    res = post(client, question="Complete this Python function:\n\ndef add(a, b):\n    pass\n")
    assert res.status_code == 200
    body = res.json()
    assert eng.calls[0]["modality"] == "code" and eng.calls[0]["path"] is None
    assert body["text"] == CODE and body["code"] == CODE
    assert body["spoken"] == "Here is the function. It passed all 3 of its own examples."
    assert tts.said == [body["spoken"]]
    assert body["flagged"] is False and body["info"]["self_checks"] == 3


@pytest.mark.parametrize("info, spoken", [
    ({}, "Here is the function."),
    ({"self_checks": 0, "self_checks_passed": 0}, "Here is the function. The prompt had no examples to check it against."),
    ({"self_checks": 1, "self_checks_passed": 1}, "Here is the function. It passed its own example."),
    ({"self_checks": 4, "self_checks_passed": 2},
     "Here is the function. It passed 2 of its 4 own examples, so check it before use."),
])
def test_code_summary(info, spoken):
    assert main.code_summary(info) == spoken


def test_code_run_endpoint_forces_code(env):
    client, eng, _, _, _ = env
    eng.reply = (CODE, {})
    res = post(client, "/code/run", question="reverse a list in place")
    assert res.status_code == 200 and eng.calls[0]["modality"] == "code"
    assert res.json()["spoken"] == "Here is the function."


def test_py_file_becomes_code_prompt(env, media):
    client, eng, _, _, _ = env
    eng.reply = (CODE, {})
    res = post(client, file=media / "stub.py", ct="text/x-python")
    assert res.status_code == 200
    call = eng.calls[0]
    assert call["modality"] == "code" and "def add(a, b):" in call["question"]


def test_no_file_plain_question_is_400(env):
    client, eng, tts, _, _ = env
    res = post(client, question="What is the weather today?")
    assert res.status_code == 400 and res.json()["route"] == "no_media"
    assert tts.said and not eng.calls


def test_unsupported_file_is_415(env, tmp_path):
    client, eng, _, _, _ = env
    f = tmp_path / "x.xyz"
    f.write_bytes(b"\x00" * 3000)
    res = post(client, file=f, question="What is this?")
    assert res.status_code == 415 and res.json()["audio_b64"] and not eng.calls


@pytest.mark.parametrize("name, ct", [("clip.webm", "video/webm"), ("q.webm", "audio/webm")])
def test_header_only_recording_is_422(env, tmp_path, name, ct):
    client, eng, _, _, _ = env
    f = tmp_path / name
    f.write_bytes(b"\x1aE\xdf\xa3\x00")
    res = post(client, file=f, ct=ct)
    assert res.status_code == 422 and res.json()["text"] == main.MSG["too_short"]
    assert not eng.calls


@pytest.mark.parametrize("name, ct", [("bad.mp4", "video/mp4"), ("bad.wav", "audio/wav"),
                                      ("bad.jpg", "image/jpeg")])
def test_corrupt_upload_is_422(env, tmp_path, name, ct):
    client, eng, _, _, _ = env
    f = tmp_path / name
    f.write_bytes(b"not a real file " * 300)
    res = post(client, file=f, ct=ct, question="What is this?")
    assert res.status_code == 422 and res.json()["text"] == main.MSG["unreadable"]
    assert not eng.calls


def test_engine_error_is_500_and_spoken(env, media):
    client, eng, tts, _, _ = env
    eng.error = RuntimeError("CUDA out of memory")
    res = post(client, file=media / "plain.png", ct="image/png", question="What?")
    assert res.status_code == 500
    assert res.json()["text"] == main.MSG["error"] and tts.said == [main.MSG["error"]]


def test_engine_timeout_is_504(env, media, monkeypatch):
    client, eng, _, _, _ = env
    monkeypatch.setitem(main.CFG["timeouts"], "request_s", 0.2)
    eng.sleep = 1.0
    res = post(client, file=media / "plain.png", ct="image/png", question="What?")
    assert res.status_code == 504 and res.json()["text"] == main.MSG["timeout"]


def test_routing_log_written(env, media):
    client, _, _, _, tmp = env
    post(client, file=media / "plain.png", ct="image/png", question="What?")
    rows = [json.loads(line) for line in (tmp / "routing.jsonl").read_text().splitlines()]
    assert rows[-1]["name"] == "photo" and rows[-1]["status"] == 200 and rows[-1]["modality"] == "image"


def test_health(env):
    client, *_ = env
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["engine"] is True
