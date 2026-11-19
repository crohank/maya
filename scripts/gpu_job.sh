#!/usr/bin/env bash
# Run one command in the maya-cosmos-tf image on the GPU, one job at a time.
# Usage: bash scripts/gpu_job.sh <tag> <command...>
# A lock directory serializes jobs from parallel agents; gpu_guard.sh pauses
# containers named maya-job-* when the GPU is hot.
set -uo pipefail
cd "$(dirname "$0")/.."
tag=$1; shift
lock=.gpu_lock
until mkdir "$lock" 2>/dev/null; do
  # A lock older than 3 h is left over from a killed job.
  if [ -n "$(find "$lock" -maxdepth 0 -mmin +180 2>/dev/null)" ]; then rmdir "$lock"; fi
  sleep 5
done
echo "$tag $$ $(date +%H:%M:%S)" > "$lock/owner"
trap 'rm -rf "$lock"' EXIT
# Network off by default: models come from hf-cache, and model-written code runs here.
net=(--network none -e HF_HUB_OFFLINE=1)
[ "${NET:-0}" = 1 ] && net=()
MSYS_NO_PATHCONV=1 docker run --rm --gpus all "${net[@]}" --name "maya-job-$tag-$$" \
  -v hf-cache:/root/.cache/huggingface -v "$(pwd -W 2>/dev/null || pwd):/app" -w /app \
  -e PYTHONPATH=/app -e PYTHONUNBUFFERED=1 "${IMAGE:-maya-engine}" "$@"
