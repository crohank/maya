"""End-to-end smoke test: the real app in-process (TestClient) with the real engine.

  bash scripts/gpu_job.sh smoke python scripts/smoke_app.py
Prints one ROW per request: status, route, server latency, answer.
"""
import json
import subprocess
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app import main

K = Path("Kaggle Data")
items = {i["id"]: i for i in json.loads((K / "items.json").read_text(encoding="utf-8"))}
T = Path("/tmp/smoke")
T.mkdir(exist_ok=True)


def ff(*a):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *map(str, a)], check=True)


ff("-i", K / "audio/p_aud_011.wav", "-c:a", "libopus", T / "aud011.webm")
ff("-i", K / "video/p_vid_001.mp4", "-c:v", "libvpx", "-b:v", "1M", "-an", T / "vid001.webm")

rows = []


def run(tag, path="/ask", file=None, ct=None, question=None, qaudio=None):
    files = {}
    if file:
        files["file"] = (Path(file).name, Path(file).read_bytes(), ct)
    if qaudio:
        files["question_audio"] = ("question.webm", Path(qaudio).read_bytes(), "audio/webm")
    data = {"question": question} if question else {}
    t = time.perf_counter()
    r = c.post(path, files=files or None, data=data)
    wall = round(time.perf_counter() - t, 2)
    b = r.json()
    row = {"tag": tag, "status": r.status_code, "route": b.get("route"), "wall_s": wall,
           "latency_ms": b.get("latency_ms"), "text": (b.get("text") or "")[:300],
           "spoken": b.get("spoken"), "question": (b.get("question") or "")[:80],
           "info_keys": sorted((b.get("info") or {}).keys()), "error": b.get("error")}
    rows.append(row)
    print("ROW", json.dumps(row), flush=True)


def item(iid):
    i = items[iid]
    return K / i["file"] if i["file"] else None, i["question"]


t0 = time.perf_counter()
with TestClient(main.app) as c:
    print("STARTUP", json.dumps(main.S.startup_s), round(time.perf_counter() - t0, 2), flush=True)
    wav = main.S.tts.wav_bytes("What is in front of me?")
    (T / "q.wav").write_bytes(wav)
    ff("-i", T / "q.wav", "-c:a", "libopus", T / "q.webm")
    for rnd in (1, 2):
        f, q = item("p_img_001"); run(f"image p_img_001 r{rnd}", file=f, ct="image/jpeg", question=q)
        f, q = item("p_aud_002"); run(f"audio p_aud_002 wav r{rnd}", file=f, ct="audio/wav", question=q)
        f, q = item("p_txt_001"); run(f"document p_txt_001 txt r{rnd}", file=f, ct="text/plain", question=q)
        f, q = item("p_vid_001"); run(f"video p_vid_001 mp4 r{rnd}", file=f, ct="video/mp4", question=q)
        _, q = item("p_code_001"); run(f"code p_code_001 r{rnd}", question=q)
        if rnd == 1:
            _, q = item("p_aud_011"); run("audio p_aud_011 as webm", file=T / "aud011.webm", ct="audio/webm", question=q)
            _, q = item("p_txt_001")
            run("document p_txt_001 pdf /document/ask", "/document/ask",
                file=K / "text/p_txt_doc_01.pdf", ct="application/pdf", question=q)
            _, q = item("p_vid_001"); run("video p_vid_001 as webm", file=T / "vid001.webm", ct="video/webm", question=q)
            run("live clip webm + spoken question", file=T / "vid001.webm", ct="video/webm", qaudio=T / "q.webm")
            _, q = item("p_code_002"); run("code p_code_002 /code/run", "/code/run", question=q)
            run("code, no file, plain words", question="Implement binary search over a sorted list.")
    print("HEALTH", json.dumps(c.get("/health").json()), flush=True)
