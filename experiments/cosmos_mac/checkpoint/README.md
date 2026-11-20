# Cosmos3-Edge walk-mode experiments on Apple Silicon (checkpoint)

These scripts test NVIDIA Cosmos3-Edge (BF16 `nvidia/Cosmos3-Edge`, transformers 5.23, MPS) for Maya's walk mode, on the London Canary Wharf clip.
They were written as one-off experiments. They contain absolute paths to the author's Mac (repo root, the source clip in `~/Downloads`), so edit those paths before running.

The main script is `../sim_walk_cosmos_only.py`. It runs a simulated live walk:
- Walk v3 triggers with detector confidence of 0.7 or higher ask Cosmos for a move.
- At other times, Cosmos gives a short describe.
- It renders `results/live/london_cosmos_sim_conf70/sim.mp4` and `log.csv`. The hand grading is in `eval.md`.

| Script | What it tested |
|---|---|
| `walk_prompts.py` | Four describe-prompt variants on three 2 s windows: the current prompt, chest-camera framing, framing with thinking, and tracks plus JSON |
| `eyes_prompt.py`, `eyes_card.py` | The "be my eyes" Left/Ahead/Right prompt, first with greedy decoding, then with the model card's settings (thinking on, sampling, MP4 at 4 fps) |
| `annotate.py`, `make_boxed.py` | Draw detector boxes coloured by side onto the frames, and write 4 fps MP4s |
| `eyes_boxed.py`, `eyes_boxed_v2.py` | The same prompt on the colour-boxed clips. v2 says "I've marked ... for your convenience" |
| `cosmos_boxes.py`, `cosmos_boxes_v2.py` | Cosmos returning its own bounding boxes, with variants P1, P2 and P3. Its coordinates are on a 0 to 1000 scale. |
| `guide_test.py` | Cosmos boxes plus a step instruction from the 2 s clip |
| `sim_walk_v1.py` | An earlier version of the simulation, with the long describe prompt and no confidence filter |

Results are in `results/live/london_cosmos_sim*/`. The MP4s are gitignored. Walk steering instructions are a research test only; the product rule is still "describe, never decide" (docs/decisions.md D2 and D3).
