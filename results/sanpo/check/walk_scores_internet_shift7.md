# Walk scores

Hand labels from one annotator (test_videos/labels/README.md). Lead time in seconds, t_close minus first matching speech start; positive means warned before the event was nearest.

Rules:

- Only rows with status == spoken count.
- Match: audio_start in [t_start, t_close + 1.0] and the answer names the event's class (synonym table in scripts/score_walk.py) or one of its keywords. One utterance can hit several overlapping events.
- Side: the first matching utterance contains the label side word (left, right, ahead/front/center/straight).
- False alarm: spoken utterance matching no event. The bracketed count is how many of those name no labelled class at all (for example "No obstacles in my path").
- utt/min uses the largest win_end in the log as clip length.

| run | clip | spoken | utt/min | must_warn hits | all-event hits | lead median (must_warn) | lead min (must_warn) | lead median (all hits) | side correct (hits) | false alarms (no class word) |
|---|---|---|---|---|---|---|---|---|---|---|
| 197531-905015052_medium_shift7 | 197531-905015052_medium | 1 | 13.3 | n/a (0 events) | 0/6 (0%) | n/a | n/a | n/a | n/a (no hits) | 1 (0) |
| 3874684_720p_shift7 | 3874684_720p | 8 | 18.4 | 1/7 (14%) | 3/11 (27%) | +1.5 | +1.5 | +1.5 | 0/3 (0%) | 5 (0) |
| fifth-avenue-point-of-view-manhattan-nyc-looking-around-day_shift7 | fifth-avenue-point-of-view-manhattan-nyc-looking-around-day | 36 | 43.1 | 4/14 (29%) | 4/15 (27%) | -0.1 | -0.5 | -0.1 | 2/4 (50%) | 31 (0) |
| london_walking_shift7 | london_walking | 12 | 36.0 | 4/8 (50%) | 7/12 (58%) | -0.2 | -0.5 | -0.1 | 1/7 (14%) | 6 (0) |
| TOTAL shift7 (4 clips) | all | 57 | 33.9 | 9/29 (31%) | 14/44 (32%) | -0.1 | -0.5 | +0.1 | 3/14 (21%) | 43 (0) |

## Strict

must_warn events only. On time: names the class and the speech ends by t_close; one utterance credits one event. Spare: seconds between speech end and t_close. Warn precision: share of all spoken utterances that name a must_warn event near its time. Rules in the scripts/score_walk.py docstring.

| run | on time | on time, side right | spare median (s) | warn precision | utt/min |
|---|---|---|---|---|---|
| 197531-905015052_medium_shift7 | n/a (0 events) | n/a (0 events) | n/a | 0/1 (0%) | 13.3 |
| 3874684_720p_shift7 | 1/7 (14%) | 0/7 (0%) | +0.8 | 1/8 (12%) | 18.4 |
| fifth-avenue-point-of-view-manhattan-nyc-looking-around-day_shift7 | 4/14 (29%) | 0/14 (0%) | +0.7 | 10/36 (28%) | 43.1 |
| london_walking_shift7 | 2/8 (25%) | 0/8 (0%) | +0.7 | 5/12 (42%) | 36.0 |
| TOTAL shift7 (4 clips) | 7/29 (24%) | 0/29 (0%) | +0.8 | 16/57 (28%) | 33.9 |

## Per-event detail

### 197531-905015052_medium_shift7

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | bus | right | no | 3.0 | 5.5 | miss | n/a |  |  |
| e2 | curb | right | no | 0.0 | 2.0 | miss | n/a |  |  |
| e3 | pole | right | no | 0.0 | 8.0 | miss | n/a |  |  |
| e4 | person | ahead | no | 0.0 | 16.0 | miss | n/a |  |  |
| e5 | pole | ahead | no | 0.0 | 16.0 | miss | n/a |  |  |
| e6 | sign | right | no | 0.0 | 3.0 | miss | n/a |  |  |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|

### 3874684_720p_shift7

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | truck | left | no | 0.0 | 2.5 | 1.26 | +1.2 | no | Truck ahead. |
| e2 | sign | left | no | 0.0 | 1.0 | miss | n/a |  |  |
| e3 | other | left | no | 0.0 | 10.0 | 4.23 | +5.8 | no | Cone right. |
| e4 | other | right | no | 4.0 | 7.5 | miss | n/a |  |  |
| e5 | curb | left | yes | 6.0 | 9.0 | miss | n/a |  |  |
| e6 | pole | right | yes | 12.0 | 15.0 | 13.51 | +1.5 | no | Pole ahead. |
| e7 | truck | ahead | yes | 14.0 | 19.0 | miss | n/a |  |  |
| e8 | curb | ahead | yes | 21.0 | 24.0 | miss | n/a |  |  |
| e9 | crosswalk | ahead | yes | 21.0 | 24.5 | miss | n/a |  |  |
| e10 | pole | right | yes | 22.0 | 25.0 | miss | n/a |  |  |
| e11 | other | right | yes | 24.5 | 26.0 | miss | n/a |  |  |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e5 | curb | left | 9.0 | miss | n/a |  |  |
| e6 | pole | right | 15.0 | 13.51-14.16 | +0.8 | no | Pole ahead. |
| e7 | truck | ahead | 19.0 | miss | n/a |  |  |
| e8 | curb | ahead | 24.0 | miss | n/a |  |  |
| e9 | crosswalk | ahead | 24.5 | miss | n/a |  |  |
| e10 | pole | right | 25.0 | miss | n/a |  |  |
| e11 | other | right | 26.0 | miss | n/a |  |  |

### fifth-avenue-point-of-view-manhattan-nyc-looking-around-day_shift7

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | other | right | yes | 2.0 | 10.5 | miss | n/a |  |  |
| e2 | car | left | no | 2.5 | 3.0 | miss | n/a |  |  |
| e3 | stroller | right | yes | 6.0 | 7.0 | miss | n/a |  |  |
| e4 | person | left | yes | 12.0 | 12.5 | miss | n/a |  |  |
| e5 | person | left | yes | 13.0 | 13.5 | 13.98 | -0.5 | no | Person ahead. |
| e6 | person | left | yes | 14.0 | 15.0 | miss | n/a |  |  |
| e7 | pole | left | yes | 19.0 | 20.5 | miss | n/a |  |  |
| e8 | person | left | yes | 24.0 | 25.0 | 24.32 | +0.7 | yes | Person left. |
| e9 | sign | right | yes | 32.5 | 35.5 | miss | n/a |  |  |
| e10 | person | left | yes | 36.0 | 37.0 | 36.78 | +0.2 | yes | Person left. |
| e11 | trash_can | right | yes | 41.0 | 48.5 | 48.93 | -0.4 | no | Trash can left. |
| e12 | pole | ahead | yes | 43.0 | 48.5 | miss | n/a |  |  |
| e13 | crosswalk | ahead | yes | 42.5 | 45.0 | miss | n/a |  |  |
| e14 | car | ahead | yes | 45.5 | 48.5 | miss | n/a |  |  |
| e15 | car | right | yes | 49.5 | 50.5 | miss | n/a |  |  |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e3 | stroller | right | 7.0 | miss | n/a |  |  |
| e1 | other | right | 10.5 | miss | n/a |  |  |
| e4 | person | left | 12.5 | 11.67-12.39 | +0.1 | no | Person right. |
| e5 | person | left | 13.5 | miss | n/a |  |  |
| e6 | person | left | 15.0 | 13.98-14.93 | +0.1 | no | Person ahead. |
| e7 | pole | left | 20.5 | miss | n/a |  |  |
| e8 | person | left | 25.0 | 22.32-23.07 | +1.9 | no | Person ahead. |
| e9 | sign | right | 35.5 | miss | n/a |  |  |
| e10 | person | left | 37.0 | 34.90-35.69 | +1.3 | no | Person ahead. |
| e13 | crosswalk | ahead | 45.0 | miss | n/a |  |  |
| e11 | trash_can | right | 48.5 | miss | n/a |  |  |
| e12 | pole | ahead | 48.5 | miss | n/a |  |  |
| e14 | car | ahead | 48.5 | miss | n/a |  |  |
| e15 | car | right | 50.5 | miss | n/a |  |  |

### london_walking_shift7

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | left | yes | 0.0 | 1.5 | 0.35 | +1.1 | no | Person ahead. |
| e2 | person | left | yes | 2.0 | 3.0 | miss | n/a |  |  |
| e3 | person | left | yes | 3.0 | 4.0 | 4.35 | -0.4 | no | Person right. |
| e4 | person | ahead | yes | 4.5 | 5.0 | 5.11 | -0.1 | yes | Person ahead. |
| e5 | person | right | no | 5.0 | 5.5 | 5.11 | +0.4 | no | Person ahead. |
| e6 | sign | left | yes | 8.5 | 12.0 | miss | n/a |  |  |
| e7 | person | right | no | 10.0 | 11.0 | 11.11 | -0.1 | no | Person ahead. |
| e8 | person | right | yes | 12.5 | 13.0 | miss | n/a |  |  |
| e9 | person | left | yes | 13.0 | 14.0 | 14.52 | -0.5 | no | Person right. |
| e10 | sign | left | yes | 14.0 | 16.5 | miss | n/a |  |  |
| e11 | other | right | no | 17.0 | 19.5 | miss | n/a |  |  |
| e12 | person | ahead | no | 18.0 | 19.5 | 19.58 | -0.1 | no | Person left. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e1 | person | left | 1.5 | 0.35-1.17 | +0.3 | no | Person ahead. |
| e2 | person | left | 3.0 | miss | n/a |  |  |
| e3 | person | left | 4.0 | miss | n/a |  |  |
| e4 | person | ahead | 5.0 | miss | n/a |  |  |
| e6 | sign | left | 12.0 | miss | n/a |  |  |
| e8 | person | right | 13.0 | 11.11-11.94 | +1.1 | no | Person ahead. |
| e9 | person | left | 14.0 | miss | n/a |  |  |
| e10 | sign | left | 16.5 | miss | n/a |  |  |
