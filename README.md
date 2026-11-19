# Maya

An offline assistant for low-vision users, built for the IEEE AI Hackathon
(Multimodal LLM Challenge). It answers questions about what the phone camera
sees, reads signs, and warns about people and vehicles coming toward you
during a walk.

Everything runs on one laptop GPU with open-weight models. There are no cloud
APIs at runtime.

Safety rule: Maya describes; it never decides. It says "Person ahead," never
"Move left" or "Safe to cross." Steering was tested and rejected (see
`docs/decisions.md` D2 and D3). The rule is enforced three ways:
- the prompts tell the model not to give instructions
- a filter checks every answer after it is generated (`app/safety.py`)
- a test, `tests/test_safety.py`

## What's in it

| Path | What |
|---|---|
| `app/` | FastAPI server and the phone web page (HTTPS, port 8443). `POST /ask` takes a photo, video clip or spoken question and returns text plus speech. |
| `scripts/perception.py` | Fast perception at about 50 ms per frame: D-FINE detector, Depth Anything V2 metric depth, and an IoU tracker. Gives each object a side, a motion label and a time to contact. |
| `scripts/fused_harness.py` | Simulated live walk on a video. Perception warnings come first; Cosmos facts are optional. Writes an annotated mp4 with the spoken audio. |
| `scripts/live_harness.py` | The earlier harness that uses only the vision-language model, plus the shared helpers (Piper TTS, ffmpeg cuts, safety filter). |
| `scripts/score_walk.py` | Scores a harness run against hand labels, with a lenient table and a strict table. |
| `scripts/run_walk_eval.sh`, `scripts/sweep_v2.py` | Re-run the walk evaluation, and sweep warning thresholds. |
| `scripts/compare_image_models.py` | Cosmos3-Edge vs Qwen3-VL on sign and label reading. |
| `docker/` | `cosmos-tf` (models and harness) and `app` (adds faster-whisper) images. |
| `test_videos/labels/` | Hand labels for the 4 walk clips (44 events). The clips themselves are not in git. |
| `results/` | Scores, logs, sweeps and image comparisons. Videos and audio files are ignored. |
| `docs/decisions.md` | Every measured decision, D1 to D9. Start here. |
| `docs/app.md`, `docs/phone_setup.md` | App endpoints, and how to trust the local certificate on a phone. |
| `docs/hardware.md`, `docs/research/` | Dev machine notes and research write-ups (perception, OCR, audio, documents, demo plan). |

## Models

| Use | Model | License |
|---|---|---|
| Images, video, documents, code, questions about speech (the engine's main model) | `Qwen/Qwen3-VL-4B-Instruct`, quantized to NF4 on load (about 3.6 GiB) | Apache-2.0 |
| Code fallback, only after failed self-checks | `Qwen/Qwen2.5-Coder-7B-Instruct`, NF4 (the VLM is unloaded first) | Apache-2.0 |
| Speech to text | faster-whisper `small.en`, CPU | MIT |
| Sound identification | `laion/clap-htsat-unfused` (CLAP, zero-shot), CPU | Apache-2.0 |
| Speech or sound routing, sound timelines | `MIT/ast-finetuned-audioset-10-10-0.4593` (AST), CPU | BSD-3-Clause |
| Walk mode: object detection | `ustc-community/dfine-small-obj365` | Apache-2.0 code; the Objects365 weights are not cleared for commercial use |
| Walk mode: depth | `depth-anything/Depth-Anything-V2-Metric-Outdoor-Small-hf` | Apache-2.0 (VKITTI Small) |
| Earlier walk slow path (not used by the engine) | `ubr-physical-ai/Cosmos3-Edge-NF4-bnb` (4-bit, about 2.4 GiB) | OpenMDW-1.1 |
| Text to speech | Piper (`piper-tts` 1.8, OHF-Voice/piper1-gpl) with the `en_US-lessac-medium` voice, CPU | GPL-3.0-or-later (engine); the voice has its own model card |

One large model stays on the GPU at a time (8 GB card, about 2 GB taken by
the display). Audio models run on the CPU.

## Setup

You need:
- Windows 11 with WSL2 and Docker Desktop
- an NVIDIA GPU with 8 GB or more and a recent driver
- Git Bash, for the scripts

The host needs no Python; everything runs in containers.

```bash
docker volume create hf-cache
docker build -t maya-cosmos-tf docker/cosmos-tf
docker build -t maya-app docker/app
```

The first run of anything downloads the models into the `hf-cache` volume.
After that, `HF_HUB_OFFLINE=1` works.

## Run the app (phone test)

```bash
bash scripts/run_app.sh                  # https://<laptop-ip>:8443
MAYA_DETACH=1 bash scripts/run_app.sh    # in the background
MAYA_OFFLINE=1 bash scripts/run_app.sh   # demo mode: no network
```

The phone must be on the same Wi-Fi and must trust the local CA once
(`docs/phone_setup.md`). To run the tests:

```bash
MSYS_NO_PATHCONV=1 docker run --rm -v "$(pwd -W)":/app -w /app maya-app python -m pytest tests
```

## Run the walk evaluation

Put the clips in `test_videos/`. Ask the repo owner for the files. Each clip
is named after its labels file:
- `fifth-avenue-point-of-view-manhattan-nyc-looking-around-day.mp4`
- `3874684_720p.mp4`
- `london_walking.mp4`
- `197531-905015052_medium.mp4`

Then:

```bash
# per-frame tracks, once per clip (GPU)
MSYS_NO_PATHCONV=1 docker run --rm --gpus all -v hf-cache:/root/.cache/huggingface \
  -v "$(pwd -W)":/app -w /app maya-cosmos-tf python scripts/perception.py --video test_videos/london_walking.mp4 \
  --out results/perception/london_walking.jsonl
# fast-path harness on all clips, then the strict scores
bash scripts/run_walk_eval.sh
```

Output goes to `results/live/<clip>_fastonly2/` (`annotated.mp4`, `log.csv`)
and `results/walk_scores_strict.md`.

## Where it stands (2026-11-19 morning)

Practice pack (100 items, the kinds judges ask live): **97/100**. On sets the
engine was not tuned on:

| Set | Score |
|---|---|
| Held-out set made tonight | 64/68 |
| SQuAD 2.0 extra | 46/60 |
| VizWiz extra | 72/80 |
| LibriSpeech extra | 34/40 |
| ESC-50 extra | 84/100 |
| HumanEval extra, all 144 | 125/144 |
| MBPP extra | 25/30 |

Run them: `bash scripts/gpu_job.sh pack python scripts/eval_pack.py --run <name> [--pack <folder>]`.

Walk mode v3 (tones), on 11 SANPO chest-camera clips scored by tracked identity:
24/33 warnings on time (v2: 15/33).

Known gaps and next steps: `docs/overnight_report.md`.
