# Design decisions

## D1. Cosmos3-Edge runs as NF4 4-bit through transformers, in Docker

**Context.** Dev GPU is an RTX 5060 Laptop, 8 GB VRAM, with about 2.8 GB held by
the desktop (the dGPU drives the display). See `docs/hardware.md`.

**Options considered.**
- BF16 `nvidia/Cosmos3-Edge` on vLLM (the model card's path). Reasoner weights
  are about 4.9 GB; with about 5.2 GB free there is no room for KV cache or
  video activations. Card says Linux only, BF16 only tested.
- llama.cpp. No GGUF exists and the Mixture-of-Transformers architecture is
  not supported. Ruled out.
- `ubr-physical-ai/Cosmos3-Edge-NF4-bnb` (bitsandbytes NF4, reasoner only,
  2.4 GB download, OpenMDW-1.1 license). Its card tests it with transformers;
  its vLLM command is auto-generated and untested.

**Choice.** NF4 build on transformers 5.23 + bitsandbytes 0.50.2, torch
2.9.0+cu128 (cu128 needed for sm_120), in Docker on WSL2
(`docker/cosmos-tf/Dockerfile`). Nothing installed on the host.

**Measured** (`scripts/smoke_cosmos.py`, 2026-11-18):

| Test | Latency | Input tokens | Peak VRAM |
|---|---|---|---|
| Model load (warm disk cache) | 4.8 s | | 2.22 GiB |
| Synthetic sign image, "What does the sign say?" | 2.51 s | 369 | 2.33 GiB |
| 15 s Fifth Ave sidewalk clip (768x432, 30 fps), native video input | 5.94 s | 10,411 | 4.32 GiB |

Linear4bit module count 169, matching the card (the vision tower stayed BF16).

Video answer, checked by hand against frames: named the man in black jacket and
blue cap walking toward camera, stroller on the right, large decorative sphere
on the right (all correct). Missed the cyclist and the road on the left.

**Open.** Frame count the processor samples by default is not yet pinned to the
brief's 4 fps / 40 frames. vLLM path not tried yet.

## D2. Walk mode describes; it does not give steering instructions

**Test.** `scripts/live_harness.py` on the 54.5 s Fifth Avenue sidewalk clip,
simulated live: 4 s window at 4 fps, 640 px wide, next look starts when the
previous sentence finishes, repeats kept silent, Piper `en_US-lessac-medium`.
Outputs in `results/live/`.

| Mode | Model time | TTS time | Lag, last frame seen to speech start | Peak VRAM |
|---|---|---|---|---|
| describe | 1.4 to 2.7 s | 0.08 to 0.32 s | 1.5 to 2.9 s | 2.62 GiB |
| guide | 1.0 to 1.5 s | up to 0.20 s | 1.0 to 1.6 s | 2.62 GiB |

**Hand check against frames** (`results/live/contact_54s.jpg`):
- describe, 8 answers: correct on the decorative sphere (9 s), the
  "MONDAYS & WEDNESDAYS ... 1-2 PM" sign it read in full (33 s), the crosswalk
  with a woman crossing (45 s). Weak on what is "most important": led with an SUV
  on the road at 0 s while people were directly ahead; called a crosswalk at
  21 to 25 s before the intersection was in view.
- guide: stuck on "Person two steps ahead, open space on your right" while the
  right side was building walls (18, 22, 36, 40 s). At 18 to 22 s it said "open
  space on your left", which was the road. Missed the pole and trash can ahead
  at 45 s.

**Choice.** Ship describe-on-tap. Steering cues ("open space on your left")
are wrong often enough to point a user into a wall or the street, and they break
the brief's rule that Maya describes and never decides.

## D3. Latency fix (pipelined harness) and the instruct test

**Change.** 2 s window at 4 fps, 448 px (590 to 646 input tokens, down from
about 2,800), answers capped at 24 tokens / one short sentence, vision loop runs
nonstop, speaker says only the newest finished answer and drops stale ones.

**Measured**, same 54.5 s clip:

| Mode | Looks | Spoken | Model per look | Speech start minus newest frame | Speech start minus oldest frame | Peak VRAM |
|---|---|---|---|---|---|---|
| instruct | 85 | 21 | median 0.60 s, max 1.05 s | median 1.02 s, max 1.74 s | median 3.02 s, max 3.74 s | 2.37 GiB |
| describe | 85 | 25 | median 0.64 s, max 0.92 s | median 1.18 s, max 2.10 s | median 3.18 s, max 4.10 s | 2.37 GiB |

Previous run (D2) had speech 4 to 5 s long and looked only after speech ended,
so content was up to about 12 s old when heard.

**Instruct accuracy.** Across 85 looks: "move right" 65, "move left" 20, never
"keep straight" or "slow down"; the action flipped between consecutive looks
(0.6 s apart) 13 times. Hand check of 6 spoken instructions against frames
(`results/live/instruct_check.jpg`): 4 wrong or dangerous, 1 unclear, 0 clearly
right. At 28.5 s a man walks head-on on the left and it said "Move left". At
47.5 s, inside the intersection, it said "Move left, white car approaching".

**Choice.** Instruct mode stays out of the product. The speed is now fine; the
side it picks is not reliable.

**Second clip** (`197531-905015052_medium.mp4`, 16.5 s, 720x1280 portrait,
sunset promenade, near-static camera, bus enters on the right at about 3 s and
drives away along the road).
- Portrait scaled by width gave 1,598 tokens per look and 1.0 s model time. Fix:
  bound the long side to 448 px. After the fix: 610 tokens, model median 0.48 s,
  speech start minus newest frame median 0.57 s (max 1.14 s), 2.37 GiB.
- describe (after fix): "Bus approaching from right" in the window that ends as
  the bus enters, then "Bus passing on your right" (correct). From 11.6 s it said
  "Bus coming towards you" while the bus was driving away (wrong direction).
- instruct (before the portrait fix): "Move right, bus on right side" for most of
  the clip, which steers toward the road and the bus.

**Third clip** (`3874684-uhd_3840_2160_30fps.mp4`, 26.3 s, 4K downscaled once to
720p as `3874684_720p.mp4`; walking on an empty right-hand sidewalk, road on the
left, fence on the right, black car on the road at about 15 s, white pickup
crossing the intersection ahead at 17 to 20 s, curb and crosswalk at 22 to 24 s).
- Timing: model median 0.52 s, speech start minus newest frame median 0.95 s
  (max 1.77 s), 2.37 GiB.
- describe: "No obstacles in my path" on the empty sidewalk (correct), "black car
  approaching on the left" at 13 to 15 s (correct). "Pickup truck two steps
  ahead to my right" at 18 to 20 s (wrong: it was far ahead, crossing).
  "No obstacles in path" at 23 to 25 s while the curb and crosswalk were right
  ahead (missed the most important thing on the clip).
- instruct: "Move right, construction area ahead" 6 times; right was a fence and
  the construction was across the road. Last answer "Move left" at the curb,
  which is toward the road.
- Safety filter gap: "Keep straight, path ahead is clear of people" passed the
  filter. Added "(path|way|road|street|coast)( ahead)? is clear" to the pattern.

**Fourth clip** (`lLondon Walking.mp4`, copied to `london_walking.mp4`; 20.0 s,
768x432; Canary Wharf open plaza, low fast camera (the downloaded page title says
bicycle ride), people mostly crossing sideways, purple A-frame signs on the left
at 8 to 11 s).
- Timing: model median 0.52 s, speech start minus newest frame median 0.93 s
  (max 1.25 s), 2.37 GiB.
- describe: "Person walking away from you" 6 of 8 spoken answers; most people
  were crossing sideways. Never mentioned the purple signs, the closest objects
  on the left at 8 to 11 s.
- instruct: "Move right" 8 of 8 spoken answers. Right happened to be away from
  the signs at 8 to 11 s. "Man in black jacket stepping off sidewalk" at 10 to
  12 s: the plaza has no sidewalk edge there.

**Pattern over 4 clips.** instruct said "move right" 65/85, 17/17, about 9/10,
and 8/8 looks. It has a right-side bias, not a reading of the scene.

## D4. Text memory of previous answers: rejected

**Test.** describe mode, `--memory 2`: the last two answers and their age are
added to the prompt with "say whether it is now closer, farther, or moving
across". Same 4 clips, same settings as D3.

| Clip | Looks | Spoken | Silent repeats | Without memory: spoken / repeats |
|---|---|---|---|---|
| Fifth Ave 54.5 s | 88 | 7 | 63 | 25 / 0 |
| Promenade 16.5 s | 25 | 4 | 17 | 7 / 9 |
| 4K sidewalk 26.3 s | 49 | 7 | 27 | 10 / 13 |
| London 20.0 s | 36 | 2 | 32 | 8 / 6 |

The model copies its own earlier sentence instead of looking: London said
"Person walking away from you" for 32 of 36 looks; Fifth Ave never mentioned the
sphere, the sign, or the crosswalk that the no-memory run caught. It also
returned "N/A" twice and a bare "Bus.". One gain: "Pole on the right, moving
closer" at the end of the 4K clip, which the no-memory run missed.

**Choice.** No text memory. Carry-over between looks has to come from
structured state (object tracks), not from the model's own sentences.

## D5. Image reading: Qwen3-VL-4B, after a patch-embed fix

**Test.** `scripts/compare_image_models.py`, 10 items (3 real frames, 7 synthetic
with known text), pass = every required key string in the answer.

**Bug.** Qwen3-VL's vision patch embed is an `nn.Conv3d` with kernel == stride
(2,16,16). On the RTX 5060 (sm_120), torch 2.9.0+cu128, bf16, that one layer took
14 to 17 s per 640x360 image, cuDNN on or off. Replaced by one matmul over the
same weights (`Conv3dAsLinear`): 0.2 ms, max abs difference 0.008 vs the Conv3d
output (mean magnitude 0.32). Root cause (docs/research/02_image_ocr.md):
torch 2.9.0 disabled cuDNN for 3D convolutions because of broken cuDNN 9.10 to
9.14 kernels, so bf16 Conv3d falls back to a slow path on any recent GPU
(pytorch issues #168167, #166643; fixed in 2.10 / 2.9.1 with cuDNN >= 9.15).
vLLM PR #27418 and SGLang PR #20282 made the same Conv3d to Linear swap.

| Model | Passed | Median latency | p90 | Peak VRAM |
|---|---|---|---|---|
| Cosmos3-Edge NF4 | 5/10 | 1.05 s | 2.33 s | 2.44 GiB |
| Qwen3-VL-4B NF4, before fix | 6/10 | 39.3 s | 60.6 s | 3.61 GiB |
| Qwen3-VL-4B NF4, after fix | 6/10 | 1.98 s | 2.72 s | 3.61 GiB |

Both failed the small Fifth Ave sign (Cosmos "RIDE", Qwen "FAR CORP."). Cosmos
looped on the busy parking sign; Qwen read it. Qwen got the small-print date.

**Choice.** Qwen3-VL-4B for "read that" requests, Cosmos for video. Small street
text needs a zoom crop before either model.

## D6. Baseline walk scores against hand labels

`scripts/score_walk.py` against `test_videos/labels/*.json` (44 events, 29
must_warn, single annotator, labels written after seeing the transcripts, so not
blind). Match rule: spoken utterance starting in [t_start, t_close + 1 s] that
names the event class. Lenient (one utterance can hit overlapping events), so
rates may be slightly high. Full table: `results/walk_scores.md`.

| Mode | must_warn hits | All hits | Lead median (s) | Side correct | False alarms |
|---|---|---|---|---|---|
| describe | 10/29 (34%) | 14/44 (32%) | -0.3 | 7/14 (50%) | 33 |
| instruct | 11/29 (38%) | 17/44 (39%) | +0.1 | 10/17 (59%) | 27 |
| describe_mem2 | 4/29 (14%) | 7/44 (16%) | -0.2 | 2/7 (29%) | 12 |

Median lead about 0 s: warnings arrive at the closest moment, not before it.
The target for the fused version is must_warn hits up and lead time above +2 s.

Correction to the D3 note on the 4K clip: the labeller found the vehicle at 0 to
3.5 s is the black pickup, and the "black car" near 15 s is the white utility
truck looking dark at low resolution (`3874684_720p.json`, e1 note).

**Bug found in the first run.** Querying as fast as the model returned (about
every 1.5 s) queued speech behind speech; lag grew to 72 s by the end of the
clip. Fix: look again only after the current sentence finishes.
