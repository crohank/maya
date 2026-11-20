#!/usr/bin/env bash
# The recommended walk setting from the 2026-11-20 overnight reviews (v6), for the clips given
# as stems. Needs results/perception/<stem>.jsonl, results/scene/<stem>_{cv2,stripes,path}.jsonl
# in the main checkout (mounted at /main). Add --move-gate 0.8 --options xk for Cosmos steering.
python experiments/cosmos_combined/sim_walk_combined.py "$@" \
  --scene-tag cv2 --corner stripes --corner-word "Curb and crosswalk ahead." --stages 0 --vlm-obstacles 0 \
  --describe off --steps 1 --stairs 0 --traffic-gap 20 --alert-repeat 30 --window 1.0 \
  --wset still_min_h=0.07 --wset still_words=1 --wset steps_style=short --wset riders=1 \
  --traffic-near-corner 10 --path-obstacles 1 --move-gate 0.4 --trigger-ttc 0.1 --options sk
