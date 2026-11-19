# Walk mode on SANPO clips

A second walk test set, from SANPO (Google Research), with labels made by a
rule from SANPO's own depth and panoptic masks instead of by hand. It exists
because the four internet clips in `test_videos/` were labelled by one person,
after seeing model output, and filmed at the wrong height.

## Data

- Source: SANPO-Real, `gs://gresearch/sanpo_dataset/v0/sanpo-real/`, read over
  plain HTTPS from the public bucket (no account). License CC BY 4.0
  (README of `github.com/google-research-datasets/sanpo_dataset`). Faces and
  plates are blurred by the publisher. Cite Waghmare et al., WACV 2025.
- Bucket layout per session: `description.json` (traffic levels, cameras),
  `camera_chest/` and `camera_head/`, each with `left/` and `right/`. Under
  `camera_chest/left/`: `video_frames/NNNNNN.png` (2208x1242 PNG, 2.8 to 3.9
  MB each, 15 fps), `segmentation_masks/` (PNG, R = semantic class, G*256+B =
  instance id, 22 to 25 KB), `depth_maps/` (CREStereo depth in metres,
  float16 gz, 720x1280 after a 2-value header, about 0.63 MB), `zed_depth_maps/`
  (ZED depth, full res, not used), `frame_segmentation_annotation_type.json`
  (each frame HUMAN_ANNOTATED or MACHINE_ANNOTATED), and
  `camera_chest/fixed_camera_poses.csv` (one pose per frame).
- 701 session prefixes. `scripts/sanpo_fetch.py index` read every
  `description.json` and listing. Candidates: real, walking, chest left has
  frames, masks and depth. Ranked by 2 x human traffic + vehicle traffic.
- `masks --top 24` pulled all masks of the top 24 sessions and scored each
  frame by the largest pedestrian, rider or vehicle instance in the middle
  half of the frame. `clips` took the best 30 s window per session and kept
  the top 11 sessions.
- On disk (`data/sanpo/`, gitignored): 563 MB. 11 MP4s 215 MB, depth at
  320x180 plus masks per clip 212 MB, full-session masks of the 11 sessions
  130 MB, index 6 MB. Downloaded in total about 10.6 GB (8.6 GB of PNG frames,
  deleted after encoding, about 1.7 GB depth, 0.3 GB masks).
- Clips: `data/sanpo/clips/sanpo_<first 8 chars of session id>_<start frame>.mp4`,
  1280x720. The first clip (RqOwmltc) is 15 fps; the other 10 keep every
  second frame (7.5 fps) to halve the download. Perception samples at 8 fps,
  so it sees every frame of the 7.5 fps clips and about every second frame of
  the 15 fps one.

| Clip | Traffic (people, vehicles) | Setting | Human-annotated mask frames |
|---|---|---|---|
| sanpo_RqOwmltc_0000 | heavy, low | Manhattan sidewalk, crowd head-on, walker behind a companion with a stroller | 75 of 450 |
| sanpo_UGNwBEZM_0353 | heavy, low | High Line path, people passing on the left | 0 of 225 |
| sanpo_cBVSUvSN_0000 | heavy, low | Union Square market, dense crowd | 75 of 225 |
| sanpo_7X41_wkj_0000 | heavy, low | plaza sidewalk, people head-on | 75 of 225 |
| sanpo_eHxtA669_0000 | heavy, low | Central Park path | 74 of 220 |
| sanpo_qttyxdua_0000 | heavy, low | urban | 75 of 225 |
| sanpo_8WF0e5NO_0195 | moderate, moderate | covered walkway, overexposed | 0 of 225 |
| sanpo_qFDP9gJD_0000 | moderate, heavy | road junction | 75 of 225 |
| sanpo_qn1eNtR0_0029 | moderate, heavy | sidewalk under scaffolding, parked cars | 0 of 225 |
| sanpo_wXwTZnJH_0007 | moderate, heavy | sidewalk beside parked cars | 0 of 225 |
| sanpo_x5OCPnbr_0078 | moderate, heavy | crosswalk at a junction, van passing | 75 of 225 |

Traffic levels are SANPO's session tags, not counted by me.

## Event rule (`scripts/sanpo_events.py`)

For each instance of SANPO class pedestrian, rider or vehicle (instance ids
are consistent through a session):

1. Per frame, resample the mask to the 320x180 depth grid. Distance Z =
   median CREStereo depth over the mask eroded by one pixel (mask borders mix
   in the occluder or the background). Lateral offset X = median over the same
   pixels of (u - cx) / fx * Z, from the session's chest-camera intrinsics.
   Median filter over 3 frames.
2. Drop frames where the visible mask height in metres does not fit the
   depth (under 0.4 m, or under half the frame's vertical extent at that
   depth for objects cut by the frame edge, or over 4 m).
3. Corridor: |X| <= 1.0 m (centre to centre; leaves about 0.4 m between
   shoulders). t_close = the frame of minimum Z among corridor frames.
4. Closing: Z fell by at least 1.0 m over the 3 s before t_close, and the
   instance was seen for at least 0.6 s before it. Someone walking ahead at
   the walker's pace does not close.
5. must_warn: Z at t_close under 3 m, in the corridor, closing. Vehicles
   also need their own speed over 1.5 m/s: closing rate minus walker speed
   (from SANPO camera poses) combined with lateral rate. Parked cars beside
   the sidewalk close at walking speed and would otherwise all qualify.
6. must_warn events of the same class and side whose t_close fall within
   1 s of each other are merged into one event, earliest t_start and t_close
   (the scorer credits one utterance per event; a group passing together is
   one warning, as the hand labels treat crowds).
7. Kept as must_warn false, for the lenient table: closing with Z 3 to 5 m in
   the corridor, closing within 2 m just outside it, under 3 m but not
   closing, and "parked" vehicles.
8. t_start = first frame the instance is within 10 m, but no earlier than
   t_close - 2.5 s. Without the cap a person in view for 20 s let any early
   "Person ahead" count (first run: 31/33 on time, one credited 20 s early).
   Hand-labelled must_warn events have a median t_close - t_start of 1.5 s, so
   with 2.5 s the strict scorer opens at t_close - 3 s on both sets. side = mask centroid
   at t_close in frame thirds (as `test_videos/labels/README.md`).
   dist_bucket from Z; motion from the last 1 s of Z and X.

Labels: `data/sanpo/labels/<stem>.json` (same schema as `test_videos/labels`,
with `keywords`: riders accept "person", vehicles accept truck, bus, van,
pickup, motorbike). Per-instance series: `<stem>_tracks.json`. Contact
sheets of every must_warn event at t_close with the instance outlined:
`results/sanpo/check/<stem>_must_warn.jpg`.

### What I checked by eye

All 33 must_warn events on the contact sheets. Most are a person passing
within arm's length at the frame edge, or walking head-on into the walker's
path. The companion pushing a stroller just ahead in RqOwmltc is never an
event (she does not close). Before the vehicle speed check there were 4
vehicle must_warn events: 2 parked cars, 1 bicycle locked to a rack (SANPO's
vehicle class includes bicycles) and the van at the x5OCPnbr crosswalk. The
check removes all 4; the van is the one it gets wrong (see Limits). In the
first version (30th-percentile depth, no erosion, size or history checks)
RqOwmltc also had 3 vehicle must_warn events, two of them cars far down the
street read at 2.3 and 2.6 m; steps 1, 2 and 4 removed them. I did not check
which step removed which.

### Limits

- No vehicle events. All 33 must_warn events are people. On these sidewalks
  no moving vehicle came within 3 m in the corridor. The only close moving
  vehicle, the van at the x5OCPnbr crosswalk (Z 3.0 m, own speed estimate 1.3
  m/s), falls just outside both thresholds. Vehicle warnings are not tested here.
- t_close is the nearest point as seen by the camera. For people passing to
  the side, that is often the frame where they are half out of view at the
  edge, so "nearest" is close to "alongside". The real nearest point can come
  a few tenths of a second later, out of frame. This makes the strict scorer
  slightly harder (speech must end by t_close).
- Heading is taken as the camera's optical axis. The chest camera sways and
  points 5 to 14 degrees down; when the walker turns, the corridor turns with
  the chest, not with the path.
- Most mask frames are machine-annotated (propagated by SANPO). Human-annotated
  frames are every 6th source frame in 7 of 11 clips, none in the 4 clips
  whose start frame is odd at 7.5 fps. Wrong masks become wrong events; the
  size check removes some.
- CREStereo depth is itself a model output (stereo), not lidar.
- Thresholds (1.0 m corridor, 3 m, 1.0 m closing, 1.5 m/s) are mine, set
  after looking at the first two clips' sheets, not tuned on model scores.
- Crowd merging is by class and side only; two different people passing on
  the right within 1 s become one event.
- The scorer still matches by class word, not identity.

## Camera: SANPO chest rig vs a phone at chest height

- Which camera is on the chest: `description.json` lists two cameras (ZED 2i
  and ZED M) and two locations without saying which is which. I take the
  list order. Check on one session (-5OCPnbr, frame 100): ORB matches between
  chest left and right times ZED depth gave disparity x Z = 241 px m; ZED 2i
  fx x baseline is 237, ZED M is 86. So the chest camera is the ZED 2i there.
- Lens: ZED 2i stereo in all 11 sessions, rectified left image hfov 58.3 to
  58.4 degrees, 2208x1242 (16:9 landscape). A phone main camera in landscape
  is wider (about 65 to 75 degrees); held in portrait it is narrower across
  (about 50 degrees) and taller. With 58 degrees, a person at 1 m fills the
  frame edge at 0.55 m lateral, so people passing close leave the frame
  earlier than they would on a wide phone.
- Height and tilt, measured: ground-plane fit to sidewalk and road pixels
  of the CREStereo depth (12 frames per clip, `results/sanpo/check/camheight.py`):
  camera 1.15 to 1.31 m above ground, pitched 5 to 14 degrees down. A phone
  in a chest lanyard or shirt pocket sits around 1.2 to 1.4 m, so the height
  matches. The internet clips were filmed lower (London) or from a hand/head.
- Mounting: rigid chest harness, so less shake than a hand-held phone but
  body sway turns the view at each step. A phone in a pocket or lanyard
  tilts more and swings.
- Exposure: industrial camera, some clips are strongly overexposed (8WF0e5NO)
  or flare in low sun (RqOwmltc 6 s). Phone HDR would do better.
- Frame rate 15 fps native (7.5 fps in 10 clips here); phones record 30.

## Results

Fast path only, v2 rules, no VLM, same code as D9:

```bash
bash scripts/gpu_job.sh sanpo python scripts/perception.py --video data/sanpo/clips/<stem>.mp4 \
    --out results/sanpo/perception/<stem>.jsonl --no-video
bash results/sanpo/run_walk.sh   # fused_harness.py --no-vlm --rules v2, then score_walk.py
```

Perception: median 41 to 89 ms per frame (p90 62 to 106 ms) on the shared GPU.

Strict table (`results/sanpo/walk_scores_sanpo.md`), 11 clips, 5.5 minutes,
33 must_warn events, all people:

| Clip | On time | On time, side right | Spare median (s) | Warn precision | Utt/min |
|---|---|---|---|---|---|
| sanpo_7X41_wkj_0000 | 3/4 | 1/4 | +1.2 | 6/16 | 32.9 |
| sanpo_8WF0e5NO_0195 | 2/2 | 2/2 | +1.3 | 2/4 | 10.4 |
| sanpo_RqOwmltc_0000 | 8/8 | 2/8 | +1.7 | 18/24 | 48.3 |
| sanpo_UGNwBEZM_0353 | 4/6 | 3/6 | +0.8 | 9/11 | 22.5 |
| sanpo_cBVSUvSN_0000 | 5/7 | 1/7 | +1.3 | 12/25 | 50.2 |
| sanpo_eHxtA669_0000 | 3/3 | 1/3 | +1.4 | 7/11 | 22.6 |
| sanpo_qn1eNtR0_0029 | 3/3 | 2/3 | +1.1 | 4/12 | 24.8 |
| 4 clips with no must_warn event | n/a | n/a | n/a | 0/59 | 22.8 to 41.7 |
| **Total** | **28/33 (85%)** | **12/33 (36%)** | +1.4 | 58/162 (36%) | 31.5 |

Lenient table: must_warn hits 29/33, all-event hits 69/84, side correct on
33 of 69 hits, 87 false alarms.

### Chance baseline

In a crowd the harness says "Person ..." every 1 to 2 s, and the scorer
matches by class, so some hits come from talking often. Same spoken
warnings, shifted in time by 7 s or 13 s (wrapping at clip end), same labels
(`results/sanpo/check/shift_baseline.py`):

| Set | Run | On time | Side right | Warn precision |
|---|---|---|---|---|
| SANPO (33 must_warn) | real | 28/33 (85%) | 12/33 (36%) | 58/162 (36%) |
| SANPO | shifted 7 s | 20/33 (61%) | 7/33 (21%) | 49/162 (30%) |
| SANPO | shifted 13 s | 23/33 (70%) | 7/33 (21%) | 44/162 (27%) |
| Internet clips, D9 (29 must_warn) | real | 12/29 (41%) | 6/29 (21%) | 24/57 (42%) |
| Internet clips | shifted 7 s | 7/29 (24%) | 0/29 | 16/57 (28%) |
| Internet clips | shifted 13 s | 8/29 (28%) | 3/29 (10%) | 19/57 (33%) |

### Against D9

- On time: 85% here vs 41% on the internet clips. Most of the gap is the
  event mix: every SANPO event is a person, the detector's best class, while
  9 of the 29 internet events are curbs, crosswalks or signs the fast path
  cannot name (60% of the 20 detectable ones). And the time-shifted run still
  gets 61 to 70% here, so on-time hits in crowds are mostly cheap. Above chance
  the gain is similar on both sets: +5 to +8 events here, +4 to +5 there.
- Side right: 36% here vs 21%, chance 21% here vs 0 to 10% there. Still the
  weak point. Label sides: 23 left, 9 right, 1 ahead (people pass on the
  walker's left on these US sidewalks). Of the 23 left passes, the credited
  warning said left 10 times, right 5, ahead 3, and 5 were missed. Of 9
  right passes it said right 2, ahead 5, left 2. The warning ends about 1.4
  s before t_close, while the person is still near the centre, and the label
  side is where they pass. A side taken from the track's lateral motion
  (which way it is drifting) would match the label better than its current
  position.
- Talk: 31.5 utterances per minute, about the same as D9 (33.9). On the 4
  clips with no must_warn event it still says 10 to 20 things per 30 s.
- With t_start capped at 4 s instead of 2.5 s (`results/sanpo/walk_scores_sanpo_approach4.md`):
  29/33 on time, 14/33 side right, so the cap moves the result by 1 to 2 events.

### What this set is and is not good for

Good: many head-on and passing people at the right height, labels that do
not depend on anyone having seen the model output, and a chance baseline.
Not good: vehicles, curbs and obstacles (none labelled), and it rewards
frequent talk in crowds. The class-only match in `scripts/score_walk.py`
is the main reason; matching the warning to a track id, or to the instance
mask, would fix it but needs the harness to log which track it spoke about.
