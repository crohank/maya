# Overnight brief (agents read this first)

Project: Maya, an offline multimodal assistant (IEEE AI Hackathon). Repo root:
`C:\Users\Rohan Kumar\Documents\Projects\IEEE Hackathon`. Use Git Bash. The host
has no Python; everything runs in Docker image `maya-engine`.

## What is judged

`Kaggle Data/README.md`: during the live demo, judges pick random items of the
same five kinds as the practice pack (new photos, recordings, documents, videos
and coding prompts, plus surprise items), and the assistant answers them live
with Wi-Fi off. The practice pack (`Kaggle Data/items.json`, `answers.json`, 100
items) is our dev set. **Do not hard-code anything about specific pack items**
(answers, file names, the exact 10 ESC-10 sound classes, the exact video
templates). Methods must generalize to new items of the same kind. When you
report a number, say it is on the practice pack.

## Code layout

- `maya/engine.py`: `Engine(**opts).answer(modality, path, question) -> (text, info)`.
  `eng.opts` holds `--opt key=value` strings. `eng.vlm` lazily loads Qwen3-VL-4B NF4
  (`maya/vlm.py`, `chat(content, system, max_new_tokens)` and `text(prompt, ...)`).
  `eng.gpu_model(name, loader)` holds at most one GPU model (frees the others).
  `eng.cache` is a dict for CPU models.
- One module per modality: `maya/image.py`, `video.py`, `docqa.py`, `code.py`, `audio.py`.
  Each has `answer(eng, path, question)`.
- `scripts/eval_pack.py`: runs and scores items. Scoring rules in its docstring;
  hand-written keys in `scripts/pack_keys.json`. Results go to `results/pack/<run>.csv|.md`.

## How to run (GPU)

Every GPU or model run goes through the lock script. Never call `docker run --gpus` yourself.

```bash
bash scripts/gpu_job.sh <tag> python scripts/eval_pack.py --modality code --run code_v1 [--opt key=value]
bash scripts/gpu_job.sh <tag> python -c "..."        # ad-hoc checks
```

- It waits for the GPU lock (other agents share the GPU), so a run may queue for minutes. That is expected.
- Network is OFF inside these jobs (models come from the `hf-cache` volume). Model-written code runs there too.
- `scripts/gpu_guard.sh` pauses jobs if the GPU reaches 82 C and resumes at 72 C. A paused job is not a hang.
- Keep runs small while iterating (`--ids` or one modality). Do not loop the full pack.
- CPU-only checks without a model can use:
  `MSYS_NO_PATHCONV=1 docker run --rm --network none -v "$(pwd -W):/app" -w /app -e PYTHONPATH=/app maya-engine python ...`

## Downloads

Allowed only from official publisher repos on Hugging Face and from PyPI, and only
when needed. Download with network on but no GPU:
`MSYS_NO_PATHCONV=1 docker run --rm -v hf-cache:/root/.cache/huggingface maya-engine python -c "from huggingface_hub import snapshot_download; snapshot_download('ORG/NAME')"`.
Disk is tight (22 GB free on C:): NO new model downloads at all without asking the lead first. Already cached:
Qwen3-VL-4B-Instruct (+ NF4 copy), Cosmos3-Edge NF4, faster-whisper small, small.en,
distil-large-v3, MIT/ast-finetuned-audioset-10-10-0.4593, laion/clap-htsat-unfused,
Qwen/Qwen2.5-Coder-3B-Instruct, D-FINE small obj365 and COCO, Depth Anything V2 small.
No new pip packages in the image: if you need one, say so in your report.

## Rules

- Own only the files your task names. Do not edit `maya/vlm.py`, `maya/engine.py`,
  `scripts/eval_pack.py`, `scripts/pack_keys.json` or another agent's files; ask the lead
  in your report if a shared change is needed.
- Do not git commit, push, or touch other Docker containers.
- Nothing leaves the machine.
- User-visible text (answers the assistant speaks, docs) never uses em or en dashes.
- Code comments only for what the code cannot say (why, measured numbers, external constraints).
- Never invent or round up results. Report what you measured, including failures.

## Report back

Variants tried with practice-pack scores and median seconds per item, the config you
recommend (default options in code), which items still fail and why, and files changed.
