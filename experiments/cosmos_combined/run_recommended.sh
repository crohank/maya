#!/usr/bin/env bash
# The recommended walk setting from the 2026-11-20 overnight reviews (v11: v10 plus head-on words), for the clips given
# as stems. Needs results/perception/<stem>.jsonl and results/scene/<stem>_{lg,stripes}.jsonl in
# the main checkout (mounted at /main): perception.py, lane_ground_probe.py, stripes.py.
# Add --move-gate 0.8 --options xk (and drop the last line's MOVE flags) for Cosmos steering.
python experiments/cosmos_combined/sim_walk_combined.py "$@" \
  --scene-tag lg --path-tag lg --corner stripes --corner-word "Curb and crosswalk ahead." --stages 0 \
  --vlm-obstacles 0 --describe off --steps 1 --stairs 0 --traffic-gap 20 --alert-repeat 30 --window 1.0 \
  --wset still_min_h=0.07 --wset still_words=1 --wset steps_style=short --wset riders=1 --wset headon_x=0.5 \
  --traffic-near-corner 10 --path-obstacles 1 --corner-gap 20 \
  --move-gate 0.4 --trigger-ttc 0.1 --options sk
