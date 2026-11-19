#!/usr/bin/env bash
# Fast-path walk eval: run the fused harness without Cosmos on every labelled
# clip, then score all runs. Needs results/perception/<stem>.jsonl (perception.py).
# Usage from Git Bash at the repo root: bash scripts/run_walk_eval.sh [v1|v2]
set -euo pipefail
RULES=${1:-v2}
SUFFIX=$([ "$RULES" = v2 ] && echo fastonly2 || echo fastonly)
run() {
  MSYS_NO_PATHCONV=1 docker run --rm -v hf-cache:/root/.cache/huggingface \
    -v "$(pwd -W 2>/dev/null || pwd):/app" -w /app -e HF_HUB_OFFLINE=1 maya-cosmos-tf "$@"
}
labels=() logs=()
for f in test_videos/labels/*.json; do
  stem=$(basename "$f" .json)
  labels+=(--labels "$f")
  run python scripts/fused_harness.py --video "test_videos/$stem.mp4" --no-vlm --rules "$RULES"
done
for m in describe instruct fastonly fused fastonly2; do
  for d in results/live/*_"$m"; do [ -f "$d/log.csv" ] && logs+=(--log "$d/log.csv"); done
done
run python scripts/score_walk.py "${labels[@]}" "${logs[@]}" --out results/walk_scores_strict.md
