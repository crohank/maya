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

## D7. Fused harness: perception fast path + Cosmos facts

`scripts/fused_harness.py`. Fast path: tracks from `scripts/perception.py`
(D-FINE obj365 + Depth Anything V2 metric small + IoU tracker, about 50 ms per
frame, 0.2 GiB). Warn when a track in the path is close (box bottom in the lower
12% of the frame or box height over 45%) or approaching with TTC under 3.5 s,
confirmed in 3 of 5 frames, 5 s per-track cooldown. Depth distance is not used
for triggering: it read 2 to 3x long, so nearly every track was "far". Slow
path: Cosmos gets the top 3 tracks and is asked for one thing they miss, or NONE.
The two paths are assumed to share the GPU without slowing each other (not
measured together).

| Mode | must_warn hits | All hits | Lead median (s) | Side correct | Utt/min | False alarms |
|---|---|---|---|---|---|---|
| describe (baseline) | 10/29 (34%) | 14/44 (32%) | -0.3 | 7/14 (50%) | 24.3 | 33 |
| fast path only | 13/29 (45%) | 17/44 (39%) | +0.4 | 4/17 (24%) | 26.4 | 27 |
| fused | 18/29 (62%) | 24/44 (55%) | +0.2 | 8/24 (33%) | 34.6 | 44 |

Full table: `results/walk_scores_fused.md`. Fused nearly doubles must_warn hits.
Still open: warnings land near the closest moment, not 2 s before it; side
accuracy dropped (Fifth Ave fused 0/9); it talks more (34.6 utterances per
minute) with more false alarms.

## D8. Latency review of the fused run, by eye

Frame strips (seen / speech starts / speech ends) in `results/latency_review/`.
From the logs (fast warnings): trigger frame to speech start median 0.3 to 0.4 s,
max 1.2 s; speech itself 1.3 to 1.7 s; so a warning finishes about 2 s after the
trigger frame. The voice is the bottleneck: on Fifth Ave 64 fast warnings were
dropped because the voice was busy, in London Cosmos facts held the voice and 13
fast warnings were dropped.

Hand check of 13 spoken warnings:
- Timely and right: truck on the left at 1.8 s (4K clip), crowd approaching at 16.9 s.
- Too late: car on the left at 3.5 s spoken at 4.7 s, gone by then; a woman head-on
  at 15.3 s was already past when speech started, and was called "on your right"
  while she was on the left.
- Not a hazard: "Person close ahead" for people walking away in the same direction
  (0.4 s, 9.4 s, 11.5 s). These flood the voice.
- Wrong: "Pole close ahead" at 6.4 s (4K clip, railing on the right, no pole),
  "Truck ahead, approaching" for a truck crossing left to right.
- Cosmos facts are mostly noise: "A step on my left foot", "A purple box",
  "Curb on left side of road" repeated 5 times.

Root causes: (1) the "close" trigger fires when the box reaches the bottom of the
frame, which at walking speed is about 1 s from contact, too late by design;
(2) 1.5 s spoken sentences; (3) one voice shared by too many low-value messages.

The scorer is too lenient for this use case: a hit counts if speech starts by
t_close + 1 s and names the class, so a generic "Person close ahead" in a crowd
scores, and a warning that ends after the person passed still counts.

Proposed fixes: earlier trigger from TTC only (3 to 4 s), drop people moving the
same way (receding or static), pick the most urgent track, a sub-second cue
(stereo panned tone, pitch by urgency) with words only after, Cosmos facts only on
tap or when nothing urgent, and a stricter scorer (speech must END before the
object reaches the walker, side must match, precision reported). Better test
clips: chest-height phone recordings with head-on encounters and curbs.

**Bug found in the first run.** Querying as fast as the model returned (about
every 1.5 s) queued speech behind speech; lag grew to 72 s by the end of the
clip. Fix: look again only after the current sentence finishes.

## D9. Faster warnings (fast path v2) and a strict scorer

**Strict scorer** (`scripts/score_walk.py`, second table, must_warn only). A
warning counts only if its speech ENDS by t_close, it names the class, and it
starts no earlier than min(t_start - 0.5, t_close - 3). One utterance credits
one event. Side must match the label (no side word is wrong). Warn precision =
share of spoken utterances that name some must_warn event near its time. It
still matches by class, not identity: in a crowd, "Person right." about one
person can be credited to another.

Ceiling: 9 of the 29 must_warn events are curbs, crosswalks, signs or "other",
which the detector has no class for. The fast path can reach at most 20/29.

**v2 rules** (`scripts/fused_harness.py --rules v2`, now the default):
- Warn from time-to-contact alone, under 4 s.
- Drop the v1 "close" trigger, so people walking the same way stay quiet.
- Warn when someone crosses the walking corridor close up.
- One warning per frame, the most urgent track.
- Confirm in 2 of 3 frames (v1 used 3 of 5).
- Two-word phrases ("Person left.") with Piper at length_scale 0.8. Mean speech
  is 0.77 s, down from 1.62 s.
- Side uses a narrow centre band: below 0.42 of frame width is left, above 0.58 is right.

Full table: `results/walk_scores_strict.md`. Fast-only runs, no Cosmos.

| Mode | On time | On time, side right | Spare median (s) | Warn precision | Utt/min |
|---|---|---|---|---|---|
| describe (Cosmos only) | 5/29 (17%) | 0/29 | +0.8 | 13/47 (28%) | 24.3 |
| fused v1 | 7/29 (24%) | 2/29 (7%) | +0.6 | 23/67 (34%) | 34.6 |
| fast v1 | 8/29 (28%) | 1/29 (3%) | +0.7 | 18/45 (40%) | 26.4 |
| fast v2 | 12/29 (41%) | 6/29 (21%) | +1.3 | 24/57 (42%) | 33.9 |

Against the 20 detectable events, v2 is on time for 12 and also gets the side
right for 6. Spare is the time left after the warning finishes.

What is still wrong:
- It talks too much in a crowd. Fifth Ave runs at 43 utterances per minute,
  saying "Person left/right/ahead" every 0.8 s.
- The side is wrong for head-on people who pass on the left. Three Fifth Ave
  events were called "right".
- The 4K clip's pole, bollard and curb are missed (static tracks, no growth
  signal).

`scripts/sweep_v2.py` grid (`results/sweep_v2.md`) found no setting that is
both quieter and as timely:
- A 1.5 to 2.5 s quiet gap after each warning cuts talk to 14 to 21 per minute.
- But the gap drops on-time hits from 12 to between 5 and 10, and side-right
  hits from 6 to between 1 and 5.
- A minimum box height of 0.25 gives 9/29 on time and 6/29 side right at 22.6
  per minute. This is the quieter alternative.
- TTC 5 s gives 13 to 14 on time but fewer right sides.

All thresholds were tuned and scored on the same 4 clips by the same
annotator, so these numbers are optimistic. They need new clips to confirm.
Next steps:
- Fixing the noise needs identity, not thresholds: warn once per approaching
  person, and use a stereo tone for repeats.
- Record chest-height test clips with head-on passes.

## D10. Judged items first: one engine for all five kinds (overnight 2026-11-19)

The practice pack README says judges ask random items of its five kinds live with
Wi-Fi off, so the night went to `maya/` (one engine, Qwen3-VL-4B NF4 resident) and
`scripts/eval_pack.py`. Full write-up: `docs/overnight_report.md`.

| Set | Before | After |
|---|---|---|
| Practice pack (tuning set) | 74/100 | 96/100 |
| Held-out set made tonight | | 64/68 |
| SQuAD 2.0 extra | 47/60 (plain) | 46/60 |
| VizWiz extra | | 72/80 |
| LibriSpeech extra | | 34/40 |
| ESC-50 extra | 73/100 (AST) | 84/100 (CLAP) |
| HumanEval extra sample | 36/40 | 37/40 |
| HumanEval extra, all 144 | | 125/144 |
| MBPP extra | | 25/30 |

Decisions:
- **Video:** Qwen3-VL with every sampled frame, plus measured frame facts on synthetic clips. Cosmos3-Edge scored 2 to 4 of 15 and costs about 11 s per swap, so it is out of the item path.
- **Sound ID:** CLAP zero-shot over 122 general labels beat AST on both the pack and ESC-50.
- **Documents:** quote-then-verify rules. Better refusals on the pack, a tie on the extra set, about 3 s per question.
- **Code:** run the prompt's own examples and retry. Qwen2.5-Coder-3B only as a fallback, after failed self-checks.
- **Walk mode:** v3 (panned tones, one word per person). On SANPO with identity-matched scoring it gets 24/33 on time against v2's 15/33. Holding the side back (v5) was worse.
