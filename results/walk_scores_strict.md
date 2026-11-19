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
| 197531-905015052_medium_describe | 197531-905015052_medium | 7 | 26.2 | n/a (0 events) | 2/6 (33%) | n/a | n/a | +6.2 | 1/2 (50%) | 4 (0) |
| 3874684_720p_describe | 3874684_720p | 10 | 22.9 | 1/7 (14%) | 1/11 (9%) | +2.8 | +2.8 | +2.8 | 0/1 (0%) | 8 (7) |
| fifth-avenue-point-of-view-manhattan-nyc-looking-around-day_describe | fifth-avenue-point-of-view-manhattan-nyc-looking-around-day | 22 | 24.4 | 6/14 (43%) | 6/15 (40%) | -0.6 | -0.9 | -0.6 | 5/6 (83%) | 17 (0) |
| london_walking_describe | london_walking | 8 | 24.3 | 3/8 (38%) | 5/12 (42%) | +0.1 | -0.9 | +0.1 | 1/5 (20%) | 4 (0) |
| 197531-905015052_medium_instruct | 197531-905015052_medium | 6 | 22.9 | n/a (0 events) | 2/6 (33%) | n/a | n/a | +6.2 | 2/2 (100%) | 3 (0) |
| 3874684_720p_instruct | 3874684_720p | 10 | 23.2 | 1/7 (14%) | 2/11 (18%) | +2.2 | +2.2 | +4.7 | 0/2 (0%) | 6 (3) |
| fifth-avenue-point-of-view-manhattan-nyc-looking-around-day_instruct | fifth-avenue-point-of-view-manhattan-nyc-looking-around-day | 21 | 23.2 | 7/14 (50%) | 7/15 (47%) | -0.5 | -0.8 | -0.5 | 4/7 (57%) | 15 (2) |
| london_walking_instruct | london_walking | 8 | 24.3 | 3/8 (38%) | 6/12 (50%) | +0.1 | -0.2 | +0.3 | 4/6 (67%) | 3 (0) |
| 197531-905015052_medium_fastonly | 197531-905015052_medium | 1 | 9.6 | n/a (0 events) | 2/6 (33%) | n/a | n/a | +5.6 | 1/2 (50%) | 0 (0) |
| 3874684_720p_fastonly | 3874684_720p | 10 | 23.0 | 3/7 (43%) | 4/11 (36%) | +1.9 | +0.8 | +1.3 | 1/4 (25%) | 5 (1) |
| fifth-avenue-point-of-view-manhattan-nyc-looking-around-day_fastonly | fifth-avenue-point-of-view-manhattan-nyc-looking-around-day | 27 | 32.4 | 7/14 (50%) | 8/15 (53%) | +0.4 | -0.5 | +0.4 | 1/8 (12%) | 17 (0) |
| london_walking_fastonly | london_walking | 7 | 21.2 | 3/8 (38%) | 3/12 (25%) | -0.1 | -0.7 | -0.1 | 1/3 (33%) | 5 (0) |
| 197531-905015052_medium_fused | 197531-905015052_medium | 9 | 34.8 | n/a (0 events) | 3/6 (50%) | n/a | n/a | +1.2 | 1/3 (33%) | 7 (0) |
| 3874684_720p_fused | 3874684_720p | 17 | 39.0 | 5/7 (71%) | 6/11 (55%) | +0.5 | -0.7 | +0.5 | 4/6 (67%) | 10 (0) |
| fifth-avenue-point-of-view-manhattan-nyc-looking-around-day_fused | fifth-avenue-point-of-view-manhattan-nyc-looking-around-day | 30 | 33.0 | 8/14 (57%) | 9/15 (60%) | +0.2 | -0.9 | +0.3 | 0/9 (0%) | 21 (0) |
| london_walking_fused | london_walking | 11 | 33.0 | 5/8 (62%) | 6/12 (50%) | +0.2 | -0.7 | +0.2 | 3/6 (50%) | 6 (2) |
| 197531-905015052_medium_fastonly2 | 197531-905015052_medium | 1 | 13.3 | n/a (0 events) | 1/6 (17%) | n/a | n/a | +0.7 | 1/1 (100%) | 0 (0) |
| 3874684_720p_fastonly2 | 3874684_720p | 8 | 18.4 | 1/7 (14%) | 2/11 (18%) | +1.1 | +1.1 | +1.0 | 1/2 (50%) | 5 (1) |
| fifth-avenue-point-of-view-manhattan-nyc-looking-around-day_fastonly2 | fifth-avenue-point-of-view-manhattan-nyc-looking-around-day | 36 | 43.1 | 8/14 (57%) | 9/15 (60%) | +0.3 | -0.6 | +0.1 | 2/9 (22%) | 24 (0) |
| london_walking_fastonly2 | london_walking | 12 | 36.0 | 4/8 (50%) | 5/12 (42%) | +0.5 | -0.1 | +0.6 | 1/5 (20%) | 4 (0) |
| TOTAL describe (4 clips) | all | 47 | 24.3 | 10/29 (34%) | 14/44 (32%) | -0.3 | -0.9 | -0.3 | 7/14 (50%) | 33 (7) |
| TOTAL fastonly (4 clips) | all | 45 | 26.4 | 13/29 (45%) | 17/44 (39%) | +0.4 | -0.7 | +0.5 | 4/17 (24%) | 27 (1) |
| TOTAL fastonly2 (4 clips) | all | 57 | 33.9 | 13/29 (45%) | 17/44 (39%) | +0.4 | -0.6 | +0.4 | 5/17 (29%) | 33 (1) |
| TOTAL fused (4 clips) | all | 67 | 34.6 | 18/29 (62%) | 24/44 (55%) | +0.2 | -0.9 | +0.3 | 8/24 (33%) | 44 (2) |
| TOTAL instruct (4 clips) | all | 45 | 23.3 | 11/29 (38%) | 17/44 (39%) | +0.1 | -0.8 | +0.3 | 10/17 (59%) | 27 (5) |

## Strict

must_warn events only. On time: names the class and the speech ends by t_close; one utterance credits one event. Spare: seconds between speech end and t_close. Warn precision: share of all spoken utterances that name a must_warn event near its time. Rules in the scripts/score_walk.py docstring.

| run | on time | on time, side right | spare median (s) | warn precision | utt/min |
|---|---|---|---|---|---|
| 197531-905015052_medium_describe | n/a (0 events) | n/a (0 events) | n/a | 0/7 (0%) | 26.2 |
| 3874684_720p_describe | 1/7 (14%) | 0/7 (0%) | +0.8 | 2/10 (20%) | 22.9 |
| fifth-avenue-point-of-view-manhattan-nyc-looking-around-day_describe | 1/14 (7%) | 0/14 (0%) | +0.4 | 7/22 (32%) | 24.4 |
| london_walking_describe | 3/8 (38%) | 0/8 (0%) | +0.8 | 4/8 (50%) | 24.3 |
| 197531-905015052_medium_instruct | n/a (0 events) | n/a (0 events) | n/a | 0/6 (0%) | 22.9 |
| 3874684_720p_instruct | 0/7 (0%) | 0/7 (0%) | n/a | 2/10 (20%) | 23.2 |
| fifth-avenue-point-of-view-manhattan-nyc-looking-around-day_instruct | 2/14 (14%) | 0/14 (0%) | +0.3 | 9/21 (43%) | 23.2 |
| london_walking_instruct | 1/8 (12%) | 1/8 (12%) | +0.3 | 4/8 (50%) | 24.3 |
| 197531-905015052_medium_fastonly | n/a (0 events) | n/a (0 events) | n/a | 0/1 (0%) | 9.6 |
| 3874684_720p_fastonly | 2/7 (29%) | 0/7 (0%) | +1.8 | 5/10 (50%) | 23.0 |
| fifth-avenue-point-of-view-manhattan-nyc-looking-around-day_fastonly | 5/14 (36%) | 0/14 (0%) | +0.3 | 11/27 (41%) | 32.4 |
| london_walking_fastonly | 1/8 (12%) | 1/8 (12%) | +0.3 | 2/7 (29%) | 21.2 |
| 197531-905015052_medium_fused | n/a (0 events) | n/a (0 events) | n/a | 0/9 (0%) | 34.8 |
| 3874684_720p_fused | 2/7 (29%) | 1/7 (14%) | +1.0 | 7/17 (41%) | 39.0 |
| fifth-avenue-point-of-view-manhattan-nyc-looking-around-day_fused | 4/14 (29%) | 0/14 (0%) | +0.7 | 12/30 (40%) | 33.0 |
| london_walking_fused | 1/8 (12%) | 1/8 (12%) | +0.3 | 4/11 (36%) | 33.0 |
| 197531-905015052_medium_fastonly2 | n/a (0 events) | n/a (0 events) | n/a | 0/1 (0%) | 13.3 |
| 3874684_720p_fastonly2 | 1/7 (14%) | 0/7 (0%) | +0.4 | 2/8 (25%) | 18.4 |
| fifth-avenue-point-of-view-manhattan-nyc-looking-around-day_fastonly2 | 7/14 (50%) | 3/14 (21%) | +1.3 | 17/36 (47%) | 43.1 |
| london_walking_fastonly2 | 4/8 (50%) | 3/8 (38%) | +1.0 | 5/12 (42%) | 36.0 |
| TOTAL describe (4 clips) | 5/29 (17%) | 0/29 (0%) | +0.8 | 13/47 (28%) | 24.3 |
| TOTAL fastonly (4 clips) | 8/29 (28%) | 1/29 (3%) | +0.7 | 18/45 (40%) | 26.4 |
| TOTAL fastonly2 (4 clips) | 12/29 (41%) | 6/29 (21%) | +1.3 | 24/57 (42%) | 33.9 |
| TOTAL fused (4 clips) | 7/29 (24%) | 2/29 (7%) | +0.6 | 23/67 (34%) | 34.6 |
| TOTAL instruct (4 clips) | 3/29 (10%) | 1/29 (3%) | +0.3 | 15/45 (33%) | 23.3 |

## Per-event detail

### 197531-905015052_medium_describe

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | bus | right | no | 3.0 | 5.5 | 6.45 | -1.0 | yes | Bus on the right. |
| e2 | curb | right | no | 0.0 | 2.0 | miss | n/a |  |  |
| e3 | pole | right | no | 0.0 | 8.0 | miss | n/a |  |  |
| e4 | person | ahead | no | 0.0 | 16.0 | 2.56 | +13.4 | no | Person walking toward you. |
| e5 | pole | ahead | no | 0.0 | 16.0 | miss | n/a |  |  |
| e6 | sign | right | no | 0.0 | 3.0 | miss | n/a |  |  |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|

### 3874684_720p_describe

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | truck | left | no | 0.0 | 2.5 | miss | n/a |  |  |
| e2 | sign | left | no | 0.0 | 1.0 | miss | n/a |  |  |
| e3 | other | left | no | 0.0 | 10.0 | miss | n/a |  |  |
| e4 | other | right | no | 4.0 | 7.5 | miss | n/a |  |  |
| e5 | curb | left | yes | 6.0 | 9.0 | miss | n/a |  |  |
| e6 | pole | right | yes | 12.0 | 15.0 | miss | n/a |  |  |
| e7 | truck | ahead | yes | 14.0 | 19.0 | 16.22 | +2.8 | no | A black car approaching on the left. |
| e8 | curb | ahead | yes | 21.0 | 24.0 | miss | n/a |  |  |
| e9 | crosswalk | ahead | yes | 21.0 | 24.5 | miss | n/a |  |  |
| e10 | pole | right | yes | 22.0 | 25.0 | miss | n/a |  |  |
| e11 | other | right | yes | 24.5 | 26.0 | miss | n/a |  |  |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e5 | curb | left | 9.0 | miss | n/a |  |  |
| e6 | pole | right | 15.0 | miss | n/a |  |  |
| e7 | truck | ahead | 19.0 | 16.22-18.16 | +0.8 | no | A black car approaching on the left. |
| e8 | curb | ahead | 24.0 | miss | n/a |  |  |
| e9 | crosswalk | ahead | 24.5 | miss | n/a |  |  |
| e10 | pole | right | 25.0 | miss | n/a |  |  |
| e11 | other | right | 26.0 | miss | n/a |  |  |

### fifth-avenue-point-of-view-manhattan-nyc-looking-around-day_describe

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | other | right | yes | 2.0 | 10.5 | miss | n/a |  |  |
| e2 | car | left | no | 2.5 | 3.0 | miss | n/a |  |  |
| e3 | stroller | right | yes | 6.0 | 7.0 | miss | n/a |  |  |
| e4 | person | left | yes | 12.0 | 12.5 | 13.30 | -0.8 | yes | Person in black coat, slightly left. |
| e5 | person | left | yes | 13.0 | 13.5 | 13.30 | +0.2 | yes | Person in black coat, slightly left. |
| e6 | person | left | yes | 14.0 | 15.0 | 15.74 | -0.7 | yes | Person in front left, slightly ahead. |
| e7 | pole | left | yes | 19.0 | 20.5 | miss | n/a |  |  |
| e8 | person | left | yes | 24.0 | 25.0 | 25.87 | -0.9 | no | Person in front, slightly right. |
| e9 | sign | right | yes | 32.5 | 35.5 | miss | n/a |  |  |
| e10 | person | left | yes | 36.0 | 37.0 | 37.19 | -0.2 | yes | Person in yellow jacket, left. |
| e11 | trash_can | right | yes | 41.0 | 48.5 | 48.87 | -0.4 | yes | Trash can, right, slightly ahead. |
| e12 | pole | ahead | yes | 43.0 | 48.5 | miss | n/a |  |  |
| e13 | crosswalk | ahead | yes | 42.5 | 45.0 | miss | n/a |  |  |
| e14 | car | ahead | yes | 45.5 | 48.5 | miss | n/a |  |  |
| e15 | car | right | yes | 49.5 | 50.5 | miss | n/a |  |  |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e3 | stroller | right | 7.0 | miss | n/a |  |  |
| e1 | other | right | 10.5 | miss | n/a |  |  |
| e4 | person | left | 12.5 | miss | n/a |  |  |
| e5 | person | left | 13.5 | 10.59-13.06 | +0.4 | no | Person in black coat, right, close. |
| e6 | person | left | 15.0 | miss | n/a |  |  |
| e7 | pole | left | 20.5 | miss | n/a |  |  |
| e8 | person | left | 25.0 | miss | n/a |  |  |
| e9 | sign | right | 35.5 | miss | n/a |  |  |
| e10 | person | left | 37.0 | miss | n/a |  |  |
| e13 | crosswalk | ahead | 45.0 | miss | n/a |  |  |
| e11 | trash_can | right | 48.5 | miss | n/a |  |  |
| e12 | pole | ahead | 48.5 | miss | n/a |  |  |
| e14 | car | ahead | 48.5 | miss | n/a |  |  |
| e15 | car | right | 50.5 | miss | n/a |  |  |

### london_walking_describe

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | left | yes | 0.0 | 1.5 | miss | n/a |  |  |
| e2 | person | left | yes | 2.0 | 3.0 | 2.61 | +0.4 | no | Person walking away from you. |
| e3 | person | left | yes | 3.0 | 4.0 | miss | n/a |  |  |
| e4 | person | ahead | yes | 4.5 | 5.0 | miss | n/a |  |  |
| e5 | person | right | no | 5.0 | 5.5 | 6.21 | -0.7 | no | Person walking toward you, slightly left. |
| e6 | sign | left | yes | 8.5 | 12.0 | miss | n/a |  |  |
| e7 | person | right | no | 10.0 | 11.0 | 10.40 | +0.6 | no | Person walking away, center. |
| e8 | person | right | yes | 12.5 | 13.0 | 13.90 | -0.9 | no | Person walking away on the left. |
| e9 | person | left | yes | 13.0 | 14.0 | 13.90 | +0.1 | yes | Person walking away on the left. |
| e10 | sign | left | yes | 14.0 | 16.5 | miss | n/a |  |  |
| e11 | other | right | no | 17.0 | 19.5 | miss | n/a |  |  |
| e12 | person | ahead | no | 18.0 | 19.5 | miss | n/a |  |  |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e1 | person | left | 1.5 | miss | n/a |  |  |
| e2 | person | left | 3.0 | miss | n/a |  |  |
| e3 | person | left | 4.0 | miss | n/a |  |  |
| e4 | person | ahead | 5.0 | 2.61-4.15 | +0.8 | no | Person walking away from you. |
| e6 | sign | left | 12.0 | miss | n/a |  |  |
| e8 | person | right | 13.0 | 10.40-12.17 | +0.8 | no | Person walking away, center. |
| e9 | person | left | 14.0 | 12.25-13.81 | +0.2 | no | Person walking away from you. |
| e10 | sign | left | 16.5 | miss | n/a |  |  |

### 197531-905015052_medium_instruct

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | bus | right | no | 3.0 | 5.5 | 5.93 | -0.4 | yes | Move right, bus on right side |
| e2 | curb | right | no | 0.0 | 2.0 | miss | n/a |  |  |
| e3 | pole | right | no | 0.0 | 8.0 | miss | n/a |  |  |
| e4 | person | ahead | no | 0.0 | 16.0 | 3.19 | +12.8 | yes | Move right, pedestrian ahead on right. |
| e5 | pole | ahead | no | 0.0 | 16.0 | miss | n/a |  |  |
| e6 | sign | right | no | 0.0 | 3.0 | miss | n/a |  |  |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|

### 3874684_720p_instruct

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | truck | left | no | 0.0 | 2.5 | miss | n/a |  |  |
| e2 | sign | left | no | 0.0 | 1.0 | miss | n/a |  |  |
| e3 | other | left | no | 0.0 | 10.0 | 2.75 | +7.3 | no | Move right, construction area ahead. |
| e4 | other | right | no | 4.0 | 7.5 | miss | n/a |  |  |
| e5 | curb | left | yes | 6.0 | 9.0 | miss | n/a |  |  |
| e6 | pole | right | yes | 12.0 | 15.0 | miss | n/a |  |  |
| e7 | truck | ahead | yes | 14.0 | 19.0 | 16.78 | +2.2 | no | Move right, black car on right side. |
| e8 | curb | ahead | yes | 21.0 | 24.0 | miss | n/a |  |  |
| e9 | crosswalk | ahead | yes | 21.0 | 24.5 | miss | n/a |  |  |
| e10 | pole | right | yes | 22.0 | 25.0 | miss | n/a |  |  |
| e11 | other | right | yes | 24.5 | 26.0 | miss | n/a |  |  |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e5 | curb | left | 9.0 | miss | n/a |  |  |
| e6 | pole | right | 15.0 | miss | n/a |  |  |
| e7 | truck | ahead | 19.0 | miss | n/a |  |  |
| e8 | curb | ahead | 24.0 | miss | n/a |  |  |
| e9 | crosswalk | ahead | 24.5 | miss | n/a |  |  |
| e10 | pole | right | 25.0 | miss | n/a |  |  |
| e11 | other | right | 26.0 | miss | n/a |  |  |

### fifth-avenue-point-of-view-manhattan-nyc-looking-around-day_instruct

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | other | right | yes | 2.0 | 10.5 | 7.80 | +2.7 | yes | Move right, large ball object on right side |
| e2 | car | left | no | 2.5 | 3.0 | miss | n/a |  |  |
| e3 | stroller | right | yes | 6.0 | 7.0 | miss | n/a |  |  |
| e4 | person | left | yes | 12.0 | 12.5 | 13.05 | -0.6 | yes | Move left, pedestrian crossing ahead. |
| e5 | person | left | yes | 13.0 | 13.5 | 13.05 | +0.4 | yes | Move left, pedestrian crossing ahead. |
| e6 | person | left | yes | 14.0 | 15.0 | 15.72 | -0.7 | no | Move right, pedestrian with yellow bag ahead. |
| e7 | pole | left | yes | 19.0 | 20.5 | miss | n/a |  |  |
| e8 | person | left | yes | 24.0 | 25.0 | miss | n/a |  |  |
| e9 | sign | right | yes | 32.5 | 35.5 | miss | n/a |  |  |
| e10 | person | left | yes | 36.0 | 37.0 | 37.81 | -0.8 | no | Move right, pedestrian with mask and hoodie. |
| e11 | trash_can | right | yes | 41.0 | 48.5 | miss | n/a |  |  |
| e12 | pole | ahead | yes | 43.0 | 48.5 | miss | n/a |  |  |
| e13 | crosswalk | ahead | yes | 42.5 | 45.0 | 45.49 | -0.5 | yes | Move left, pedestrian crossing ahead. |
| e14 | car | ahead | yes | 45.5 | 48.5 | 48.22 | +0.3 | no | Move left, white car approaching |
| e15 | car | right | yes | 49.5 | 50.5 | miss | n/a |  |  |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e3 | stroller | right | 7.0 | miss | n/a |  |  |
| e1 | other | right | 10.5 | miss | n/a |  |  |
| e4 | person | left | 12.5 | miss | n/a |  |  |
| e5 | person | left | 13.5 | 11.04-12.94 | +0.6 | no | Move right, person with umbrella. |
| e6 | person | left | 15.0 | miss | n/a |  |  |
| e7 | pole | left | 20.5 | miss | n/a |  |  |
| e8 | person | left | 25.0 | miss | n/a |  |  |
| e9 | sign | right | 35.5 | miss | n/a |  |  |
| e10 | person | left | 37.0 | miss | n/a |  |  |
| e13 | crosswalk | ahead | 45.0 | miss | n/a |  |  |
| e11 | trash_can | right | 48.5 | miss | n/a |  |  |
| e12 | pole | ahead | 48.5 | miss | n/a |  |  |
| e14 | car | ahead | 48.5 | miss | n/a |  |  |
| e15 | car | right | 50.5 | 48.22-50.39 | +0.1 | no | Move left, white car approaching |

### london_walking_instruct

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | left | yes | 0.0 | 1.5 | miss | n/a |  |  |
| e2 | person | left | yes | 2.0 | 3.0 | 2.68 | +0.3 | no | Move right, pedestrian crossing ahead. |
| e3 | person | left | yes | 3.0 | 4.0 | miss | n/a |  |  |
| e4 | person | ahead | yes | 4.5 | 5.0 | 5.19 | -0.2 | no | Move right, pedestrian with coffee cup. |
| e5 | person | right | no | 5.0 | 5.5 | 5.19 | +0.3 | yes | Move right, pedestrian with coffee cup. |
| e6 | sign | left | yes | 8.5 | 12.0 | miss | n/a |  |  |
| e7 | person | right | no | 10.0 | 11.0 | 10.59 | +0.4 | yes | Move right, pedestrian on right |
| e8 | person | right | yes | 12.5 | 13.0 | 12.95 | +0.1 | yes | Move right, man in black jacket stepping off sidewalk. |
| e9 | person | left | yes | 13.0 | 14.0 | miss | n/a |  |  |
| e10 | sign | left | yes | 14.0 | 16.5 | miss | n/a |  |  |
| e11 | other | right | no | 17.0 | 19.5 | miss | n/a |  |  |
| e12 | person | ahead | no | 18.0 | 19.5 | 18.59 | +0.9 | yes | Move right, pedestrian with briefcase crossing ahead. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e1 | person | left | 1.5 | miss | n/a |  |  |
| e2 | person | left | 3.0 | miss | n/a |  |  |
| e3 | person | left | 4.0 | miss | n/a |  |  |
| e4 | person | ahead | 5.0 | miss | n/a |  |  |
| e6 | sign | left | 12.0 | miss | n/a |  |  |
| e8 | person | right | 13.0 | 10.59-12.67 | +0.3 | yes | Move right, pedestrian on right |
| e9 | person | left | 14.0 | miss | n/a |  |  |
| e10 | sign | left | 16.5 | miss | n/a |  |  |

### 197531-905015052_medium_fastonly

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | bus | right | no | 3.0 | 5.5 | miss | n/a |  |  |
| e2 | curb | right | no | 0.0 | 2.0 | miss | n/a |  |  |
| e3 | pole | right | no | 0.0 | 8.0 | 6.40 | +1.6 | no | Pole ahead, approaching. |
| e4 | person | ahead | no | 0.0 | 16.0 | miss | n/a |  |  |
| e5 | pole | ahead | no | 0.0 | 16.0 | 6.40 | +9.6 | yes | Pole ahead, approaching. |
| e6 | sign | right | no | 0.0 | 3.0 | miss | n/a |  |  |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|

### 3874684_720p_fastonly

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | truck | left | no | 0.0 | 2.5 | 1.98 | +0.5 | yes | Truck on your left, approaching. |
| e2 | sign | left | no | 0.0 | 1.0 | miss | n/a |  |  |
| e3 | other | left | no | 0.0 | 10.0 | miss | n/a |  |  |
| e4 | other | right | no | 4.0 | 7.5 | miss | n/a |  |  |
| e5 | curb | left | yes | 6.0 | 9.0 | miss | n/a |  |  |
| e6 | pole | right | yes | 12.0 | 15.0 | 13.07 | +1.9 | no | Pole close ahead, approaching. |
| e7 | truck | ahead | yes | 14.0 | 19.0 | 18.25 | +0.8 | no | Car on your left, approaching. |
| e8 | curb | ahead | yes | 21.0 | 24.0 | miss | n/a |  |  |
| e9 | crosswalk | ahead | yes | 21.0 | 24.5 | miss | n/a |  |  |
| e10 | pole | right | yes | 22.0 | 25.0 | 22.32 | +2.7 | no | Pole close ahead. |
| e11 | other | right | yes | 24.5 | 26.0 | miss | n/a |  |  |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e5 | curb | left | 9.0 | miss | n/a |  |  |
| e6 | pole | right | 15.0 | 11.93-12.93 | +2.1 | no | Pole close ahead. |
| e7 | truck | ahead | 19.0 | miss | n/a |  |  |
| e8 | curb | ahead | 24.0 | miss | n/a |  |  |
| e9 | crosswalk | ahead | 24.5 | miss | n/a |  |  |
| e10 | pole | right | 25.0 | 22.32-23.48 | +1.5 | no | Pole close ahead. |
| e11 | other | right | 26.0 | miss | n/a |  |  |

### fifth-avenue-point-of-view-manhattan-nyc-looking-around-day_fastonly

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | other | right | yes | 2.0 | 10.5 | miss | n/a |  |  |
| e2 | car | left | no | 2.5 | 3.0 | 3.71 | -0.7 | yes | Car on your left, approaching. |
| e3 | stroller | right | yes | 6.0 | 7.0 | miss | n/a |  |  |
| e4 | person | left | yes | 12.0 | 12.5 | 12.17 | +0.3 | no | Person close ahead. |
| e5 | person | left | yes | 13.0 | 13.5 | 13.53 | -0.0 | no | Person on your right, approaching. |
| e6 | person | left | yes | 14.0 | 15.0 | 15.49 | -0.5 | no | Person close on your right. |
| e7 | pole | left | yes | 19.0 | 20.5 | miss | n/a |  |  |
| e8 | person | left | yes | 24.0 | 25.0 | 24.06 | +0.9 | no | Person close on your right. |
| e9 | sign | right | yes | 32.5 | 35.5 | miss | n/a |  |  |
| e10 | person | left | yes | 36.0 | 37.0 | miss | n/a |  |  |
| e11 | trash_can | right | yes | 41.0 | 48.5 | 43.44 | +5.1 | no | Trash can close on your left, approaching. |
| e12 | pole | ahead | yes | 43.0 | 48.5 | miss | n/a |  |  |
| e13 | crosswalk | ahead | yes | 42.5 | 45.0 | miss | n/a |  |  |
| e14 | car | ahead | yes | 45.5 | 48.5 | 46.37 | +2.1 | no | Car on your left, approaching. |
| e15 | car | right | yes | 49.5 | 50.5 | 50.11 | +0.4 | no | Car ahead, approaching. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e3 | stroller | right | 7.0 | miss | n/a |  |  |
| e1 | other | right | 10.5 | miss | n/a |  |  |
| e4 | person | left | 12.5 | miss | n/a |  |  |
| e5 | person | left | 13.5 | 12.17-13.47 | +0.0 | no | Person close ahead. |
| e6 | person | left | 15.0 | miss | n/a |  |  |
| e7 | pole | left | 20.5 | miss | n/a |  |  |
| e8 | person | left | 25.0 | 22.65-23.99 | +1.0 | no | Person close ahead. |
| e9 | sign | right | 35.5 | miss | n/a |  |  |
| e10 | person | left | 37.0 | 34.90-36.81 | +0.2 | no | Person on your right, approaching. |
| e13 | crosswalk | ahead | 45.0 | miss | n/a |  |  |
| e11 | trash_can | right | 48.5 | 43.44-45.90 | +2.6 | no | Trash can close on your left, approaching. |
| e12 | pole | ahead | 48.5 | miss | n/a |  |  |
| e14 | car | ahead | 48.5 | 46.37-48.17 | +0.3 | no | Car on your left, approaching. |
| e15 | car | right | 50.5 | miss | n/a |  |  |

### london_walking_fastonly

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | left | yes | 0.0 | 1.5 | 1.58 | -0.1 | yes | Person on your left, approaching. |
| e2 | person | left | yes | 2.0 | 3.0 | 3.74 | -0.7 | no | Person ahead, approaching. |
| e3 | person | left | yes | 3.0 | 4.0 | 3.74 | +0.3 | no | Person ahead, approaching. |
| e4 | person | ahead | yes | 4.5 | 5.0 | miss | n/a |  |  |
| e5 | person | right | no | 5.0 | 5.5 | miss | n/a |  |  |
| e6 | sign | left | yes | 8.5 | 12.0 | miss | n/a |  |  |
| e7 | person | right | no | 10.0 | 11.0 | miss | n/a |  |  |
| e8 | person | right | yes | 12.5 | 13.0 | miss | n/a |  |  |
| e9 | person | left | yes | 13.0 | 14.0 | miss | n/a |  |  |
| e10 | sign | left | yes | 14.0 | 16.5 | miss | n/a |  |  |
| e11 | other | right | no | 17.0 | 19.5 | miss | n/a |  |  |
| e12 | person | ahead | no | 18.0 | 19.5 | miss | n/a |  |  |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e1 | person | left | 1.5 | miss | n/a |  |  |
| e2 | person | left | 3.0 | miss | n/a |  |  |
| e3 | person | left | 4.0 | 1.58-3.66 | +0.3 | yes | Person on your left, approaching. |
| e4 | person | ahead | 5.0 | miss | n/a |  |  |
| e6 | sign | left | 12.0 | miss | n/a |  |  |
| e8 | person | right | 13.0 | miss | n/a |  |  |
| e9 | person | left | 14.0 | miss | n/a |  |  |
| e10 | sign | left | 16.5 | miss | n/a |  |  |

### 197531-905015052_medium_fused

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | bus | right | no | 3.0 | 5.5 | miss | n/a |  |  |
| e2 | curb | right | no | 0.0 | 2.0 | 2.85 | -0.8 | no | Curb on left side ahead. |
| e3 | pole | right | no | 0.0 | 8.0 | 6.82 | +1.2 | no | Pole ahead, approaching. |
| e4 | person | ahead | no | 0.0 | 16.0 | miss | n/a |  |  |
| e5 | pole | ahead | no | 0.0 | 16.0 | 6.82 | +9.2 | yes | Pole ahead, approaching. |
| e6 | sign | right | no | 0.0 | 3.0 | miss | n/a |  |  |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|

### 3874684_720p_fused

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | truck | left | no | 0.0 | 2.5 | 1.94 | +0.6 | yes | Truck on your left, approaching. |
| e2 | sign | left | no | 0.0 | 1.0 | miss | n/a |  |  |
| e3 | other | left | no | 0.0 | 10.0 | miss | n/a |  |  |
| e4 | other | right | no | 4.0 | 7.5 | miss | n/a |  |  |
| e5 | curb | left | yes | 6.0 | 9.0 | 8.48 | +0.5 | yes | A curb in left background |
| e6 | pole | right | yes | 12.0 | 15.0 | 12.83 | +2.2 | no | Pole close ahead, approaching. |
| e7 | truck | ahead | yes | 14.0 | 19.0 | 19.72 | -0.7 | yes | Truck ahead, approaching. |
| e8 | curb | ahead | yes | 21.0 | 24.0 | 23.30 | +0.7 | yes | Curb ahead left of sidewalk. |
| e9 | crosswalk | ahead | yes | 21.0 | 24.5 | miss | n/a |  |  |
| e10 | pole | right | yes | 22.0 | 25.0 | 25.08 | -0.1 | no | Pole close ahead. |
| e11 | other | right | yes | 24.5 | 26.0 | miss | n/a |  |  |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e5 | curb | left | 9.0 | miss | n/a |  |  |
| e6 | pole | right | 15.0 | 12.83-14.77 | +0.2 | no | Pole close ahead, approaching. |
| e7 | truck | ahead | 19.0 | miss | n/a |  |  |
| e8 | curb | ahead | 24.0 | miss | n/a |  |  |
| e9 | crosswalk | ahead | 24.5 | miss | n/a |  |  |
| e10 | pole | right | 25.0 | 21.87-23.23 | +1.8 | yes | Pole close on your right. |
| e11 | other | right | 26.0 | miss | n/a |  |  |

### fifth-avenue-point-of-view-manhattan-nyc-looking-around-day_fused

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | other | right | yes | 2.0 | 10.5 | miss | n/a |  |  |
| e2 | car | left | no | 2.5 | 3.0 | 2.61 | +0.4 | no | A yellow taxi on the street ahead. |
| e3 | stroller | right | yes | 6.0 | 7.0 | miss | n/a |  |  |
| e4 | person | left | yes | 12.0 | 12.5 | 13.36 | -0.9 | no | A red curb on the pedestrian walkway. |
| e5 | person | left | yes | 13.0 | 13.5 | 13.36 | +0.1 | no | A red curb on the pedestrian walkway. |
| e6 | person | left | yes | 14.0 | 15.0 | 15.64 | -0.6 | no | Person close on your right. |
| e7 | pole | left | yes | 19.0 | 20.5 | miss | n/a |  |  |
| e8 | person | left | yes | 24.0 | 25.0 | 24.53 | +0.5 | no | Person close on your right. |
| e9 | sign | right | yes | 32.5 | 35.5 | miss | n/a |  |  |
| e10 | person | left | yes | 36.0 | 37.0 | miss | n/a |  |  |
| e11 | trash_can | right | yes | 41.0 | 48.5 | 42.81 | +5.7 | no | Trash can close on your left, approaching. |
| e12 | pole | ahead | yes | 43.0 | 48.5 | miss | n/a |  |  |
| e13 | crosswalk | ahead | yes | 42.5 | 45.0 | 45.07 | -0.1 | no | A curb beside the crosswalk. |
| e14 | car | ahead | yes | 45.5 | 48.5 | 46.76 | +1.7 | no | Car on your left, approaching. |
| e15 | car | right | yes | 49.5 | 50.5 | 50.24 | +0.3 | no | Car ahead, approaching. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e3 | stroller | right | 7.0 | miss | n/a |  |  |
| e1 | other | right | 10.5 | miss | n/a |  |  |
| e4 | person | left | 12.5 | 9.57-11.66 | +0.8 | no | Person close ahead, approaching. |
| e5 | person | left | 13.5 | 11.72-13.08 | +0.4 | no | Person close ahead. |
| e6 | person | left | 15.0 | miss | n/a |  |  |
| e7 | pole | left | 20.5 | miss | n/a |  |  |
| e8 | person | left | 25.0 | 22.46-24.45 | +0.6 | no | Person close ahead, approaching. |
| e9 | sign | right | 35.5 | miss | n/a |  |  |
| e10 | person | left | 37.0 | miss | n/a |  |  |
| e13 | crosswalk | ahead | 45.0 | miss | n/a |  |  |
| e11 | trash_can | right | 48.5 | 42.81-45.00 | +3.5 | no | Trash can close on your left, approaching. |
| e12 | pole | ahead | 48.5 | miss | n/a |  |  |
| e14 | car | ahead | 48.5 | miss | n/a |  |  |
| e15 | car | right | 50.5 | miss | n/a |  |  |

### london_walking_fused

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | left | yes | 0.0 | 1.5 | 1.61 | -0.1 | yes | Person on your left, approaching. |
| e2 | person | left | yes | 2.0 | 3.0 | 3.74 | -0.7 | no | Person ahead, approaching. |
| e3 | person | left | yes | 3.0 | 4.0 | 3.74 | +0.3 | no | Person ahead, approaching. |
| e4 | person | ahead | yes | 4.5 | 5.0 | miss | n/a |  |  |
| e5 | person | right | no | 5.0 | 5.5 | miss | n/a |  |  |
| e6 | sign | left | yes | 8.5 | 12.0 | 11.84 | +0.2 | yes | A blue sign on a purple structure on the left. |
| e7 | person | right | no | 10.0 | 11.0 | miss | n/a |  |  |
| e8 | person | right | yes | 12.5 | 13.0 | miss | n/a |  |  |
| e9 | person | left | yes | 13.0 | 14.0 | miss | n/a |  |  |
| e10 | sign | left | yes | 14.0 | 16.5 | 15.35 | +1.2 | no | A black sign on a post in the center of the walkway. |
| e11 | other | right | no | 17.0 | 19.5 | miss | n/a |  |  |
| e12 | person | ahead | no | 18.0 | 19.5 | 18.31 | +1.2 | yes | Person ahead, approaching. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e1 | person | left | 1.5 | miss | n/a |  |  |
| e2 | person | left | 3.0 | miss | n/a |  |  |
| e3 | person | left | 4.0 | 1.61-3.68 | +0.3 | yes | Person on your left, approaching. |
| e4 | person | ahead | 5.0 | miss | n/a |  |  |
| e6 | sign | left | 12.0 | miss | n/a |  |  |
| e8 | person | right | 13.0 | miss | n/a |  |  |
| e9 | person | left | 14.0 | miss | n/a |  |  |
| e10 | sign | left | 16.5 | miss | n/a |  |  |

### 197531-905015052_medium_fastonly2

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | bus | right | no | 3.0 | 5.5 | 4.79 | +0.7 | yes | Bus crossing right. |
| e2 | curb | right | no | 0.0 | 2.0 | miss | n/a |  |  |
| e3 | pole | right | no | 0.0 | 8.0 | miss | n/a |  |  |
| e4 | person | ahead | no | 0.0 | 16.0 | miss | n/a |  |  |
| e5 | pole | ahead | no | 0.0 | 16.0 | miss | n/a |  |  |
| e6 | sign | right | no | 0.0 | 3.0 | miss | n/a |  |  |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|

### 3874684_720p_fastonly2

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | truck | left | no | 0.0 | 2.5 | 1.64 | +0.9 | yes | Truck left. |
| e2 | sign | left | no | 0.0 | 1.0 | miss | n/a |  |  |
| e3 | other | left | no | 0.0 | 10.0 | miss | n/a |  |  |
| e4 | other | right | no | 4.0 | 7.5 | miss | n/a |  |  |
| e5 | curb | left | yes | 6.0 | 9.0 | miss | n/a |  |  |
| e6 | pole | right | yes | 12.0 | 15.0 | miss | n/a |  |  |
| e7 | truck | ahead | yes | 14.0 | 19.0 | 17.95 | +1.1 | no | Car left. |
| e8 | curb | ahead | yes | 21.0 | 24.0 | miss | n/a |  |  |
| e9 | crosswalk | ahead | yes | 21.0 | 24.5 | miss | n/a |  |  |
| e10 | pole | right | yes | 22.0 | 25.0 | miss | n/a |  |  |
| e11 | other | right | yes | 24.5 | 26.0 | miss | n/a |  |  |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e5 | curb | left | 9.0 | miss | n/a |  |  |
| e6 | pole | right | 15.0 | miss | n/a |  |  |
| e7 | truck | ahead | 19.0 | 17.95-18.61 | +0.4 | no | Car left. |
| e8 | curb | ahead | 24.0 | miss | n/a |  |  |
| e9 | crosswalk | ahead | 24.5 | miss | n/a |  |  |
| e10 | pole | right | 25.0 | miss | n/a |  |  |
| e11 | other | right | 26.0 | miss | n/a |  |  |

### fifth-avenue-point-of-view-manhattan-nyc-looking-around-day_fastonly2

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | other | right | yes | 2.0 | 10.5 | miss | n/a |  |  |
| e2 | car | left | no | 2.5 | 3.0 | 3.95 | -0.9 | yes | Car left. |
| e3 | stroller | right | yes | 6.0 | 7.0 | miss | n/a |  |  |
| e4 | person | left | yes | 12.0 | 12.5 | 12.58 | -0.1 | no | Person right. |
| e5 | person | left | yes | 13.0 | 13.5 | 13.38 | +0.1 | no | Person ahead. |
| e6 | person | left | yes | 14.0 | 15.0 | 14.23 | +0.8 | no | Person crossing right. |
| e7 | pole | left | yes | 19.0 | 20.5 | 21.08 | -0.6 | yes | Pole left. |
| e8 | person | left | yes | 24.0 | 25.0 | 24.61 | +0.4 | no | Person ahead. |
| e9 | sign | right | yes | 32.5 | 35.5 | miss | n/a |  |  |
| e10 | person | left | yes | 36.0 | 37.0 | 36.55 | +0.4 | no | Person ahead. |
| e11 | trash_can | right | yes | 41.0 | 48.5 | 41.93 | +6.6 | no | Trash can left. |
| e12 | pole | ahead | yes | 43.0 | 48.5 | miss | n/a |  |  |
| e13 | crosswalk | ahead | yes | 42.5 | 45.0 | miss | n/a |  |  |
| e14 | car | ahead | yes | 45.5 | 48.5 | 48.55 | -0.0 | no | Car right. |
| e15 | car | right | yes | 49.5 | 50.5 | miss | n/a |  |  |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e3 | stroller | right | 7.0 | miss | n/a |  |  |
| e1 | other | right | 10.5 | miss | n/a |  |  |
| e4 | person | left | 12.5 | 10.33-11.37 | +1.1 | yes | Person crossing left. |
| e5 | person | left | 13.5 | 11.50-12.29 | +1.2 | yes | Person left. |
| e6 | person | left | 15.0 | 12.58-13.34 | +1.7 | no | Person right. |
| e7 | pole | left | 20.5 | miss | n/a |  |  |
| e8 | person | left | 25.0 | 22.22-23.08 | +1.9 | no | Person right. |
| e9 | sign | right | 35.5 | miss | n/a |  |  |
| e10 | person | left | 37.0 | 34.86-35.77 | +1.2 | no | Person right. |
| e13 | crosswalk | ahead | 45.0 | miss | n/a |  |  |
| e11 | trash_can | right | 48.5 | 41.93-42.85 | +5.7 | no | Trash can left. |
| e12 | pole | ahead | 48.5 | miss | n/a |  |  |
| e14 | car | ahead | 48.5 | miss | n/a |  |  |
| e15 | car | right | 50.5 | 48.55-49.16 | +1.3 | yes | Car right. |

### london_walking_fastonly2

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | left | yes | 0.0 | 1.5 | 0.89 | +0.6 | no | Person ahead. |
| e2 | person | left | yes | 2.0 | 3.0 | miss | n/a |  |  |
| e3 | person | left | yes | 3.0 | 4.0 | 4.11 | -0.1 | no | Person ahead. |
| e4 | person | ahead | yes | 4.5 | 5.0 | miss | n/a |  |  |
| e5 | person | right | no | 5.0 | 5.5 | miss | n/a |  |  |
| e6 | sign | left | yes | 8.5 | 12.0 | miss | n/a |  |  |
| e7 | person | right | no | 10.0 | 11.0 | miss | n/a |  |  |
| e8 | person | right | yes | 12.5 | 13.0 | 12.58 | +0.4 | no | Person left. |
| e9 | person | left | yes | 13.0 | 14.0 | 13.35 | +0.7 | no | Person ahead. |
| e10 | sign | left | yes | 14.0 | 16.5 | miss | n/a |  |  |
| e11 | other | right | no | 17.0 | 19.5 | miss | n/a |  |  |
| e12 | person | ahead | no | 18.0 | 19.5 | 18.11 | +1.4 | yes | Person ahead. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e1 | person | left | 1.5 | miss | n/a |  |  |
| e2 | person | left | 3.0 | 0.89-1.64 | +1.4 | no | Person ahead. |
| e3 | person | left | 4.0 | 1.67-2.38 | +1.6 | yes | Person left. |
| e4 | person | ahead | 5.0 | 4.11-4.94 | +0.1 | yes | Person ahead. |
| e6 | sign | left | 12.0 | miss | n/a |  |  |
| e8 | person | right | 13.0 | miss | n/a |  |  |
| e9 | person | left | 14.0 | 12.58-13.31 | +0.7 | yes | Person left. |
| e10 | sign | left | 16.5 | miss | n/a |  |  |
