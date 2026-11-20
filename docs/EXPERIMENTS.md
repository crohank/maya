# Experiments: what we tried and how it went

This file lists every approach we tried for Maya, grouped by area. Each row says
what the approach was, what we measured, and the verdict:

- **kept**: in the app or in the recommended walk setting
- **dropped**: tested and turned off or removed
- **open**: partly works, or the problem is still unsolved

The numbers come from the older write-ups, which have the full detail:
[decisions.md](decisions.md) (D1 to D10),
[overnight_report.md](overnight_report.md) (the five item kinds),
[sanpo_eval.md](sanpo_eval.md) (the SANPO walk set),
[walk_overnight_2026-11-20.md](walk_overnight_2026-11-20.md) (the combined Cosmos walk sim),
and the research notes in [research/](research/). The last day's work (v12 and the
crosswalk checks) is written up only here.

Walk versions v1 to v12 are runs of
`experiments/cosmos_combined/sim_walk_combined.py`. Their logs are in
`results/live/<clip>_cc_UX<n>/` (without steering) and `results/live/<clip>_cc_BEST<n>/`
(with Cosmos steering). "Review" means an agent frame review of 22 real clips,
described under [Evaluation methods](#evaluation-methods).

## Contents

1. [Test data](#test-data)
2. [Evaluation methods](#evaluation-methods)
3. [Perception](#perception)
4. [Distance](#distance)
5. [Walk words and tones](#walk-words-and-tones)
6. [Scene cues](#scene-cues)
7. [Curb and crosswalk](#curb-and-crosswalk)
8. [Cosmos steering, describe and stairs](#cosmos-steering-describe-and-stairs)
9. [Sound alerts](#sound-alerts)
10. [Speech](#speech)
11. [Image and Q&A modes](#image-and-qa-modes)
12. [Summary](#summary)
13. [Review table across walk versions](#review-table-across-walk-versions)

## Test data

| Set | What it is | Used for |
|---|---|---|
| Practice pack | 100 items from the organisers (25 image, 20 audio, 20 document, 15 video, 20 code). Kept local, not in git. | Tuning set for the five item kinds, so its scores are optimistic |
| Held-out set | 68 items we generated (`scripts/make_heldout.py`): new synthetic videos, documents, images and code, WebM inputs | Overfitting check, not tuned on |
| Extra sets | SQuAD 2.0 (60), VizWiz (80, real photos from blind users), LibriSpeech (40), ESC-50 (100, all 50 classes), HumanEval (144), MBPP (30), built by `scripts/make_extra_data.py` | Overfitting check, not tuned on (two documented exceptions in [overnight_report.md](overnight_report.md)) |
| Internet walk clips | 4 clips: Fifth Ave sidewalk, an empty 4K sidewalk, London Canary Wharf, a promenade. Hand labels for 44 events (29 must warn) in `test_videos/labels/` | First walk scores (D6 to D9). One annotator, labels written after seeing model output |
| SANPO | 11 chest-camera clips from Google Research (CC BY 4.0), labels made by a rule from SANPO's own depth and instance masks: 33 must-warn events, all people | Walk warnings about people, with no human in the labelling loop ([sanpo_eval.md](sanpo_eval.md)) |
| Park Avenue walk | A public YouTube walk through Manhattan ([video](https://www.youtube.com/watch?v=VAjHWBkz_z8)): 18 held-out 15 s cuts (`rt_01` to `rt_18`) with timed notes by eye, plus 6 earlier cuts (`yt_*`). With the 3 stock clips, 27 real clips | All walk work from v1 to v12 |

Things to know about the walk data:
- The team's "phone recordings" (`my_walk2`, `my_walk3`, `nyc_full`) turned out to be
  screen crops of the same YouTube video, so they are not independent footage.
- 24 of the 27 real clips come from that one walk: daylight, one city, one camera.
  Nothing was tested at night, in rain, or on a phone worn by a walker.
- Tuning used 11 clips (the 8 earlier cuts and the 3 stock clips). The 18 `rt_*` cuts
  were held out for the steering comparison, then used for every review.
- Clips and videos stay out of git. The YouTube-based clips are shown in the demo
  for this non-commercial project, with credit to the original video.

## Evaluation methods

| Method | What it was | Result | Verdict |
|---|---|---|---|
| Lenient scorer (D6) | A spoken line counts if it starts between the event's first sight and its closest moment plus 1 s and names the class | A generic "Person close ahead" in a crowd scored, and so did a warning that ended after the person had passed | dropped as the main score |
| Strict scorer (D9) | Speech must end before the object arrives, one line credits one event, the side must match, precision reported | Fast path v1 8/29 on time, v2 12/29. Still matches by class word, not by which person | kept for the internet clips |
| Chance baseline | The same warnings shifted by 7 s or 13 s | On SANPO the shifted runs still scored 61 to 70% on time against 85% for the real run, so the class scorer rewards talking often | kept as a sanity check |
| Identity scorer (`scripts/score_walk_id.py`) | A warning counts only if its track matches the SANPO instance mask of the right person (box to mask IoU 0.25 or more) | Shifted runs score 0 or 1 of 33. Swapping in a random nearby person: v3 13.2 against 24 real | kept for people warnings |
| Agent frame reviews | A fresh agent per version checks every spoken line against frames 1 s before, at and 1 s after, on 22 clips, with the same rules each time, and lists missed events | The trend between versions is the signal. The reviewers are agents reading frames, not blind people | kept, with that caveat |
| Held-out timed notes | By-eye notes of what happens when in the 18 `rt_*` cuts (`data/realtest/manifest.json`, local) | Used to count approaching people who got a beep or a word | kept |
| `score_combined.py` | Mechanical checks of steering lines: did speech start before the closest point, does it point toward the object | Cheap filter before frame reviews | kept |
| Pack scorer (`scripts/eval_pack.py`) | Hand-written keys, lenient on wording and strict on facts | Same scorer for the practice pack, held-out and extra sets | kept |

The frame reviews themselves (`data/review/blind_review*/REVIEW.md`) and the review
videos are kept locally with the clips, not in git.

## Perception

| Approach | What it was | Result | Verdict |
|---|---|---|---|
| VLM only (D2, D3) | Cosmos3-Edge NF4 describing a 2 s window, looking again as soon as the last answer is spoken | 0.5 to 0.6 s per look. 10/29 must-warn events on the lenient scorer, 5/29 on the strict one. Led with an SUV in the road while people were straight ahead | dropped as the walk path |
| Text memory (D4) | The last two answers added to the prompt | The model copied itself: "Person walking away from you" for 32 of 36 looks on the London clip | dropped |
| Detector, depth and tracker (D7) | D-FINE small (Objects365), Depth Anything V2 Metric Outdoor Small, our own IoU tracker (`scripts/perception.py`) | About 50 ms per frame and 0.2 GiB. Median 41 to 89 ms per frame on SANPO with the GPU shared | kept |
| ByteTrack | Through `supervision` | supervision 0.32 removed it, so `perception.py` carries an IoU tracker | dropped |
| Fused harness (D7) | Detector warnings plus Cosmos asked for one thing the tracks miss | Lenient must-warn 18/29 against 10/29 for describe, but more talk (34.6 lines a minute) and Cosmos facts were mostly noise ("A purple box", "Curb on left side of road" 5 times) | Cosmos facts dropped |
| Corridor and edge filters | Vehicles must be on a collision course, nothing centred in the outer 12% of the frame, poles and bins only when near, 2.5 s between object words | 8 clips: 45 object and scene words down to 30. SANPO identity set unchanged at 24/33 cues on time | kept |
| More object names (v2) | Name planters, chairs, barrels, parking meters, suitcases, dogs, low signs | Only "Chair" fired, once and correctly. "Trash can" 5 of 5 right. Planters, barrels and sign boards on screen were never named | kept, little effect |
| Still obstacles (v3) | Still objects can take the word slot when the most urgent track was already named | Part of v3 (useful lines 44% to 57%) | kept |
| Riders (v5) | A person box on a bike box is named "Bike" | The rt_01 and rt_11 cyclists became "Bike". rt_03 still missed | kept |
| Detector confidence gate | Teammate's Mac sim: only triggers at confidence 0.7 or higher | Dropped a phantom pole, but also the real van close on the right | not adopted |
| Pan rate and crowd words | No "crossing" while the camera turns. "Crowd ahead." instead of person words | Neither helped clearly | dropped (opt-in, off) |
| Cosmos lane obstacles (v6) | Cosmos3-Edge on a crop of the walking lane names objects the detector has no class for, two answers in a row, fixed word list | 18 words: 7 in the path (sign boards, wheelbarrow, scissor lift, planter, trash can), 7 beside it, 4 wrong ("Cart", "Machine") | kept, changed below |
| Stricter lane words (v7) | Three matching answers in a row, no "Cart" or "Machine" | 3 words, none useful. The phantoms went, and so did all 7 real in-path warnings | dropped |
| One Cosmos call for ground and lane (v10) | One call per second on the lane crop returns both words, to fit the live GPU budget | 14 lane words: 6 useful, 8 beside the path. 0.17 to 0.25 s per call | kept |

Open: about 21 fixed obstacles are still never named in the v10 review (barrels,
some boards, bollards). Open-vocabulary detectors (OmDet-Turbo, Grounding DINO) were
researched in [research/01_perception_stack.md](research/01_perception_stack.md) but
not built.

## Distance

| Approach | What it was | Result | Verdict |
|---|---|---|---|
| Depth for triggering (D7) | Depth Anything V2 metric distance to decide "near" | Read 2 to 3 times too long, so nearly every track was "far" | dropped for triggering |
| "Close" from box size (D7) | Warn when the box bottom reaches the lower 12% of the frame or the box is over 45% tall | Fires about 1 s before contact, too late by design | dropped |
| Time to contact (D9) | Warn when time to contact is under 4 s, the most urgent track per frame | Strict score 8/29 to 12/29 on time on the internet clips | kept |
| Steps from class height (v2) | Pinhole estimate from a typical height per class, one step = 0.75 m | Roughly right (within 1.5 times): 34 of 46 (v2), 39 of 48 (v3), 40 of 49 (v4). The errors overstate up close: "9" at 2 m, "6" at 1.5 m | kept |
| Cap when feet are cut off (v3) | At most 2 steps when the box touches the bottom edge | Part of v3 | kept |
| "Close" for near objects (v4) | Boxes cut at the bottom or taller than a threshold say "close" | 18 of 20 "close" lines were within 3 m | kept |
| Short numbers (v4) | "Person left, 5." instead of "5 steps" | Step words make each line about 1 s longer. SANPO words on time: 10 of 33 with no distance, 6 with "3 steps", 8 with "3." | kept |
| Depth for poles (v12) | Poles and boxes cut at the top use the track's depth distance | Part of v12 | kept |
| Far objects get tones only (v12) | Tracks over 9 steps away get a beep, no word | Part of v12 | kept |
| Ground fit on feet (v12) | Per-clip fit of where people's feet sit in the frame against their distance, to put a number on the crosswalk word | Over 25 clips the frame bottom sits 2.4 to 5.1 m ahead (median 3.3 m) | kept, an upper bound |

v12 result on the 27 clips: walk words without a number went from 8 to 0, and spoken
lines from 151 to 130. Cosmos lane words take their number from a matching detector
box, but only 6 of the 20 lane words got one. The other 14 (sign boards, barriers,
poles, the lift) had no matching box. v12 has not had a full frame review.

## Walk words and tones

| Approach | What it was | Result | Verdict |
|---|---|---|---|
| Short phrases (D9) | Two-word phrases ("Person left.") with Piper at length scale 0.8 | Mean speech 0.77 s, down from 1.62 s | kept |
| Quiet gap (D9 sweep) | 1.5 to 2.5 s of silence after each warning | Talk fell to 14 to 21 lines a minute, but on-time hits fell from 12 to 5 to 10 | dropped |
| Minimum box height 0.25 (D9 sweep) | Ignore small boxes | 9/29 on time at 22.6 lines a minute, a quieter alternative | not adopted |
| Panned tones, one word per person (v3 rules) | A stereo beep panned to the object's side for repeats, one spoken word per person | SANPO identity scorer: 24/33 on time against 15/33 for v2, 17 words a minute | kept |
| Tones by pulse count | Low is one 440 Hz pulse, mid two 880 Hz pulses, high three 1760 Hz pulses, instead of three pitches | The three old pitches were hard to tell apart. Not tested with listeners | kept |
| Hold the side (v5 rules) | Centred tone until the track commits to a side | Side right at the first side cue 7/33 against 11/33 for v3 | dropped |
| Side from position | Side taken from where the object is now | 2 to 3 s out, which side someone passes on is close to a coin flip. v3 side right 11 to 15 of 33 on SANPO | open |
| Words for head-on people (v11) | A track within 0.5 m of the centre line gets a word even if a person was named in the last 8 s | Approaching people with a word: 30 to 34 of 45. 12 new lines, 8 checked: 6 useful, 2 noise, none wrong | kept |
| A number on every word (v12) | Every word ends in a step count or "close" | Words without a number 8 to 0, lines 151 to 130 | kept |

Beeps were not judged in the frame reviews. Across the held-out notes, 38 of 45
people approaching the walker got a beep or a word within 2 s before to 1 s after.

## Scene cues

| Approach | What it was | Result | Verdict |
|---|---|---|---|
| Qwen3-VL yes/no questions (`scripts/walk_scene.py`) | Three yes/no questions per frame at 2 fps, 0.46 s median | On one 3:14 recording: 3/3 corners announced 0.5 to 3.5 s before the edge, no corner cue on 2 minutes of sidewalk, 7 of 9 traffic cues right. Tuned on the same video | kept on `main` (opt-in). Not in the Cosmos stack |
| Crossing stages | A question on the bottom 28% of the frame (street or sidewalk) for "In the crosswalk.", "On the sidewalk.", "Curb ahead, step up." | "In the crosswalk." came 1.4 s and 2 s after stepping off. "Step up" fired at the wrong time twice. The v1 review counted 12 wrong location lines, the worst being "On the sidewalk." mid-crossing | dropped (off from v2) |
| Cosmos ground check to mute the curb word (v3) | Skip the curb word when Cosmos said the walker is in the street | Left 1 curb word in 22 clips, and missed curbs rose to 15 | dropped |
| Three street checks in a row (v7) | A softer version of the same | Removed nothing | dropped |
| Cosmos "where are you standing?" | Multiple choice: at the edge with a crosswalk ahead, already in the street, or on a sidewalk with none | Mostly wrong on frame-checked corners | dropped |
| "Cars passing." | From perception tracks, since Qwen3-VL almost never said traffic | Said in 15 of 22 clips in v2 and v3, often noise or wrong mid-crossing | kept with limits below |
| "Cars passing." limits (v3, v5) | At most every 20 s, and only within 10 s after a curb word | 15 to 9 lines (3 useful, 5 noise, 1 wrong in v6). Still said mid-crossing in rt_13 and with no traffic in yt_siren1 | open |

## Curb and crosswalk

| Approach | What it was | Result | Verdict |
|---|---|---|---|
| Cosmos curb approach (`cosmos_edge_test.py`) | Single yes/no prompts asking whether a curb or crosswalk is a few steps ahead | Missed the approach on all 4 labelled corners | dropped |
| Stripe detector (`stripes.py`) | Pixels only: bright, low-saturation horizontal bands in the lower half of the frame | Fires within about 2 s of the curb at 9 of 11 held-out corners, silent on 6 sidewalk-only clips | kept |
| Early warning | | Stripes are detected only once they touch the frame bottom, about 3 m (4 steps) ahead. No early warning yet | open |
| Centre columns only | Search only the middle of the frame | 6 more false alarms | dropped |
| One curb word per 20 s (v8) | The gap was 8 s, and a crossing takes 10 to 15 s | Mid-crossing curb words 3 to 1, well-timed ones 4 and 4 | kept |
| "Curb ahead, step down." (v11 trial) | That wording, with a street check | Well-timed curb words 4 to 1 | dropped |
| Frame check of curb words | 15 curb words checked against frames | 10 right, 5 false: 2 mid-crossing, 1 a side crosswalk, 1 a bike-lane marking, 1 plain paving | |
| Cosmos confirm (`curb_confirm_probe.py`, v12) | On stripe frames, ask Cosmos "Is a painted crosswalk directly in front of the camera, with the camera still on the sidewalk?" | Removed the plain-paving false alarm. Never said no on a frame-checked good corner. 4 false alarms remain | kept |
| Step count on the crosswalk word (v12) | Steps from the ground fit at the stripe row | "Curb and crosswalk ahead, 4." The number is an upper bound | kept |

Open: the curb word never says step up or step down, it still fires mid-crossing in
some clips (rt_03, rt_14 in the v10 review), and the 4K clip's curb came 4.5 s late.

## Cosmos steering, describe and stairs

Rule from the start: Maya describes, it never decides. These tests checked whether
steering could earn an exception. It could not.

| Approach | What it was | Result | Verdict |
|---|---|---|---|
| Guide mode (D2) | Cosmos describes free space | "Open space on your right" while the right was building walls, "open space on your left" for the road | dropped |
| Instruct mode (D3) | Cosmos says "move left" or "move right" | "Move right" 65 of 85 looks, flipped 13 times between looks 0.6 s apart. Of 6 hand-checked lines, 4 wrong or dangerous. Same right-side bias on all 4 clips | dropped |
| Teammate's Mac sim | BF16 Cosmos3-Edge on Apple Silicon, MOVE on walk v3 triggers, describe otherwise, London clip only | 4 moves: 3 in the right direction, 1 acceptable, all late at 3.2 to 3.3 s per call. One grader, one 20 s clip | research only |
| Teammate prompts, held out (v0) | The Mac prompts on 4-bit Cosmos on CUDA, 18 held-out clips | 71 MOVE lines: 13 on time, 4 toward the object, "1 step right" 41 times | dropped |
| Gated MOVE | Only for tracks on a collision course, choose from moves that do not head toward the object | 17 lines: 10 on time, none toward the object | tested further |
| Gated MOVE, frame reviews (v3, v4) | The same, judged on frames | 1 of 15 lines useful, 6 wrong, 8 late. "Slow down." came after the vehicle had passed 5 of 6 times. Three lines would step the walker into someone beside them | dropped (kept behind a flag for the `with_steering` videos) |
| Short DESCRIBE (v1) | Cosmos names up to two nearby things with side and steps | 2 of 25 useful. Almost always "2 steps", whatever the distance (an SUV 10 m away). Talks 3 to 4.6 s while hazards arrive | dropped |
| Stairs check | Cosmos one-word check: up, down or no | 0 of 7 alerts right. "Going up" for subway stairs going down. The rt_18 staircase was never announced in any version | dropped |
| Cosmos for video items | Cosmos3-Edge on the practice-pack videos | 2 to 4 of 15, plus about 11 s per model swap | dropped |
| Cosmos for images (D5) | Sign and label reading | 5/10 against 6/10 for Qwen3-VL-4B | dropped |
| BF16 Cosmos3-Edge (D1) | The model card's path | Does not fit the 6 GB left on the 8 GB card. The NF4 build runs at 2.2 to 2.4 GiB | NF4 kept |
| Live GPU budget | Tracking at 8 fps (0.42 s per second of video), street check 0.25 s and lane check 0.3 s | Does not keep up live. Checking the lane every 2 s lost real warnings. One combined call: about 0.6 s per second | combined call kept |

## Sound alerts

| Approach | What it was | Result | Verdict |
|---|---|---|---|
| AST sound ID | `MIT/ast-finetuned-audioset-10-10-0.4593` | ESC-50 73 to 74/100 | replaced for items |
| CLAP zero-shot | `laion/clap-htsat-unfused` over 122 everyday and street sounds | ESC-50 84/100 (all 50 classes, 40 never in the pack) | kept for items |
| Horns | Both models on horns | CLAP called a horn a doorbell and once "traffic noise". AST scored a real horn 0.69, and no ESC-50 clip scored above 0.31 for horn. A clear AST horn (0.4) or siren (0.5) is now always named | kept |
| Walk alerts (`maya/sound.py` `alert_timeline`) | AST on 2 s windows with a 1 s hop, words "Siren.", "Car horn." | On 6 YouTube street clips both sirens and the horn were named within about 0.1 s of the window, nothing fired on the other clips | kept |
| AST on CPU for walk | | 2.3 to 3.4 s per window on a loaded CPU, so the word would land after the event. Runs on the GPU when there is one | GPU kept |
| Reversing beeps | "Truck backing up." from reversing beeps | Fires on yt_reversing and on no other clip in v10 to v12. Not scored on its own | kept |
| Crosswalk signal ticks | A tick-rate rule on onsets above 500 Hz | Part of sound ID. Not measured on a real signal | open |
| Crowd babble | When AST hears speech but Whisper is empty or unsure (log prob under -0.8), say so | Stops a looping transcript or "no speech" flip-flop | kept |

## Speech

| Approach | What it was | Result | Verdict |
|---|---|---|---|
| Route by sound content | Decide speech or sound from the audio itself, not the wording of the question | With AST and small.en: practice-pack audio 8/20 to 18/20 | kept |
| faster-whisper small.en | CPU, int8 | LibriSpeech transcribe 16/20. With questions answered from the transcript, LibriSpeech extra 34/40 | kept |
| Piper TTS | `en_US-lessac-medium`, CPU | About 0.1 s per sentence | kept |
| One voice, priority queue | Alerts first, then walk words, then descriptions. A newer warning replaces a stale one | Before this, 64 fast warnings were dropped on Fifth Ave because the voice was busy (D8), and an early harness let speech lag 72 s behind the video | kept |
| Safety and advice filters | Every answer is checked for instructions ("safe to cross", "path is clear") and advice clauses are cut | "Keep straight, path ahead is clear of people" passed the first filter, so the pattern was widened (D3). Tested in `tests/test_safety.py` | kept |

## Image and Q&A modes

The judged part of the hackathon: random items of five kinds, asked live with Wi-Fi off.

| Approach | What it was | Result | Verdict |
|---|---|---|---|
| Qwen3-VL-4B NF4, Conv3d fix (D5) | The vision patch embed was a Conv3d that took 14 to 17 s on this GPU. Replaced by one matmul over the same weights | 39.3 s to 1.98 s median per image, same answers (max difference 0.008) | kept |
| One engine for all kinds (D10) | `maya/` keeps Qwen3-VL-4B on the GPU and routes image, audio, document, video and code | Practice pack 74/100 to 97/100 | kept |
| Video frame timestamps | The processor resampled our frames as 24 fps footage, so the model saw about 4 frames | Practice video 8/15 to 15/15, held-out 13/24 to 22/24 | kept |
| Measured frame facts | On synthetic-looking clips only: counts over time, colors in order, direction, bounces, size trend | Part of the video fix | kept |
| Count recount from boxes | Answer plainly first, recount from Qwen3-VL boxes when the count is 4 or more | Practice images 23/25 to 24/25, held-out 11/12 to 12/12, VizWiz 72/80 unchanged. Threshold picked from the misses on these sets, so optimistic | kept |
| Quote then verify (documents) | The model quotes a sentence and answers. Code checks the quote is really there and holds the question's numbers and names. Otherwise "The document does not say." | Practice text 17/20 to 19/20. SQuAD extra 46/60 against 47/60 for a plain prompt. About 3 s per question against 0.6 s | kept |
| Relation-flip check | Code-only check for a question that flips a stated relation (rise or drop, first or last, a negation) | SQuAD half A unanswerable 2/8 to 4/8, half B (held out) 4/7 unchanged, no false refusals | kept |
| Model-based verifiers | A second model call to judge answerability | Caught some traps, but always refused a real question too | dropped |
| Self-checked code | Run the prompt's own examples in a sandbox, up to 2 retries | Practice code 18/20 to 20/20. HumanEval sample 36/40 to 37/40, all 144: 125. MBPP 25/30 | kept |
| Coder fallback | Qwen2.5-Coder only after failed self-checks | 3B is under a non-commercial license, so 7B NF4 (Apache-2.0) replaced it at the same scores. Alone: 7B 19/20, 3B 18/20, 1.5B 13/20 | 7B kept |
| Input hardening | A review found 16 input bugs: one-frame and rotated videos, transparent PNGs, scanned PDFs, sandbox escapes, very short audio, HEIC | All fixed, scores unchanged, 117 tests at the time | kept |
| Phone app | FastAPI over HTTPS, one page, spoken questions | 16 of 16 end-to-end requests returned 200. Warm photo 0.35 s, video 1.3 to 1.6 s, document 2.6 to 4.2 s | kept |

Final scores: practice pack 97/100, held-out 64/68, SQuAD extra 46/60, VizWiz 72/80,
LibriSpeech 34/40, ESC-50 84/100, HumanEval 125/144, MBPP 25/30.

Open: unanswerable questions that swap a role (who presented to whom) still get
answered, about 8 of 15 on the SQuAD extra set. The code sandbox is not a hard boundary
against writes through the Windows file mount.

## Summary

### What worked

- A fast layer first. Detector, depth and tracker at about 50 ms a frame decide
  when to warn. The VLM only adds names and checks the detector cannot do.
- Time to contact instead of box size. Warnings moved from about 1 s before contact to
  usable lead time (strict 8/29 to 12/29).
- Panned beeps with one word per person: 24/33 on time on SANPO against 15/33 for words.
- Fewer, shorter words. Useful lines went from 34% (v1) to 51 to 59% (v4 to v10) while
  wrong lines fell from 38 to 8.
- A pixel stripe detector for crosswalks where the VLM saw nothing (9 of 11 corners).
- A Cosmos yes/no confirm on top of the stripes, and Cosmos on a crop of the walking
  lane for objects the detector has no class for.
- For the judged items: fixing the Conv3d slowdown and the frame-rate bug, quote-then-verify
  documents, self-checked code, CLAP for sounds.

### What didn't

- Any VLM steering: 1 of 15 useful lines, 6 wrong, 8 late, and a right-side bias.
- VLM descriptions during a walk (2 of 25 useful) and VLM stairs checks (0 of 7).
- Text memory of earlier answers.
- VLM questions about where the walker stands (street, sidewalk, mid-crossing).
- Depth Anything distance for triggering (2 to 3 times too long).
- Quiet gaps and stricter confirmation rules: each cut wrong lines but lost real warnings.

### Open problems

- Curbs: no early warning (stripes show up about 3 m out), no step up or down, and
  false alarms mid-crossing and on bike lanes.
- Fixed obstacles without a detector class: about 21 never named.
- About 15 people walking straight at the walker get no word (beeps not judged).
- Distances under 2 m still read long sometimes ("9" at 2 m).
- Side of passing is close to a coin flip 2 to 3 s out.
- Everything is a simulation on recorded daylight video from one city, reviewed by
  agents. No blind or low-vision person has tried it yet.

## Review table across walk versions

Agent frame reviews of the same 22 real clips. Spoken words only, beeps not judged.

| | v1 | v2 | v3 | v4 | v6 | v7 | v10 |
|---|---|---|---|---|---|---|---|
| Lines | 164 | 117 | 93 | 107 | 119 | 108 | 114 |
| Correct and useful | 56 (34%) | 51 (44%) | 53 (57%) | 63 (59%) | 66 (55%) | 57 (53%) | 58 (51%) |
| Correct but noise | 59 | 36 | 26 | 29 | 30 | 33 | 44 |
| Wrong | 38 | 21 | 11 | 10 | 18 | 13 | 8 |
| Late | 11 | 9 | 3 | 5 | 5 | 5 | 4 |
| Missed events | 47 | 38 | 55 | 47 | 41 | 45 | 42 |
| missed obstacles | 25 | 20 | 24 | 24 | 20 | 24 | 21 |
| missed curbs | 11 | 4 | 15 | 4 | 4 | 4 | 4 |
| missed head-on people | 7 | 10 | 12 | 15 | 15 | 15 | 15 |
| missed cyclists | 3 | 3 | 3 | 3 | 1 | 1 | 1 |
| missed stairs | 1 | 1 | 1 | 1 | 1 | 1 | 1 |

- v1: the combined build as first made (Cosmos MOVE, DESCRIBE and location words).
- v2: DESCRIBE and stage words off, distances in steps, more classes named.
- v3: still obstacles get words. The Cosmos street check muted the curb word too often.
- v4: "close" for near objects, short numbers.
- v5: riders named "Bike", "Cars passing." only near a curb (not reviewed on its own).
- v6: Cosmos lane obstacles.
- v7: stricter lane words. Lost the real warnings with the phantoms.
- v8: one curb word per 20 s (not reviewed on its own).
- v10: one Cosmos call per second for ground and lane, the only version that fits the
  live GPU budget. Its reviewer judged noise more strictly. By the v7 bar it would be
  about 63 useful and 38 noise.
- v11: v10 plus words for head-on people (12 new lines, 8 checked, 6 useful). The
  recommended setting in `experiments/cosmos_combined/run_recommended.sh`.
- v12: a number on every word and the Cosmos crosswalk confirm (lines 151 to 130).
  Not reviewed in full.
