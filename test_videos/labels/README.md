# Walk event labels

Hand-made ground truth for scoring what Maya says during a walk
(`scripts/score_walk.py`). One JSON file per clip in `test_videos/`, named
after the clip stem.

| File | Clip | Length | Events | must_warn |
|---|---|---|---|---|
| `fifth-avenue-point-of-view-manhattan-nyc-looking-around-day.json` | Fifth Ave sidewalk, crowd, corner at 45 s | 54.5 s | 15 | 14 |
| `3874684_720p.json` | empty sidewalk, fence right, curb and crosswalk at 22 to 24 s | 26.3 s | 11 | 7 |
| `london_walking.json` | Canary Wharf plaza, people crossing, A-frame signs | 20.0 s | 12 | 8 |
| `197531-905015052_medium.json` | promenade at sunset, bus on the road | 16.5 s | 6 | 0 |

The promenade clip has no must_warn events: nothing comes into the walker's
path (the bus stays on the road beyond the curb). Its must_warn hit rate is
reported as n/a, not 0 or 100%.

## Schema

Each file is a list of events:

| Field | Meaning |
|---|---|
| `id` | `e1`, `e2`, ... unique within the file |
| `t_start` | seconds, when the thing is first clearly visible |
| `t_close` | seconds, when it is nearest or matters most |
| `cls` | person, bicycle, car, bus, truck, stroller, pole, trash_can, sign, curb, crosswalk, other |
| `side` | left, ahead, right, at `t_close` |
| `dist_bucket` | near (under 2 m), mid (2 to 5 m), far, at `t_close` |
| `motion` | approaching, receding, crossing, static |
| `must_warn` | true if a walker would need to hear about it to avoid contact or a curb |
| `keywords` | optional; extra words that also count as naming this event (used for `other` objects such as the Fifth Ave sphere, and for "car"/"vehicle" on pickup trucks) |
| `note` | what it is, and what I was unsure about |

## How the labels were made

- Frames every 0.5 s, timestamp burned in, tiled into contact sheets in
  `results/labels_frames/<stem>/` by `results/labels_frames/extract.sh`
  (ffmpeg in the maya-cosmos-tf container). Times are therefore to the
  nearest 0.5 s.
- I picked the events a blind walker would need: people coming at the
  walker, obstacles on the walking surface, vehicles close by or crossing
  ahead, curbs and crosswalk edges, readable signs. Continuous crowds are
  labelled as their closest individuals, not every person.
- Side is the object's position in the frame at `t_close` (left third, middle,
  right third), not a world direction.
- Distances are guesses from a monocular frame. The London camera is low,
  which makes people look closer than they are.

## Caveats

- Single annotator, one pass, no second rater, so there is no agreement
  figure. `must_warn` and `t_close` are judgment calls; borderline cases say
  so in `note`.
- Labels were written after reading the hand checks in `docs/decisions.md`
  and after seeing the existing model runs' transcripts in D2 to D4, so they
  are not blind to model output. One disagreement with D3 is recorded in
  `3874684_720p.json` (e1 note).
- 44 events over about 2 minutes of video is a small set; one event moves a
  per-clip rate by 7 to 17 points.

## Scoring rules (summary)

Implemented and documented at the top of `scripts/score_walk.py`:

- Only spoken utterances count (`status == spoken`).
- An utterance matches an event when `audio_start` is in
  `[t_start, t_close + 1.0]` and the answer names the class (synonym table)
  or one of the event's keywords.
- Lead time is `t_close - audio_start` of the first match; positive is in time.
- Side is correct when the first matching answer contains the label's side
  word (left, right, or ahead/front/center/straight).
- A false alarm is a spoken utterance that matches no event.
