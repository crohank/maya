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
| 197531-905015052_medium_describe_mem2 | 197531-905015052_medium | 4 | 14.6 | n/a (0 events) | 2/6 (33%) | n/a | n/a | +7.2 | 0/2 (0%) | 1 (0) |
| 3874684_720p_describe_mem2 | 3874684_720p | 7 | 16.3 | 2/7 (29%) | 2/11 (18%) | -0.6 | -1.0 | -0.6 | 1/2 (50%) | 5 (3) |
| fifth-avenue-point-of-view-manhattan-nyc-looking-around-day_describe_mem2 | fifth-avenue-point-of-view-manhattan-nyc-looking-around-day | 7 | 7.8 | 1/14 (7%) | 1/15 (7%) | -0.3 | -0.3 | -0.3 | 1/1 (100%) | 6 (0) |
| london_walking_describe_mem2 | london_walking | 2 | 6.1 | 1/8 (12%) | 2/12 (17%) | +0.4 | +0.4 | +0.0 | 0/2 (0%) | 0 (0) |
| TOTAL describe (4 clips) | all | 47 | 24.3 | 10/29 (34%) | 14/44 (32%) | -0.3 | -0.9 | -0.3 | 7/14 (50%) | 33 (7) |
| TOTAL describe_mem2 (4 clips) | all | 20 | 10.4 | 4/29 (14%) | 7/44 (16%) | -0.2 | -1.0 | -0.1 | 2/7 (29%) | 12 (3) |
| TOTAL instruct (4 clips) | all | 45 | 23.3 | 11/29 (38%) | 17/44 (39%) | +0.1 | -0.8 | +0.3 | 10/17 (59%) | 27 (5) |

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

### 197531-905015052_medium_instruct

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | bus | right | no | 3.0 | 5.5 | 5.93 | -0.4 | yes | Move right, bus on right side |
| e2 | curb | right | no | 0.0 | 2.0 | miss | n/a |  |  |
| e3 | pole | right | no | 0.0 | 8.0 | miss | n/a |  |  |
| e4 | person | ahead | no | 0.0 | 16.0 | 3.19 | +12.8 | yes | Move right, pedestrian ahead on right. |
| e5 | pole | ahead | no | 0.0 | 16.0 | miss | n/a |  |  |
| e6 | sign | right | no | 0.0 | 3.0 | miss | n/a |  |  |

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

### 197531-905015052_medium_describe_mem2

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | bus | right | no | 3.0 | 5.5 | 4.34 | +1.2 | no | Bus approaching from behind. |
| e2 | curb | right | no | 0.0 | 2.0 | miss | n/a |  |  |
| e3 | pole | right | no | 0.0 | 8.0 | miss | n/a |  |  |
| e4 | person | ahead | no | 0.0 | 16.0 | 2.75 | +13.3 | no | Person walking toward you. |
| e5 | pole | ahead | no | 0.0 | 16.0 | miss | n/a |  |  |
| e6 | sign | right | no | 0.0 | 3.0 | miss | n/a |  |  |

### 3874684_720p_describe_mem2

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | truck | left | no | 0.0 | 2.5 | miss | n/a |  |  |
| e2 | sign | left | no | 0.0 | 1.0 | miss | n/a |  |  |
| e3 | other | left | no | 0.0 | 10.0 | miss | n/a |  |  |
| e4 | other | right | no | 4.0 | 7.5 | miss | n/a |  |  |
| e5 | curb | left | yes | 6.0 | 9.0 | miss | n/a |  |  |
| e6 | pole | right | yes | 12.0 | 15.0 | miss | n/a |  |  |
| e7 | truck | ahead | yes | 14.0 | 19.0 | 19.97 | -1.0 | no | Vehicle approaching from behind. |
| e8 | curb | ahead | yes | 21.0 | 24.0 | miss | n/a |  |  |
| e9 | crosswalk | ahead | yes | 21.0 | 24.5 | miss | n/a |  |  |
| e10 | pole | right | yes | 22.0 | 25.0 | 25.13 | -0.1 | yes | Pole on the right, moving closer. |
| e11 | other | right | yes | 24.5 | 26.0 | miss | n/a |  |  |

### fifth-avenue-point-of-view-manhattan-nyc-looking-around-day_describe_mem2

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | other | right | yes | 2.0 | 10.5 | miss | n/a |  |  |
| e2 | car | left | no | 2.5 | 3.0 | miss | n/a |  |  |
| e3 | stroller | right | yes | 6.0 | 7.0 | miss | n/a |  |  |
| e4 | person | left | yes | 12.0 | 12.5 | miss | n/a |  |  |
| e5 | person | left | yes | 13.0 | 13.5 | miss | n/a |  |  |
| e6 | person | left | yes | 14.0 | 15.0 | 15.29 | -0.3 | yes | Person walking toward you, slightly left. |
| e7 | pole | left | yes | 19.0 | 20.5 | miss | n/a |  |  |
| e8 | person | left | yes | 24.0 | 25.0 | miss | n/a |  |  |
| e9 | sign | right | yes | 32.5 | 35.5 | miss | n/a |  |  |
| e10 | person | left | yes | 36.0 | 37.0 | miss | n/a |  |  |
| e11 | trash_can | right | yes | 41.0 | 48.5 | miss | n/a |  |  |
| e12 | pole | ahead | yes | 43.0 | 48.5 | miss | n/a |  |  |
| e13 | crosswalk | ahead | yes | 42.5 | 45.0 | miss | n/a |  |  |
| e14 | car | ahead | yes | 45.5 | 48.5 | miss | n/a |  |  |
| e15 | car | right | yes | 49.5 | 50.5 | miss | n/a |  |  |

### london_walking_describe_mem2

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | left | yes | 0.0 | 1.5 | miss | n/a |  |  |
| e2 | person | left | yes | 2.0 | 3.0 | 2.59 | +0.4 | no | Person walking away from you. |
| e3 | person | left | yes | 3.0 | 4.0 | miss | n/a |  |  |
| e4 | person | ahead | yes | 4.5 | 5.0 | miss | n/a |  |  |
| e5 | person | right | no | 5.0 | 5.5 | miss | n/a |  |  |
| e6 | sign | left | yes | 8.5 | 12.0 | miss | n/a |  |  |
| e7 | person | right | no | 10.0 | 11.0 | miss | n/a |  |  |
| e8 | person | right | yes | 12.5 | 13.0 | miss | n/a |  |  |
| e9 | person | left | yes | 13.0 | 14.0 | miss | n/a |  |  |
| e10 | sign | left | yes | 14.0 | 16.5 | miss | n/a |  |  |
| e11 | other | right | no | 17.0 | 19.5 | miss | n/a |  |  |
| e12 | person | ahead | no | 18.0 | 19.5 | 19.89 | -0.4 | no | Person walking toward you, slightly left. |

## Skipped logs

- results/live/fifth-avenue-point-of-view-manhattan-nyc-looking-around-day_guide/log.csv: no status column (older harness)
