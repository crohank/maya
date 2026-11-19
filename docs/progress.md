# Progress log

> Older snapshot (D1 to D5). Current state: `README.md` and `docs/decisions.md` D6 to D9.

Snapshot: 2026-11-18 evening. Code due 2026-11-19 end of day, demo 2026-11-20 1 PM.
Detailed measurements and reasoning live in `docs/decisions.md` (D1 to D5).

## Working now (measured)

| Piece | State | Numbers |
|---|---|---|
| Cosmos3-Edge NF4 (`ubr-physical-ai/Cosmos3-Edge-NF4-bnb`) video reasoning | runs in Docker image `maya-cosmos-tf` | 0.5 s per 2 s clip, 2.4 GiB peak |
| Live walking harness (`scripts/live_harness.py`) | simulated live, pipelined, newest-answer speaker | speech starts about 1 s after newest frame seen |
| Piper TTS (`en_US-lessac-medium`) | CPU | about 0.1 s per sentence |
| Safety filter (regex in `scripts/live_harness.py`) | catches cross/go/clear phrasing | checked on 5 sentences |
| Qwen3-VL-4B NF4 image reading | fixed Conv3d slowdown (D5) | about 2 s per image, 3.6 GiB peak, 6/10 strict (about 8/10 loose) |

## Decisions so far

- Walk mode describes, never steers. Steering ("move left/right") was wrong or
  dangerous on all 4 clips and showed a right-side bias (D2, D3).
- Text memory of earlier answers made the VLM copy itself; rejected (D4).
- Carry-over between frames comes from object tracks, not from the VLM (D4).
- llama.cpp ruled out for Cosmos (no GGUF, MoT architecture). vLLM not used
  before the deadline (D1, research 02).

## In progress (parallel agents, started 2026-11-18 evening)

| Workstream | Owner files | Output |
|---|---|---|
| Perception: D-FINE detector + Depth Anything V2 Small/Metric + ByteTrack | `scripts/perception.py`, `docs/perception.md`, `results/perception/` | per-frame tracks: side, distance, motion, time to contact |
| Ground-truth labels + scorer for the 4 clips | `test_videos/labels/`, `scripts/score_walk.py`, `results/walk_scores.*` | hit rate, lead time, false alarms per run |
| FastAPI backend + accessible phone page over HTTPS | `app/`, `tests/`, `docker/app/`, `docs/app.md`, `docs/phone_setup.md` | `/ask`, `/health`, rule router, model swap |
| Research: audio, docs + code, practice pack | `docs/research/04..06_*.md` | recommendations with sources |

Done research: `docs/research/01_perception_stack.md`, `02_image_ocr.md`, `03_demo_plan.md`.

## Next steps (in order)

1. Fuse perception into the harness: fast-path rule warnings (near or TTC < 3 s,
   3 of 5 frames, 5 s per-object cooldown) plus Cosmos given the top 3 tracks and
   asked for one thing tracks cannot know (sign, curb, crosswalk) or NONE.
2. Score describe vs fused on all 4 clips with `scripts/score_walk.py`.
3. Wire audio (faster-whisper on CPU + AST sounds), document Q&A (BM25 +
   NOT_IN_DOCUMENT), code run (sandboxed subprocess) into the app.
4. Download the practice pack (Kaggle CLI, user's token) and run
   `scripts/eval_practice_pack.py`.
5. Phone over HTTPS end to end; demo script and fallback clips (research 03).
6. README with hardware, models, licenses, measured tables, named limits.

## How to run what exists

```
docker run --rm --gpus all -v hf-cache:/root/.cache/huggingface -v "${PWD}:/app" -w /app -e HF_HUB_OFFLINE=1 maya-cosmos-tf python scripts/live_harness.py --video test_videos/london_walking.mp4 --modes describe
docker run --rm --gpus all -v hf-cache:/root/.cache/huggingface -v "${PWD}:/app" -w /app -e HF_HUB_OFFLINE=1 maya-cosmos-tf python scripts/compare_image_models.py
```

## Environment gotchas

- Dev GPU is 8 GB with about 2.8 GB held by the display (dGPU drives the screen).
  OMEN Gaming Hub, Graphics Switcher, Hybrid frees it (needs reboot).
- Docker Desktop hung once (engine 500 errors, VM unreachable). Fix: `wsl --shutdown`
  then start Docker Desktop. The torch profiler run happened right before it; avoid it.
- Host has no Python; run scripts inside the container.
