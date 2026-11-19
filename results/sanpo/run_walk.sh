#!/usr/bin/env bash
# Fast-path walk harness (v2 rules, no VLM, CPU) on every SANPO clip that has
# perception output, then the strict scorer. Run from the repo root in Git Bash.
set -euo pipefail
cd "$(dirname "$0")/../.."
run() {
  MSYS_NO_PATHCONV=1 docker run --rm --network none -e HF_HUB_OFFLINE=1 \
    -v hf-cache:/root/.cache/huggingface -v "$(pwd -W 2>/dev/null || pwd):/app" -w /app \
    -e PYTHONPATH=/app maya-engine "$@"
}
labels=() logs=()
for p in results/sanpo/perception/sanpo_*_summary.json; do
  s=$(basename "$p" _summary.json)
  if [ ! -f "results/sanpo/live/${s}_fastonly2/log.csv" ]; then
    run python scripts/fused_harness.py --video "data/sanpo/clips/$s.mp4" --no-vlm --rules v2 \
      --perception "results/sanpo/perception/$s.jsonl" --out results/sanpo/live | tail -1
  fi
  labels+=(--labels "data/sanpo/labels/$s.json")
  logs+=(--log "results/sanpo/live/${s}_fastonly2/log.csv")
done
run python scripts/score_walk.py "${labels[@]}" "${logs[@]}" --out results/sanpo/walk_scores_sanpo.md
