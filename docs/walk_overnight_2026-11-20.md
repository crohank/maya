# Walk mode overnight, 2026-11-20 00:15 to 07:00

Goal: combine the teammate's Cosmos walk simulation (branch `cosmos-mac-walk-sim`:
Cosmos MOVE and DESCRIBE lines, boxes in the video) with Maya's walk audio (beeps,
words, alerts), test it on real footage only, and judge it as a blind walker would.

## Branches (local only, nothing pushed)

- `walk-cosmos-combined`: the combination. `experiments/cosmos_combined/sim_walk_combined.py`
  runs the teammate's loop on 4-bit Cosmos3-Edge (the BF16 model does not fit the 6 GB free),
  with Maya's beeps, walk words, alerts and boxes in one Piper voice.
- `walk-blind-ux` (branched from it): six rounds of changes, each reviewed against frames.
  The combined branch was fast-forwarded to it, so both hold the same code; they differ in
  the recommended settings.

## Test data (real only)

- 18 new 15 s cuts of the YouTube Park Avenue walk with timed by-eye notes
  (`data/realtest/manifest.json`), plus 6 earlier cuts and 3 stock walk clips: 27 clips.
- The team's "phone recordings" (`my_walk2`, `my_walk3`, `nyc_full`) are portrait crops of
  the same YouTube video, so they are not independent footage.
- Tuning used 11 clips (the 8 earlier ones and 3 stock clips); the 18 new cuts were held out
  for the Cosmos MOVE comparison.

## Cosmos MOVE (steering), held-out 18 clips

| Version | MOVE spoken | On time | Toward the object |
|---|---|---|---|
| Teammate prompts | 71 | 13 | 4 ("1 step right" 41 times) |
| Gated to collision courses, step or keep straight | 17 | 10 | 0 |

Frame reviews of the gated version on 22 clips, twice: 1 of 15 MOVE lines useful, 6 wrong,
8 late. "Slow down." came after the vehicle had passed in 5 of 6 cases; three lines would step
the walker into someone standing beside them. Cosmos picks whichever cautious option it is
offered ("slow down", "stop", "keep straight") rather than judging free space.

## What a blind walker hears, frame reviews of the same 22 clips

Each version was reviewed by a fresh agent that checked every spoken line against frames
1 s before, at and 1 s after, using the same rules each time.

| | v1 | v2 | v3 | v4 | v6 | v7 |
|---|---|---|---|---|---|---|
| Lines | 164 | 117 | 93 | 107 | 119 | 108 |
| Correct and useful | 56 (34%) | 51 (44%) | 53 (57%) | 63 (59%) | 66 (55%) | 57 (53%) |
| Correct but noise | 59 | 36 | 26 | 29 | 30 | 33 |
| Wrong | 38 | 21 | 11 | 10 | 18 | 13 |
| Late | 11 | 9 | 3 | 5 | 5 | 5 |
| Missed events | 47 | 38 | 55 | 47 | 41 | 45 |

- v1: the combined version as first built (Cosmos MOVE and DESCRIBE, Cosmos street/sidewalk
  words). DESCRIBE was useful 2 times in 25 and almost always said "2 steps".
- v2: DESCRIBE and stage words off, distances in steps, more obstacle classes named.
- v3: still obstacles get words; the curb word was suppressed too often (missed rose).
- v4: "close" for near objects, short numbers ("Person left, 5."); distances 40 of 49 about right.
- v6: obstacle words from Cosmos looking only at the walking lane (7 of 18 in the path, 7
  beside it, 4 wrong); cyclists named "Bike";
  "Cars passing." only at the curb.
- v7: stricter lane words (3 checks in a row); lost the real in-path warnings along with the
  phantom ones, so the reviewer picked v6.

The reviewers judged spoken words only, not beeps. Of 45 "person approaching" moments in
the held-out notes, 38 got a beep or a word within 2 s before to 1 s after.

## Recommended setting

v8 without MOVE: v6 plus at most one curb word per 20 s, which removed 2 of 3 mid-crossing
curb words and kept the 4 well-timed ones (not reviewed separately). Videos in
`data/review/FINAL_walk/recommended/`, settings in
`experiments/cosmos_combined/run_recommended.sh`). v4 is the more cautious choice: fewer
wrong lines (10 against 18) but more missed obstacles. With MOVE kept, as asked, it is
`data/review/FINAL_walk/with_steering/`; the reviews say a blind user is worse off with it.

## Other findings

- Cosmos-only curb approach: Cosmos missed it on all 4 labelled corners; a pixel stripe
  detector (`stripes.py`) fires within about 2 s of the curb at 9 of 11 held-out corners and
  stays silent on 6 sidewalk-only clips.
- Cosmos stairs check: 0 of 7 alerts right; off.
- Step distances lengthen each word by about 1 s: on SANPO, words on time fell from 10 to 6
  of 33 with "3 steps" and to 8 with the short "3."; beeps on time stayed 24 to 25 of 33.

## Process

- GPU max 71 C, never paused. Disk 68 GB free.
- Downloads: yt-dlp from PyPI and 208 MB of sections of the one YouTube video the user gave.
- I ran `python3` on the Windows host once by mistake at about 00:35 (a compile check); it may
  have opened the Microsoft Store page.

## Live GPU budget (measured, not yet wired in)

The simulation times each model call separately. On one laptop GPU, per second of walking:
tracking at 8 fps about 0.42 s, the Cosmos street check 0.25 s and the lane check 0.3 s, which
does not keep up live. Checking the lane every 2 s instead lost real warnings (rt_06 sign board
at 10 s instead of 1 s, nothing in rt_17). One Cosmos call on the lane crop that returns both
words ("sidewalk sign") took 0.17 to 0.25 s and named the same obstacles on 10 clips (barriers
and sign boards in rt_06, the wheelbarrow in rt_07, the lift in rt_09, planter, sign board and
trash can in rt_17), so the budget becomes about 0.6 s per second. Its ground word is less
clean ("crosswalk" instead of street or sidewalk). Script: `cosmos_lane_ground_test.py`.

## Caveats

- The reviewers are agents reading frames, not blind people, and every review used the same
  method; treat the trend between versions as the signal, not the absolute percentages.
- 24 of the 27 clips come from one YouTube walk in Manhattan (daylight, one camera). Nothing
  here was tested at night, in rain or on a real phone in a pocket.
- Everything is a simulation on recorded video with measured model times; the app's live walk
  mode is unchanged on `main`.
- Step counts assume a field of view per orientation; 40 of 49 were about right in review.
