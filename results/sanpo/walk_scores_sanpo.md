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
| sanpo_7X41_wkj_0000_fastonly2 | sanpo_7X41_wkj_0000 | 16 | 32.9 | 3/4 (75%) | 3/8 (38%) | +1.6 | +1.0 | +1.6 | 1/3 (33%) | 11 (2) |
| sanpo_8WF0e5NO_0195_fastonly2 | sanpo_8WF0e5NO_0195 | 4 | 10.4 | 1/2 (50%) | 1/2 (50%) | +1.4 | +1.4 | +1.4 | 1/1 (100%) | 3 (0) |
| sanpo_RqOwmltc_0000_fastonly2 | sanpo_RqOwmltc_0000 | 24 | 48.3 | 8/8 (100%) | 27/28 (96%) | +2.0 | +0.8 | +1.7 | 12/27 (44%) | 3 (0) |
| sanpo_UGNwBEZM_0353_fastonly2 | sanpo_UGNwBEZM_0353 | 11 | 22.5 | 5/6 (83%) | 7/9 (78%) | +1.3 | -0.9 | +1.6 | 6/7 (86%) | 2 (0) |
| sanpo_cBVSUvSN_0000_fastonly2 | sanpo_cBVSUvSN_0000 | 25 | 50.2 | 6/7 (86%) | 15/17 (88%) | +2.2 | +0.6 | +2.1 | 5/15 (33%) | 9 (4) |
| sanpo_eHxtA669_0000_fastonly2 | sanpo_eHxtA669_0000 | 11 | 22.6 | 3/3 (100%) | 7/7 (100%) | +1.9 | +0.1 | +1.6 | 2/7 (29%) | 3 (0) |
| sanpo_qFDP9gJD_0000_fastonly2 | sanpo_qFDP9gJD_0000 | 18 | 38.0 | n/a (0 events) | 1/1 (100%) | n/a | n/a | +2.3 | 0/1 (0%) | 16 (0) |
| sanpo_qn1eNtR0_0029_fastonly2 | sanpo_qn1eNtR0_0029 | 12 | 24.8 | 3/3 (100%) | 3/6 (50%) | +1.9 | +1.4 | +1.9 | 2/3 (67%) | 8 (3) |
| sanpo_qttyxdua_0000_fastonly2 | sanpo_qttyxdua_0000 | 10 | 22.8 | n/a (0 events) | n/a (0 events) | n/a | n/a | n/a | n/a (no hits) | 10 (0) |
| sanpo_wXwTZnJH_0007_fastonly2 | sanpo_wXwTZnJH_0007 | 11 | 25.9 | n/a (0 events) | 3/3 (100%) | n/a | n/a | +0.1 | 2/3 (67%) | 6 (0) |
| sanpo_x5OCPnbr_0078_fastonly2 | sanpo_x5OCPnbr_0078 | 20 | 41.7 | n/a (0 events) | 2/3 (67%) | n/a | n/a | +2.1 | 2/2 (100%) | 16 (0) |
| TOTAL fastonly2 (11 clips) | all | 162 | 31.5 | 29/33 (88%) | 69/84 (82%) | +1.8 | -0.9 | +1.8 | 33/69 (48%) | 87 (9) |

## Strict

must_warn events only. On time: names the class and the speech ends by t_close; one utterance credits one event. Spare: seconds between speech end and t_close. Warn precision: share of all spoken utterances that name a must_warn event near its time. Rules in the scripts/score_walk.py docstring.

| run | on time | on time, side right | spare median (s) | warn precision | utt/min |
|---|---|---|---|---|---|
| sanpo_7X41_wkj_0000_fastonly2 | 3/4 (75%) | 1/4 (25%) | +1.2 | 6/16 (38%) | 32.9 |
| sanpo_8WF0e5NO_0195_fastonly2 | 2/2 (100%) | 2/2 (100%) | +1.3 | 2/4 (50%) | 10.4 |
| sanpo_RqOwmltc_0000_fastonly2 | 8/8 (100%) | 2/8 (25%) | +1.7 | 18/24 (75%) | 48.3 |
| sanpo_UGNwBEZM_0353_fastonly2 | 4/6 (67%) | 3/6 (50%) | +0.8 | 9/11 (82%) | 22.5 |
| sanpo_cBVSUvSN_0000_fastonly2 | 5/7 (71%) | 1/7 (14%) | +1.3 | 12/25 (48%) | 50.2 |
| sanpo_eHxtA669_0000_fastonly2 | 3/3 (100%) | 1/3 (33%) | +1.4 | 7/11 (64%) | 22.6 |
| sanpo_qFDP9gJD_0000_fastonly2 | n/a (0 events) | n/a (0 events) | n/a | 0/18 (0%) | 38.0 |
| sanpo_qn1eNtR0_0029_fastonly2 | 3/3 (100%) | 2/3 (67%) | +1.1 | 4/12 (33%) | 24.8 |
| sanpo_qttyxdua_0000_fastonly2 | n/a (0 events) | n/a (0 events) | n/a | 0/10 (0%) | 22.8 |
| sanpo_wXwTZnJH_0007_fastonly2 | n/a (0 events) | n/a (0 events) | n/a | 0/11 (0%) | 25.9 |
| sanpo_x5OCPnbr_0078_fastonly2 | n/a (0 events) | n/a (0 events) | n/a | 0/20 (0%) | 41.7 |
| TOTAL fastonly2 (11 clips) | 28/33 (85%) | 12/33 (36%) | +1.4 | 58/162 (36%) | 31.5 |

## Per-event detail

### sanpo_7X41_wkj_0000_fastonly2

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | left | yes | 5.1 | 7.6 | 5.30 | +2.3 | no | Person crossing right. |
| e2 | person | left | yes | 6.2 | 8.7 | 7.11 | +1.6 | no | Person right. |
| e3 | person | left | no | 8.0 | 10.5 | miss | n/a |  |  |
| e4 | car | left | no | 8.6 | 11.1 | miss | n/a |  |  |
| e5 | person | left | no | 8.6 | 11.1 | miss | n/a |  |  |
| e6 | car | ahead | no | 11.6 | 12.5 | miss | n/a |  |  |
| e7 | person | left | yes | 14.3 | 14.9 | miss | n/a |  |  |
| e8 | person | left | yes | 14.6 | 17.1 | 16.07 | +1.0 | yes | Person crossing left. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e1 | person | left | 7.6 | 5.30-6.40 | +1.2 | no | Person crossing right. |
| e2 | person | left | 8.7 | 7.11-7.86 | +0.8 | no | Person right. |
| e7 | person | left | 14.9 | 12.13-13.28 | +1.7 | yes | Person crossing left. |
| e8 | person | left | 17.1 | miss | n/a |  |  |

### sanpo_8WF0e5NO_0195_fastonly2

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | right | yes | 3.4 | 5.9 | miss | n/a |  |  |
| e2 | person | left | yes | 22.0 | 24.5 | 23.17 | +1.4 | yes | Person left. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e1 | person | right | 5.9 | 3.17-3.94 | +1.9 | yes | Person right. |
| e2 | person | left | 24.5 | 23.17-23.86 | +0.7 | yes | Person left. |

### sanpo_RqOwmltc_0000_fastonly2

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | right | no | 4.6 | 6.4 | 5.04 | +1.4 | no | Person crossing ahead. |
| e2 | person | right | no | 5.5 | 8.0 | 6.29 | +1.7 | yes | Person crossing right. |
| e3 | person | right | no | 5.6 | 8.1 | 6.29 | +1.8 | yes | Person crossing right. |
| e4 | person | right | no | 5.7 | 8.2 | 6.29 | +1.9 | yes | Person crossing right. |
| e5 | person | right | no | 5.7 | 8.2 | 6.29 | +1.9 | yes | Person crossing right. |
| e6 | person | right | yes | 6.4 | 8.9 | 7.45 | +1.5 | no | Person ahead. |
| e7 | person | right | yes | 7.5 | 10.0 | 8.33 | +1.7 | no | Person crossing left. |
| e8 | person | left | no | 8.9 | 11.4 | 9.56 | +1.8 | yes | Person left. |
| e9 | person | right | no | 10.7 | 13.2 | 11.10 | +2.1 | yes | Person right. |
| e10 | person | right | no | 10.8 | 13.3 | 11.10 | +2.2 | yes | Person right. |
| e11 | person | right | yes | 11.7 | 14.2 | 12.23 | +2.0 | no | Person ahead. |
| e12 | person | right | no | 14.1 | 14.5 | 14.44 | +0.0 | no | Person ahead. |
| e13 | person | right | yes | 14.4 | 16.9 | 14.44 | +2.5 | no | Person ahead. |
| e14 | car | left | no | 16.1 | 18.6 | miss | n/a |  |  |
| e15 | person | left | yes | 18.3 | 20.8 | 18.86 | +1.9 | no | Person ahead. |
| e16 | person | right | yes | 19.3 | 21.8 | 19.65 | +2.2 | no | Person left. |
| e17 | person | left | yes | 19.4 | 21.9 | 19.65 | +2.3 | yes | Person left. |
| e18 | person | ahead | no | 20.3 | 22.8 | 20.60 | +2.2 | no | Person right. |
| e19 | person | right | no | 21.2 | 23.7 | 21.35 | +2.3 | yes | Person crossing right. |
| e20 | person | right | no | 23.1 | 25.6 | 25.11 | +0.5 | no | Person crossing left. |
| e21 | person | right | no | 25.5 | 25.9 | 26.31 | -0.4 | yes | Person right. |
| e22 | person | right | yes | 23.4 | 25.9 | 25.11 | +0.8 | no | Person crossing left. |
| e23 | person | right | no | 23.9 | 26.4 | 25.11 | +1.3 | no | Person crossing left. |
| e24 | person | right | no | 25.4 | 27.9 | 26.31 | +1.6 | yes | Person right. |
| e25 | person | left | no | 27.0 | 29.5 | 28.75 | +0.8 | yes | Person left. |
| e26 | person | right | no | 27.8 | 29.7 | 28.75 | +0.9 | no | Person left. |
| e27 | person | ahead | no | 28.2 | 29.7 | 28.75 | +1.0 | no | Person left. |
| e28 | person | ahead | no | 27.4 | 29.9 | 28.75 | +1.2 | no | Person left. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e6 | person | right | 8.9 | 6.29-7.40 | +1.5 | yes | Person crossing right. |
| e7 | person | right | 10.0 | 7.45-8.27 | +1.7 | no | Person ahead. |
| e11 | person | right | 14.2 | 12.23-12.95 | +1.2 | no | Person ahead. |
| e13 | person | right | 16.9 | 14.44-15.30 | +1.6 | no | Person ahead. |
| e15 | person | left | 20.8 | 18.04-18.82 | +2.0 | no | Person right. |
| e16 | person | right | 21.8 | 18.86-19.59 | +2.2 | no | Person ahead. |
| e17 | person | left | 21.9 | 19.65-20.56 | +1.4 | yes | Person left. |
| e22 | person | right | 25.9 | 23.08-23.96 | +2.0 | no | Person left. |

### sanpo_UGNwBEZM_0353_fastonly2

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | left | yes | 0.0 | 2.3 | 0.96 | +1.3 | yes | Person left. |
| e2 | person | ahead | no | 5.9 | 8.4 | 6.76 | +1.6 | yes | Person ahead. |
| e3 | person | left | yes | 6.8 | 9.3 | 7.58 | +1.8 | no | Person right. |
| e4 | person | left | yes | 10.2 | 12.7 | 13.55 | -0.9 | yes | Person left. |
| e5 | person | left | yes | 16.5 | 17.7 | 17.50 | +0.2 | yes | Person left. |
| e6 | person | left | yes | 16.8 | 19.3 | 17.50 | +1.8 | yes | Person left. |
| e7 | person | left | yes | 18.2 | 20.7 | miss | n/a |  |  |
| e8 | person | right | no | 26.4 | 28.9 | 26.89 | +2.0 | yes | Person crossing right. |
| e9 | person | right | no | 27.4 | 29.9 | miss | n/a |  |  |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e1 | person | left | 2.3 | 0.96-1.69 | +0.6 | yes | Person left. |
| e3 | person | left | 9.3 | 6.76-7.54 | +1.8 | no | Person ahead. |
| e4 | person | left | 12.7 | miss | n/a |  |  |
| e5 | person | left | 17.7 | 16.27-17.46 | +0.3 | yes | Person crossing left. |
| e6 | person | left | 19.3 | 17.50-18.25 | +1.1 | yes | Person left. |
| e7 | person | left | 20.7 | miss | n/a |  |  |

### sanpo_cBVSUvSN_0000_fastonly2

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | right | no | 0.0 | 0.0 | miss | n/a |  |  |
| e2 | person | left | yes | 0.6 | 3.1 | 2.51 | +0.6 | no | Person ahead. |
| e3 | person | right | no | 1.0 | 3.5 | 2.51 | +1.0 | no | Person ahead. |
| e4 | person | left | yes | 5.0 | 7.5 | miss | n/a |  |  |
| e5 | person | ahead | no | 11.0 | 13.5 | 11.24 | +2.2 | no | Person left. |
| e6 | person | left | yes | 14.7 | 17.2 | 15.72 | +1.5 | yes | Person crossing left. |
| e7 | person | ahead | no | 16.2 | 18.7 | 16.80 | +1.9 | no | Person left. |
| e8 | person | ahead | no | 17.2 | 19.7 | 18.27 | +1.5 | no | Person left. |
| e9 | person | left | yes | 22.6 | 25.1 | 22.80 | +2.3 | no | Person crossing right. |
| e10 | person | left | no | 23.6 | 26.1 | 24.22 | +1.9 | yes | Person left. |
| e11 | person | left | yes | 23.8 | 26.3 | 24.22 | +2.1 | yes | Person left. |
| e12 | person | right | no | 26.7 | 26.9 | 27.57 | -0.6 | yes | Person crossing right. |
| e13 | person | left | yes | 25.0 | 27.5 | 24.98 | +2.5 | no | Person ahead. |
| e14 | person | left | no | 27.4 | 29.9 | 27.57 | +2.3 | no | Person crossing right. |
| e15 | person | right | no | 27.4 | 29.9 | 27.57 | +2.3 | yes | Person crossing right. |
| e16 | person | ahead | no | 27.4 | 29.9 | 27.57 | +2.3 | no | Person crossing right. |
| e17 | person | ahead | yes | 27.4 | 29.9 | 27.57 | +2.3 | no | Person crossing right. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e2 | person | left | 3.1 | miss | n/a |  |  |
| e4 | person | left | 7.5 | miss | n/a |  |  |
| e6 | person | left | 17.2 | 14.52-15.67 | +1.5 | no | Person crossing ahead. |
| e9 | person | left | 25.1 | 22.80-23.92 | +1.1 | no | Person crossing right. |
| e11 | person | left | 26.3 | 24.22-24.94 | +1.3 | yes | Person left. |
| e13 | person | left | 27.5 | 24.98-25.76 | +1.7 | no | Person ahead. |
| e17 | person | ahead | 29.9 | 27.57-28.67 | +1.2 | no | Person crossing right. |

### sanpo_eHxtA669_0000_fastonly2

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | left | no | 0.0 | 0.1 | 0.93 | -0.8 | no | Person right. |
| e2 | person | left | no | 0.0 | 0.5 | 0.93 | -0.4 | no | Person right. |
| e3 | person | left | yes | 0.6 | 3.1 | 0.93 | +2.1 | no | Person right. |
| e4 | person | right | yes | 19.2 | 21.7 | 21.63 | +0.1 | yes | Person crossing right. |
| e5 | person | left | yes | 22.3 | 24.8 | 22.86 | +1.9 | yes | Person left. |
| e6 | person | right | no | 24.6 | 27.1 | 25.45 | +1.6 | no | Person left. |
| e7 | person | right | no | 24.8 | 27.3 | 25.45 | +1.9 | no | Person left. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e3 | person | left | 3.1 | 0.93-1.68 | +1.4 | no | Person right. |
| e4 | person | right | 21.7 | 18.81-19.62 | +2.1 | no | Person left. |
| e5 | person | left | 24.8 | 22.86-23.63 | +1.2 | yes | Person left. |

### sanpo_qFDP9gJD_0000_fastonly2

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | car | left | no | 1.6 | 4.1 | 1.84 | +2.3 | no | Bus crossing ahead. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|

### sanpo_qn1eNtR0_0029_fastonly2

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | car | right | no | 1.1 | 3.6 | miss | n/a |  |  |
| e2 | person | left | yes | 11.9 | 13.9 | 12.02 | +1.9 | yes | Person left. |
| e3 | car | right | no | 16.4 | 17.5 | miss | n/a |  |  |
| e4 | car | right | no | 17.7 | 19.7 | miss | n/a |  |  |
| e5 | person | right | yes | 21.6 | 24.1 | 21.82 | +2.3 | no | Person ahead. |
| e6 | person | left | yes | 22.3 | 24.8 | 23.42 | +1.4 | yes | Person left. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e2 | person | left | 13.9 | 12.02-12.72 | +1.1 | yes | Person left. |
| e5 | person | right | 24.1 | 21.82-22.62 | +1.5 | no | Person ahead. |
| e6 | person | left | 24.8 | 23.42-24.15 | +0.6 | yes | Person left. |

### sanpo_qttyxdua_0000_fastonly2

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|

### sanpo_wXwTZnJH_0007_fastonly2

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | car | right | no | 1.8 | 4.3 | 2.67 | +1.6 | yes | Car right. |
| e2 | car | right | no | 10.4 | 12.9 | 13.65 | -0.7 | yes | Car right. |
| e3 | person | left | no | 22.2 | 24.7 | 24.52 | +0.1 | no | Person right. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|

### sanpo_x5OCPnbr_0078_fastonly2

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | car | right | no | 12.0 | 14.5 | 12.29 | +2.2 | yes | Truck crossing right. |
| e2 | person | left | no | 15.8 | 18.3 | 16.25 | +2.0 | yes | Person left. |
| e3 | car | right | no | 18.3 | 19.1 | miss | n/a |  |  |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
