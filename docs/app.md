# Maya app

FastAPI + uvicorn over HTTPS on port 8443. Every answer comes from one
`maya.engine.Engine` for the whole process (`Engine.answer(modality, path,
question)`), which keeps at most one model on the GPU. Settings live in
`app/config.yaml`. Phone setup: `docs/phone_setup.md`.

## Run

The app needs the `maya-engine` image (`docker/engine/Dockerfile`: `maya-app`
plus pypdf, rank_bm25, soundfile), since the engine reads PDFs with pypdf.
`scripts/run_app.sh` still starts `maya-app`; until it is switched, run (Git Bash):

```
MSYS_NO_PATHCONV=1 docker run --rm --gpus all -e HF_HUB_OFFLINE=1 \
  -p 8443:8443 --name maya-app \
  -v hf-cache:/root/.cache/huggingface -v "$(pwd -W)":/app -w /app -e PYTHONPATH=/app maya-engine \
  uvicorn app.main:app --host 0.0.0.0 --port 8443 \
  --ssl-keyfile certs/key.pem --ssl-certfile certs/cert.pem
```

`--network none` cannot be used here, since the phone reaches the app through
the published port; `HF_HUB_OFFLINE=1` keeps every model load on the hf-cache
volume.

Startup loads Piper, whisper small (for spoken questions) and Qwen3-VL-4B NF4
(`engine.preload: true`), so the first request does not pay the model load.

Tests (CPU only, fake Engine, no models):

```
MSYS_NO_PATHCONV=1 docker run --rm --network none -v "$(pwd -W):/app" -w /app \
  -e PYTHONPATH=/app maya-engine python -m pytest tests -q
```

## Endpoints

| Method, path | What it does |
|---|---|
| `GET /` | The page (`app/static/index.html`, `app.js`, `app.css`) |
| `POST /ask` | Multipart: `file` (optional), `question` (text, optional), `question_audio` (optional; transcribed with whisper and used as the question). Answers all five item kinds, see Routing. |
| `POST /document/ask` | Same as `/ask`; 400 with a spoken message if no file is attached. |
| `POST /code/run` | `question` (and optionally a `.py` `file`); the question is treated as a coding prompt even when it does not look like one. |
| `GET /health` | Engine present, GPU models loaded, free and allocated VRAM, startup seconds |
| `GET /ca.crt` | The local CA certificate, for installing on a phone |

Reply: `{text, spoken, route, modality, question, flagged, latency_ms, audio_b64, info}`.
`text` is what the page shows, `spoken` is what `audio_b64` (Piper WAV) says,
`info` is the engine's info dict. For code, `text` and `code` hold the function
exactly as generated and `spoken` is a short summary built from
`info.self_checks` and `info.self_checks_passed`, for example "Here is the
function. It passed all 3 of its own examples." Code is never read aloud.

`latency_ms` keys: `stt` (whisper on the spoken question), `preprocess` (ffmpeg
conversion, frame grab, image rotate), `wait` (queued behind another request
for the engine), `engine` (the whole `Engine.answer` call), `model` (the
engine's own `model_s`, when it reports one), `safety`, `tts`, `total` (server
side, upload excluded).

Errors are spoken too: every non-200 reply still carries `text` and `audio_b64`.

| Status | When |
|---|---|
| 400 | No file and the question is not a coding prompt; `/document/ask` without a file |
| 415 | File type not recognised |
| 422 | Recording under 2000 bytes (a header-only MediaRecorder clip), or a file ffmpeg or PIL cannot open |
| 500 | The engine raised |
| 504 | The engine took longer than `timeouts.request_s` (120 s; `code_request_s` 240 s for code) |

## Routing (`app/router.py`)

File type decides first (extension, then content type), the question second.
No model is involved.

| Input | Route | Conversion before the engine | `Engine.answer` modality |
|---|---|---|---|
| Image (jpg, png, webp, bmp, gif) | `photo` | EXIF rotation applied, long side capped at 1920 px, saved as JPEG | `image` |
| Audio (wav, webm, m4a, mp3, ogg, opus, aac, flac) | `sound` | ffmpeg to 16 kHz mono 16-bit WAV | `audio` |
| Video file whose only stream is audio (MediaRecorder WebM) | `sound` | same as audio | `audio` |
| Document (txt, pdf, also md, docx, html) | `document_qa` | none | `text` |
| Video (mp4, webm, mov, mkv, avi, m4v) + question with read, sign, text, label, menu, price and similar | `video_read` | last frame (within 0.25 s) | `image` |
| Uploaded video + any other question | `video_scene` | H.264 MP4 passed through; anything else re-encoded to H.264 MP4, long side 960 | `video` |
| Live clip (video + `question_audio`, from "Ask about what is in front of me") | `video_scene` | last 2 s at 4 fps, long side 448, H.264 MP4 | `video` |
| `.py` file | `code` | file text appended to the question | `code` |
| No file + question with a `def` line, a code fence, "python", or "write/implement/complete ... function" | `code` | none | `code` |
| No file, any other question | `no_media` | | none, 400 |

Empty questions get a default: "Describe what is in this photo and read any
text." for photos, "What is happening in this video?" for uploaded videos,
"What is in front of me?" for live clips, "What is this document about?" for
documents. Audio passes an empty question, and `maya/audio.py` decides from the
audio whether to transcribe or describe.

All pack code prompts route to `code` and no other pack question does (checked
in `tests/test_router.py` on the practice pack).

Each request adds one JSON line to `results/app_routing.jsonl` (route, reason,
question, raw and filtered answer, engine info, latency per stage).

Every spoken answer except code goes through `app/safety.py` (copied from
`scripts/live_harness.py`): a sentence that says safe to cross, you can cross,
go ahead, the road or path is clear and similar is dropped and replaced with "I
can describe what I see, but I can't tell you when it's safe." Em and en dashes
in model output are replaced, since the app font has no glyph for them. Code is
returned unchanged.

## GPU

One `Engine` per process, and a lock around `Engine.answer`, so requests run
one at a time; `latency_ms.wait` shows time spent queued. The engine holds
Qwen3-VL-4B NF4 for image, video, document, audio questions and code (with the
default `coder=vlm`). Engine options go in `engine.opts` in `app/config.yaml`,
the same strings as `--opt key=value` in `scripts/eval_pack.py`.

A request that hits its timeout returns 504, but the engine call keeps running
in its thread and holds the lock until it finishes.

## Measured latencies

RTX 5060 Laptop 8 GB, 2026-11-19, practice-pack items, real Engine, Piper and
whisper, called in-process with FastAPI TestClient inside a `scripts/gpu_job.sh`
job (upload over the network not included). Two runs per item where shown (r1
then r2, same process). Audio ran in a second process, because the first one
had loaded a `maya/sound.py` that was mid-edit (500 on every audio request,
`AttributeError: module 'maya.sound' has no attribute 'ast_model'`). Answers
are as returned, not scored here.

Startup: Piper 0.88 to 1.11 s, whisper small 1.44 to 4.86 s, Qwen3-VL load 9.59 to 17.02 s.

| Request | Answer | stt | preprocess | engine (model) | tts | total |
|---|---|---|---|---|---|---|
| Image p_img_001, first request after startup | "1" | | 0.01 s | 4.69 s (4.64) | 0.05 s | 4.76 s |
| Same, r2 | "1" | | 0.01 s | 0.51 s (0.41) | 0.09 s | 0.62 s |
| Audio p_aud_002 WAV, "Transcribe this audio." r1 / r2 | the transcript | | 0.05 / 0.10 s | 4.11 / 3.23 s | 0.80 / 0.82 s | 4.97 / 4.17 s |
| Audio p_aud_001 WAV, question about the speech r1 / r2 | "It was a churning day." | | 0.11 / 0.10 s | 4.28 / 3.72 s (1.36 / 0.83) | 0.13 / 0.07 s | 4.54 / 3.88 s |
| Audio p_aud_011 converted to Opus WebM, "What sound is this?" r1 / r2 | "It sounds like a chainsaw." | | 0.08 / 0.09 s | 0.90 / 0.98 s | 0.25 / 0.15 s | 1.23 / 1.22 s |
| Document p_txt_001 TXT r1 / r2 | "Governor Vaudreuil." | | 0 | 3.05 / 3.84 s (3.04 / 3.82) | 0.08 / 0.05 s | 3.14 / 3.90 s |
| Same question, the PDF copy, `POST /document/ask` | "Governor Vaudreuil." | | 0 | 3.78 s (3.67) | 0.13 s | 3.92 s |
| Video p_vid_001 MP4 (H.264, passed through) r1 / r2 | "5 shapes appear in the video." | | 0.07 / 0.07 s | 1.49 / 1.58 s (1.03 / 1.16) | 0.09 / 0.12 s | 1.65 / 1.78 s |
| Same video converted to VP8 WebM (re-encoded to MP4) | same | | 0.39 s | 1.92 s (1.25) | 0.31 s | 2.63 s |
| Live clip: that WebM + Piper "What is in front of me?" as Opus WebM | "The red circle." | 2.34 s | 0.53 s | 0.73 s (0.66) | 0.15 s | 3.75 s |
| Code p_code_001, text only r1 / r2 | the function; spoken "It passed all 6 of its own examples." | | | 3.11 / 4.12 s (2.99 / 3.98) | 0.33 / 0.48 s | 3.44 / 4.60 s |
| Code p_code_002, `POST /code/run` | the function; spoken "It passed all 3 of its own examples." | | | 7.92 s (7.73) | 0.61 s | 8.53 s |

Engine time includes CPU work outside `model_s`: whisper and the sound
classifier for audio, frame decoding for video, the sandbox self-checks for code.
The first image request pays a one-time warm-up of the vision path (4.69 s vs
0.51 s). The engine reports no `model_s` on the transcribe and sound routes.

ffmpeg conversion of the MediaRecorder-style WebM files in `heldout/` (no
duration in the header; CPU, conversion only, not answered): two Opus audio
files to 16 kHz mono WAV in 0.22 and 0.25 s; three VP8 videos (5.0, 6.5, 7.5 s)
to H.264 MP4 in 0.79, 1.06 and 1.22 s.

## Page (`app/static/`)

- "Ask about what is in front of me": two staggered MediaRecorders on the rear
  camera (with audio) keep the last 5 to 10 s. First tap stops the older one
  (clip ends at the tap) and starts recording the spoken question; second tap
  (or 15 s) sends clip plus question audio.
- "Read this": grabs the current camera frame as JPEG and asks "Read the text".
- Upload a photo, video or sound, with an optional typed question.
- Answer in a large `aria-live="assertive"` region; status in `role="status"`.
  Answer audio plays unless "Speak answers aloud" is off.
- Real `<button>` elements whose visible text is the accessible name, so iOS Voice
  Control and Android Voice Access can tap them by name.

## Known gaps

- The page has no document upload button and no way to send a typed question
  without a file, so documents and code prompts are reachable only through the
  API (`curl`, or the endpoints above) until the page is changed.
- Not tested on a real phone yet: the MediaRecorder paths are covered by
  synthetic WebM files in `tests/test_api.py`. iPhone Safari records MP4; the
  server accepts it but it has not been tried.
- HEIC photos are not supported (PIL in the image has no HEIC decoder); they get
  a 422.
- The safety filter also runs on transcripts and document answers, so a
  recording that says "go ahead" is transcribed with that sentence replaced.
- A timed-out engine call keeps the GPU busy until it finishes.
