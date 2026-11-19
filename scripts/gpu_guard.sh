#!/usr/bin/env bash
# GPU heat watchdog for unattended runs. Every 15 s: log temperature, power and
# memory to results/gpu_temps.csv; at HOT_C or above, docker-pause every running
# container whose name starts with maya-job; unpause at COOL_C or below.
# The laptop is new and the user asked to keep the GPU from running hot.
HOT_C=${HOT_C:-82}
COOL_C=${COOL_C:-72}
LOG=results/gpu_temps.csv
cd "$(dirname "$0")/.."
[ -f "$LOG" ] || echo "time,temp_c,power_w,mem_used_mib,util_pct,action" > "$LOG"
paused=0
while true; do
  read -r temp power mem util < <(nvidia-smi --query-gpu=temperature.gpu,power.draw,memory.used,utilization.gpu \
    --format=csv,noheader,nounits | head -1 | tr -d ' ' | tr ',' ' ')
  action=""
  jobs=$(docker ps --filter name=maya-job --format '{{.Names}}' 2>/dev/null)
  if [ -n "$temp" ] && [ "$temp" -ge "$HOT_C" ] && [ "$paused" = 0 ] && [ -n "$jobs" ]; then
    docker pause $jobs >/dev/null 2>&1 && paused=1 && action="pause $jobs"
  elif [ "$paused" = 1 ] && [ -n "$temp" ] && [ "$temp" -le "$COOL_C" ]; then
    jobs=$(docker ps --filter name=maya-job --filter status=paused --format '{{.Names}}')
    [ -n "$jobs" ] && docker unpause $jobs >/dev/null 2>&1
    paused=0; action="unpause $jobs"
  fi
  echo "$(date +%H:%M:%S),$temp,$power,$mem,$util,$action" >> "$LOG"
  sleep 15
done
