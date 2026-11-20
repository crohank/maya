# How the London simulation video was made, end to end

This is every step behind `results/live/london_cosmos_sim_conf70/sim.mp4`, in order. Steps 1 and 2 use scripts and outputs that are already in the repo from the main branch.

## 0. Setup (Apple Silicon Mac)

```bash
uv venv --python 3.12 cosmos-env
VIRTUAL_ENV=$PWD/cosmos-env uv pip install torch torchvision "transformers==5.23.0" accelerate av pillow "huggingface_hub[hf_xet]" opencv-python-headless torchcodec
# Cosmos3-Edge reasoner weights, about 7.7 GB (vision encoder and transformer only)
cosmos-env/bin/python -c "from huggingface_hub import snapshot_download; snapshot_download('nvidia/Cosmos3-Edge', allow_patterns=['*.json','*.jinja','vision_encoder/*','transformer/*'])"
```

`ffmpeg` must be on the PATH (`brew install ffmpeg`).

The source clip is the 20 s Canary Wharf video (768×432, 30 fps), the same footage as `test_videos/london_walking.mp4` (gitignored). The scripts read it from the path in `SRC`. Change that path to match your copy.

## 1. Detector tracks (main branch, already committed)

`scripts/perception.py` runs D-FINE, Depth Anything V2 and an IoU tracker. It writes `results/perception/london_walking.jsonl` (8 fps).

## 2. Walk v3 triggers (main branch, already committed)

`scripts/walk_v3.py run --video test_videos/london_walking.mp4` writes `results/live/london_walking_v3/log.csv`. The simulation uses this file's trigger events.

## 3. Pick the confidence cutoff

```bash
python experiments/cosmos_mac/checkpoint/tools/trigger_confidence.py results/perception/london_walking.jsonl results/live/london_walking_v3/log.csv
```

## 4. Simulated walk with Cosmos (this makes the video)

```bash
HF_HUB_OFFLINE=1 cosmos-env/bin/python -u experiments/cosmos_mac/sim_walk_cosmos_only.py
```

It writes `sim.mp4` (the MP4 is gitignored) and `log.csv`. Edit `REPO`, `SRC` and `OUT` at the top of the script first.

Earlier versions of the video:
- `checkpoint/sim_walk_v1.py`: long describe prompt, no confidence filter.
- The `_short` and `_short2` runs: the same script with the describe-prompt edits described in the commit history.

## 5. Grading aids

```bash
# frame strips per call (2 s before, at request, at speech)
cosmos-env/bin/python experiments/cosmos_mac/checkpoint/tools/eval_strips.py <clip.mp4> results/perception/london_walking.jsonl results/live/london_cosmos_sim_conf70 <out_dir> --min-conf 0.7
# one track's history and box (the false "pole")
cosmos-env/bin/python experiments/cosmos_mac/checkpoint/tools/show_track.py <clip.mp4> results/perception/london_walking.jsonl 102 11.6 pole_track102.png
# all detector boxes on one frame
cosmos-env/bin/python experiments/cosmos_mac/checkpoint/tools/draw_tracks_frame.py <clip.mp4> results/perception/london_walking.jsonl 4.0 london_boxes_t4.png
# rescore the saved practice-pack video runs (no model)
python experiments/cosmos_mac/checkpoint/tools/rescore_video_runs.py
```

The grades themselves are in the `eval.md` files. They were made by eye from these strips.
