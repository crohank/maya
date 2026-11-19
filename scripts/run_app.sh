#!/usr/bin/env bash
# Start the Maya app on https://<laptop-ip>:8443 (Git Bash on Windows).
#   bash scripts/run_app.sh            # foreground, Ctrl+C stops it
#   MAYA_DETACH=1 bash scripts/run_app.sh   # background container named maya-app
# Certificates are (re)issued for the current LAN IPv4 addresses when missing
# or when MAYA_NEW_CERT=1. Override the addresses with MAYA_HOSTS="192.168.1.23".
set -euo pipefail
cd "$(dirname "$0")/.."
export MSYS_NO_PATHCONV=1
ROOT="$(pwd -W 2>/dev/null || pwd)"

if [ -z "${MAYA_HOSTS:-}" ]; then
  # IPv4 lines from ipconfig, minus loopback and the WSL / Hyper-V 172.x adapters.
  MAYA_HOSTS="$(ipconfig.exe 2>/dev/null | tr -d '\r' | grep -E 'IPv4' | sed -E 's/.*: *//' \
    | grep -vE '^(127\.|172\.(1[6-9]|2[0-9]|3[01])\.)' | tr '\n' ' ' || true)"
fi

if [ ! -f certs/cert.pem ] || [ "${MAYA_NEW_CERT:-0}" = 1 ]; then
  docker run --rm -v "$ROOT":/app -w /app maya-app bash docker/app/make_certs.sh $MAYA_HOSTS
fi

used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
echo "GPU memory used before start: ${used} MiB"

args=(--rm --gpus all -p 8443:8443 --name maya-app
      -v hf-cache:/root/.cache/huggingface -v "$ROOT":/app -w /app)
[ "${MAYA_DETACH:-0}" = 1 ] && args+=(-d)

for h in $MAYA_HOSTS; do echo "Phone URL: https://$h:8443"; done
docker run "${args[@]}" maya-app \
  uvicorn app.main:app --host 0.0.0.0 --port 8443 \
  --ssl-keyfile certs/key.pem --ssl-certfile certs/cert.pem
