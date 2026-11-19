# Maya app

FastAPI + uvicorn over HTTPS on port 8443, in the `maya-app` Docker image
(`docker/app/Dockerfile`: `maya-cosmos-tf` plus faster-whisper, pyyaml, pytest).
Settings live in `app/config.yaml`. Phone setup: `docs/phone_setup.md`.

## Run

```
docker build -t maya-app docker/app      # once
bash scripts/run_app.sh                  # foreground; MAYA_DETACH=1 for background
MAYA_OFFLINE=1 bash scripts/run_app.sh   # demo: no network, models from the hf-cache volume
```

The script makes `certs/` on first run, then runs (Git Bash):

```
MSYS_NO_PATHCONV=1 docker run --rm --gpus all -p 8443:8443 --name maya-app \
  -v hf-cache:/root/.cache/huggingface -v "$(pwd -W)":/app -w /app maya-app \
  uvicorn app.main:app --host 0.0.0.0 --port 8443 \
  --ssl-keyfile certs/key.pem --ssl-certfile certs/cert.pem
```

Startup loads Piper (0.6 to 0.9 s), whisper small (1 s cached, 11 s first
download) and Cosmos with one warm-up call (5.6 to 8 s). Tests:
`docker run --rm -v "$(pwd -W)":/app -w /app maya-app python -m pytest tests`.

## Endpoints

| Method, path | What it does |
|---|---|
| `GET /` | The page (`app/static/index.html`, `app.js`, `app.css`) |
| `POST /ask` | Multipart: `file` (photo, video or sound, optional), `question` (text, optional), `question_audio` (optional; transcribed with whisper and used as the question). Returns `{text, route, model, question, flagged, latency_ms, audio_b64}`; `audio_b64` is the answer as Piper WAV. |
| `GET /health` | Loaded models, free and allocated VRAM, startup seconds |
| `GET /ca.crt` | The local CA certificate, for installing on a phone |
| `POST /document/ask` | Stub, 501 |
| `POST /code/run` | Stub, 501 |

`latency_ms` keys: `stt` (whisper), `preprocess` (ffmpeg cut or frame grab,
image load), `load` (model load or swap, 0 when already on the GPU), `model`
(generate), `safety`, `tts`, `total` (server side, upload excluded).

Errors are spoken too: every non-200 reply still carries `text` and `audio_b64`.
400 for no photo or video attached, 501 for stubs, 500 if a model call fails.

## Routing (`app/router.py`)

Rules, no model involved, checked in this order:

| Input | Route | Model |
|---|---|---|
| Video + question containing read, sign, text, label, bus number, written, menu, price (and a few variants) | `video_read`: last frame (within 0.25 s) at full resolution | Qwen3-VL-4B |
| Video + any other question (or none) | `video_scene`: last 2 s at 4 fps, long side 448 px | Cosmos3-Edge |
| Photo + any question | `photo`, long side capped at 1280 px, EXIF rotation applied | Qwen3-VL-4B |
| Sound file | `sound_id` | stub, 501 |
| PDF or office document | `document_qa` | stub, 501 |
| Nothing attached | `no_media` | none, 400 |

An uploaded video is treated like the rolling clip: only its last 2 s are used.
Each request adds one JSON line to `results/app_routing.jsonl` (route, reason,
question, raw and filtered answer, input tokens, latency per stage).

Every model answer goes through `app/safety.py` (copied from
`scripts/live_harness.py`): a sentence that says safe to cross, you can cross, go
ahead, the road or path is clear and similar is dropped and replaced with "I can
describe what I see, but I can't tell you when it's safe." Em and en dashes in
model output are replaced, since the app font has no glyph for them.

Cosmos gets the user's question plus "Answer in one short sentence about what
you see." On "Is it safe to cross?" it once returned only timestamps (`<0.75
seconds> <1.25 seconds> ...`); such output is retried with the default describe
prompt from the live harness.

## VRAM plan (`app/models.py`)

8 GB card, about 5.2 GB free. Cosmos NF4 holds 2.22 GiB, Qwen3-VL-4B NF4 holds
3.26 GiB. With both loaded (5.5 GiB allocated) `mem_get_info` reported 0.0 GiB
free, so `models.exclusive: true`: one vision model on the GPU at a time.

- Cosmos loads at startup.
- A photo or read request unloads Cosmos and loads Qwen (a swap).
- A scene request while Qwen is loaded swaps back.
- Qwen unloads after `idle_unload_s` (90 s) without use; Cosmos then reloads,
  so the GPU never sits empty.
- The first Qwen load quantizes the BF16 checkpoint (22 s) and saves the NF4
  weights to `/root/.cache/huggingface/maya/qwen3vl-4b-nf4` in the hf-cache
  volume; later loads read that copy (3.2 to 6.3 s).
- One GPU job at a time (a lock around load, unload and generate).
- Loads, unloads and swaps with timings and free VRAM go to
  `results/app_models.jsonl`.

`exclusive: false` keeps both when free VRAM is at least the incoming model's
`need_gib`, for a GPU with more room.

## Measured latencies

RTX 5060 Laptop 8 GB, from `curl -k` on the same machine, 2026-11-18. Files:
`test_images/syn_bus_sign.png`; a 2 s cut (13 to 15 s) of
`test_videos/3874684_720p.mp4`; an 8 s WebM cut written with `-live 1` (no
duration in the header, like MediaRecorder); question audio "What does the sign
say?" made with Piper. Raw rows in `results/app_routing.jsonl` and
`results/app_routing_run1.jsonl`.

| Request | Answer | stt | preprocess | load | model | tts | total |
|---|---|---|---|---|---|---|---|
| 2 s clip, "What is ahead of me?", Cosmos warm | "A black car is ahead of you, positioned in the middle of the road." | | 0.19 to 0.32 s | 0 | 0.65 to 1.11 s | 0.12 to 0.37 s | 1.0 to 1.8 s |
| Same, Cosmos swapped back in | same | | 0.20 to 0.42 s | 2.7 to 4.0 s | 0.71 to 0.79 s | 0.12 to 0.27 s | 3.8 to 5.3 s |
| Bus photo, "What bus is this?", Qwen warm | "This is the M15 bus." | | 0.002 s | 0 | 0.72 to 0.83 s | 0.04 to 0.13 s | 0.85 to 0.87 s |
| Same, swap from Cosmos (cached NF4) | same | | | 4.2 to 6.3 s | 0.78 to 0.99 s | | 5.4 to 7.1 s |
| Same, very first Qwen load (quantize and save) | same | | | 22.0 s | 1.04 s | | 23.1 s |
| Bus photo + spoken question, Qwen warm | "The sign says "M15 SELECT BUS SOUTH FERRY"." | 1.21 s | | 0 | 1.13 s | 0.13 s | 2.5 s |
| 8 s WebM + spoken question (read route), Qwen warm | "The sign says "NO ENTRY"." | 1.08 s | 0.73 s | 0 | 1.07 s | 0.13 s | 3.0 s |
| Same, with swap | same | 1.26 s | 0.91 s | 3.4 s | 1.37 s | 0.22 s | 7.1 s |
| 2 s clip, "Is it safe to cross?" | "A black car approaching on the left." | | 0.28 s | 0 | 1.74 s | 0.22 s | 2.2 s |

Whisper small int8 on CPU transcribed the Piper question correctly every time.

## Page (`app/static/`)

- "Ask about what is in front of me": two staggered MediaRecorders on the rear
  camera (with audio) keep the last 5 to 10 s. First tap stops the older one
  (clip ends at the tap) and starts recording the spoken question; second tap
  (or 15 s) sends clip plus question audio.
- "Read this": grabs the current camera frame as JPEG and asks "Read the text".
- Upload a photo, video or sound, with an optional typed question.
- Answer in a large `aria-live="assertive"` region; status in `role="status"`.
  Answer audio plays unless "Speak answers aloud" is off (screen reader users may
  prefer the screen reader voice alone).
- Real `<button>` elements whose visible text is the accessible name, so iOS Voice
  Control and Android Voice Access can tap them by name. Recording state changes
  the button text and border style, not only colour.

Checked with the Browser pane accessibility tree: all buttons, the question
field and the checkbox have the names above. The pane would not open
`https://localhost:8443` (it does not trust the local CA and cannot bypass the
warning), so the live page with camera was not exercised there.

## Known gaps

- Not tested on a real phone yet: the MediaRecorder clip path is covered only by
  the synthetic `-live 1` WebM. iPhone Safari records MP4; the server accepts it
  but it has not been tried.
- Document Q&A, code execution and sound identification are not built:
  `POST /document/ask`, `POST /code/run`, and `/ask` with a sound or document
  file return 501 with a spoken message.
- Every swap costs 3 to 6 s, so alternating "Read this" and "Ask" is slow. A text
  question while Qwen is loaded waits for the swap.
- Small street text still needs a zoom crop (docs/decisions.md D5); the read
  route sends the whole last frame. On the 3874684 clip Qwen read "ONAL PARKING",
  a cut-off sign.
- Text-only questions (no photo or video) are not answered.
- A request that hits `timeouts.request_s` returns an error, but the GPU call
  keeps running in its thread until it finishes.
