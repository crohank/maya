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
| sanpo_7X41_wkj_0000_fastonly2 | sanpo_7X41_wkj_0000 | 16 | 32.9 | 3/4 (75%) | 5/8 (62%) | +3.1 | +1.0 | +3.4 | 1/5 (20%) | 10 (2) |
| sanpo_8WF0e5NO_0195_fastonly2 | sanpo_8WF0e5NO_0195 | 4 | 10.4 | 2/2 (100%) | 2/2 (100%) | +2.0 | +1.4 | +2.0 | 2/2 (100%) | 2 (0) |
| sanpo_RqOwmltc_0000_fastonly2 | sanpo_RqOwmltc_0000 | 24 | 48.3 | 8/8 (100%) | 27/28 (96%) | +3.0 | +2.6 | +2.8 | 11/27 (41%) | 2 (0) |
| sanpo_UGNwBEZM_0353_fastonly2 | sanpo_UGNwBEZM_0353 | 11 | 22.5 | 6/6 (100%) | 9/9 (100%) | +2.8 | +0.2 | +2.6 | 8/9 (89%) | 1 (0) |
| sanpo_cBVSUvSN_0000_fastonly2 | sanpo_cBVSUvSN_0000 | 25 | 50.2 | 6/7 (86%) | 15/17 (88%) | +3.3 | +0.6 | +3.1 | 6/15 (40%) | 6 (4) |
| sanpo_eHxtA669_0000_fastonly2 | sanpo_eHxtA669_0000 | 11 | 22.6 | 3/3 (100%) | 7/7 (100%) | +2.9 | +2.1 | +2.5 | 2/7 (29%) | 2 (0) |
| sanpo_qFDP9gJD_0000_fastonly2 | sanpo_qFDP9gJD_0000 | 18 | 38.0 | n/a (0 events) | 1/1 (100%) | n/a | n/a | +3.0 | 0/1 (0%) | 15 (0) |
| sanpo_qn1eNtR0_0029_fastonly2 | sanpo_qn1eNtR0_0029 | 12 | 24.8 | 3/3 (100%) | 3/6 (50%) | +3.0 | +1.9 | +3.0 | 1/3 (33%) | 7 (3) |
| sanpo_qttyxdua_0000_fastonly2 | sanpo_qttyxdua_0000 | 10 | 22.8 | n/a (0 events) | n/a (0 events) | n/a | n/a | n/a | n/a (no hits) | 10 (0) |
| sanpo_wXwTZnJH_0007_fastonly2 | sanpo_wXwTZnJH_0007 | 11 | 25.9 | n/a (0 events) | 3/3 (100%) | n/a | n/a | +0.1 | 2/3 (67%) | 6 (0) |
| sanpo_x5OCPnbr_0078_fastonly2 | sanpo_x5OCPnbr_0078 | 20 | 41.7 | n/a (0 events) | 2/3 (67%) | n/a | n/a | +2.1 | 2/2 (100%) | 16 (0) |
| TOTAL fastonly2 (11 clips) | all | 162 | 31.5 | 31/33 (94%) | 74/84 (88%) | +3.1 | +0.2 | +2.8 | 35/74 (47%) | 77 (9) |

## Strict

must_warn events only. On time: names the class and the speech ends by t_close; one utterance credits one event. Spare: seconds between speech end and t_close. Warn precision: share of all spoken utterances that name a must_warn event near its time. Rules in the scripts/score_walk.py docstring.

| run | on time | on time, side right | spare median (s) | warn precision | utt/min |
|---|---|---|---|---|---|
| sanpo_7X41_wkj_0000_fastonly2 | 3/4 (75%) | 1/4 (25%) | +2.3 | 7/16 (44%) | 32.9 |
| sanpo_8WF0e5NO_0195_fastonly2 | 2/2 (100%) | 1/2 (50%) | +2.0 | 3/4 (75%) | 10.4 |
| sanpo_RqOwmltc_0000_fastonly2 | 8/8 (100%) | 5/8 (62%) | +2.6 | 20/24 (83%) | 48.3 |
| sanpo_UGNwBEZM_0353_fastonly2 | 5/6 (83%) | 4/6 (67%) | +1.1 | 9/11 (82%) | 22.5 |
| sanpo_cBVSUvSN_0000_fastonly2 | 5/7 (71%) | 2/7 (29%) | +2.5 | 14/25 (56%) | 50.2 |
| sanpo_eHxtA669_0000_fastonly2 | 3/3 (100%) | 0/3 (0%) | +2.0 | 7/11 (64%) | 22.6 |
| sanpo_qFDP9gJD_0000_fastonly2 | n/a (0 events) | n/a (0 events) | n/a | 0/18 (0%) | 38.0 |
| sanpo_qn1eNtR0_0029_fastonly2 | 3/3 (100%) | 1/3 (33%) | +2.2 | 5/12 (42%) | 24.8 |
| sanpo_qttyxdua_0000_fastonly2 | n/a (0 events) | n/a (0 events) | n/a | 0/10 (0%) | 22.8 |
| sanpo_wXwTZnJH_0007_fastonly2 | n/a (0 events) | n/a (0 events) | n/a | 0/11 (0%) | 25.9 |
| sanpo_x5OCPnbr_0078_fastonly2 | n/a (0 events) | n/a (0 events) | n/a | 0/20 (0%) | 41.7 |
| TOTAL fastonly2 (11 clips) | 29/33 (88%) | 14/33 (42%) | +2.3 | 65/162 (40%) | 31.5 |

## Per-event detail

### sanpo_7X41_wkj_0000_fastonly2

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | left | yes | 3.6 | 7.6 | 4.47 | +3.1 | no | Person ahead. |
| e2 | person | left | yes | 4.7 | 8.7 | 5.30 | +3.4 | no | Person crossing right. |
| e3 | person | left | no | 6.5 | 10.5 | 7.11 | +3.4 | no | Person right. |
| e4 | car | left | no | 7.1 | 11.1 | miss | n/a |  |  |
| e5 | person | left | no | 7.1 | 11.1 | 7.11 | +4.0 | no | Person right. |
| e6 | car | ahead | no | 11.6 | 12.5 | miss | n/a |  |  |
| e7 | person | left | yes | 14.3 | 14.9 | miss | n/a |  |  |
| e8 | person | left | yes | 13.1 | 17.1 | 16.07 | +1.0 | yes | Person crossing left. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e1 | person | left | 7.6 | 4.47-5.20 | +2.4 | no | Person ahead. |
| e2 | person | left | 8.7 | 5.30-6.40 | +2.3 | no | Person crossing right. |
| e7 | person | left | 14.9 | 12.13-13.28 | +1.7 | yes | Person crossing left. |
| e8 | person | left | 17.1 | miss | n/a |  |  |

### sanpo_8WF0e5NO_0195_fastonly2

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | right | yes | 1.9 | 5.9 | 3.17 | +2.7 | yes | Person right. |
| e2 | person | left | yes | 20.5 | 24.5 | 23.17 | +1.4 | yes | Person left. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e1 | person | right | 5.9 | 1.83-2.49 | +3.4 | no | Person ahead. |
| e2 | person | left | 24.5 | 23.17-23.86 | +0.7 | yes | Person left. |

### sanpo_RqOwmltc_0000_fastonly2

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | right | no | 4.6 | 6.4 | 5.04 | +1.4 | no | Person crossing ahead. |
| e2 | person | right | no | 5.1 | 8.0 | 6.29 | +1.7 | yes | Person crossing right. |
| e3 | person | right | no | 4.5 | 8.1 | 5.04 | +3.0 | no | Person crossing ahead. |
| e4 | person | right | no | 5.2 | 8.2 | 6.29 | +1.9 | yes | Person crossing right. |
| e5 | person | right | no | 5.4 | 8.2 | 6.29 | +1.9 | yes | Person crossing right. |
| e6 | person | right | yes | 5.3 | 8.9 | 6.29 | +2.6 | yes | Person crossing right. |
| e7 | person | right | yes | 6.3 | 10.0 | 7.45 | +2.6 | no | Person ahead. |
| e8 | person | left | no | 8.9 | 11.4 | 9.56 | +1.8 | yes | Person left. |
| e9 | person | right | no | 9.2 | 13.2 | 9.56 | +3.6 | no | Person left. |
| e10 | person | right | no | 9.3 | 13.3 | 9.56 | +3.7 | no | Person left. |
| e11 | person | right | yes | 10.2 | 14.2 | 11.10 | +3.1 | yes | Person right. |
| e12 | person | right | no | 14.1 | 14.5 | 14.44 | +0.0 | no | Person ahead. |
| e13 | person | right | yes | 13.5 | 16.9 | 13.71 | +3.2 | yes | Person right. |
| e14 | car | left | no | 14.6 | 18.6 | miss | n/a |  |  |
| e15 | person | left | yes | 16.8 | 20.8 | 18.04 | +2.8 | no | Person right. |
| e16 | person | right | yes | 17.8 | 21.8 | 18.04 | +3.8 | yes | Person right. |
| e17 | person | left | yes | 18.3 | 21.9 | 18.86 | +3.1 | no | Person ahead. |
| e18 | person | ahead | no | 18.8 | 22.8 | 18.86 | +3.9 | yes | Person ahead. |
| e19 | person | right | no | 19.7 | 23.7 | 20.60 | +3.1 | yes | Person right. |
| e20 | person | right | no | 21.8 | 25.6 | 23.08 | +2.5 | no | Person left. |
| e21 | person | right | no | 25.5 | 25.9 | 26.31 | -0.4 | yes | Person right. |
| e22 | person | right | yes | 21.9 | 25.9 | 23.08 | +2.8 | no | Person left. |
| e23 | person | right | no | 22.4 | 26.4 | 23.08 | +3.3 | no | Person left. |
| e24 | person | right | no | 23.9 | 27.9 | 25.11 | +2.8 | no | Person crossing left. |
| e25 | person | left | no | 25.5 | 29.5 | 26.31 | +3.2 | no | Person right. |
| e26 | person | right | no | 27.8 | 29.7 | 28.75 | +0.9 | no | Person left. |
| e27 | person | ahead | no | 28.2 | 29.7 | 28.75 | +1.0 | no | Person left. |
| e28 | person | ahead | no | 25.9 | 29.9 | 26.31 | +3.6 | no | Person right. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e6 | person | right | 8.9 | 5.04-6.23 | +2.7 | no | Person crossing ahead. |
| e7 | person | right | 10.0 | 6.29-7.40 | +2.6 | yes | Person crossing right. |
| e11 | person | right | 14.2 | 11.10-11.83 | +2.4 | yes | Person right. |
| e13 | person | right | 16.9 | 13.71-14.39 | +2.5 | yes | Person right. |
| e15 | person | left | 20.8 | 16.69-17.99 | +2.8 | yes | Person crossing left. |
| e16 | person | right | 21.8 | 18.04-18.82 | +3.0 | yes | Person right. |
| e17 | person | left | 21.9 | 18.86-19.59 | +2.3 | no | Person ahead. |
| e22 | person | right | 25.9 | 23.08-23.96 | +2.0 | no | Person left. |

### sanpo_UGNwBEZM_0353_fastonly2

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | left | yes | 0.0 | 2.3 | 0.96 | +1.3 | yes | Person left. |
| e2 | person | ahead | no | 4.4 | 8.4 | 6.76 | +1.6 | yes | Person ahead. |
| e3 | person | left | yes | 5.3 | 9.3 | 6.76 | +2.6 | no | Person ahead. |
| e4 | person | left | yes | 8.9 | 12.7 | 9.13 | +3.5 | yes | Person left. |
| e5 | person | left | yes | 16.5 | 17.7 | 17.50 | +0.2 | yes | Person left. |
| e6 | person | left | yes | 15.3 | 19.3 | 16.27 | +3.1 | yes | Person crossing left. |
| e7 | person | left | yes | 17.5 | 20.7 | 17.50 | +3.2 | yes | Person left. |
| e8 | person | right | no | 24.9 | 28.9 | 26.89 | +2.0 | yes | Person crossing right. |
| e9 | person | right | no | 25.9 | 29.9 | 26.89 | +3.0 | yes | Person crossing right. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e1 | person | left | 2.3 | 0.96-1.69 | +0.6 | yes | Person left. |
| e3 | person | left | 9.3 | 6.76-7.54 | +1.8 | no | Person ahead. |
| e4 | person | left | 12.7 | 9.13-9.90 | +2.8 | yes | Person left. |
| e5 | person | left | 17.7 | 16.27-17.46 | +0.3 | yes | Person crossing left. |
| e6 | person | left | 19.3 | 17.50-18.25 | +1.1 | yes | Person left. |
| e7 | person | left | 20.7 | miss | n/a |  |  |

### sanpo_cBVSUvSN_0000_fastonly2

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | right | no | 0.0 | 0.0 | miss | n/a |  |  |
| e2 | person | left | yes | 0.0 | 3.1 | 2.51 | +0.6 | no | Person ahead. |
| e3 | person | right | no | 0.0 | 3.5 | 2.51 | +1.0 | no | Person ahead. |
| e4 | person | left | yes | 3.5 | 7.5 | miss | n/a |  |  |
| e5 | person | ahead | no | 9.5 | 13.5 | 10.04 | +3.4 | yes | Person crossing ahead. |
| e6 | person | left | yes | 13.2 | 17.2 | 13.69 | +3.5 | yes | Person left. |
| e7 | person | ahead | no | 15.1 | 18.7 | 15.72 | +3.0 | no | Person crossing left. |
| e8 | person | ahead | no | 15.7 | 19.7 | 16.80 | +2.9 | no | Person left. |
| e9 | person | left | yes | 21.1 | 25.1 | 21.98 | +3.1 | no | Person right. |
| e10 | person | left | no | 22.1 | 26.1 | 22.80 | +3.3 | no | Person crossing right. |
| e11 | person | left | yes | 22.3 | 26.3 | 22.80 | +3.5 | no | Person crossing right. |
| e12 | person | right | no | 26.7 | 26.9 | 27.57 | -0.6 | yes | Person crossing right. |
| e13 | person | left | yes | 23.5 | 27.5 | 24.22 | +3.3 | yes | Person left. |
| e14 | person | left | no | 25.9 | 29.9 | 26.58 | +3.3 | no | Person ahead. |
| e15 | person | right | no | 27.1 | 29.9 | 27.57 | +2.3 | yes | Person crossing right. |
| e16 | person | ahead | no | 27.3 | 29.9 | 27.57 | +2.3 | no | Person crossing right. |
| e17 | person | ahead | yes | 25.9 | 29.9 | 26.58 | +3.3 | yes | Person ahead. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e2 | person | left | 3.1 | miss | n/a |  |  |
| e4 | person | left | 7.5 | miss | n/a |  |  |
| e6 | person | left | 17.2 | 13.69-14.46 | +2.7 | yes | Person left. |
| e9 | person | left | 25.1 | 21.98-22.74 | +2.3 | no | Person right. |
| e11 | person | left | 26.3 | 22.80-23.92 | +2.3 | no | Person crossing right. |
| e13 | person | left | 27.5 | 24.22-24.94 | +2.5 | yes | Person left. |
| e17 | person | ahead | 29.9 | 25.80-26.53 | +3.3 | no | Person left. |

### sanpo_eHxtA669_0000_fastonly2

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | left | no | 0.0 | 0.1 | 0.93 | -0.8 | no | Person right. |
| e2 | person | left | no | 0.0 | 0.5 | 0.93 | -0.4 | no | Person right. |
| e3 | person | left | yes | 0.0 | 3.1 | 0.93 | +2.1 | no | Person right. |
| e4 | person | right | yes | 17.7 | 21.7 | 18.81 | +2.9 | no | Person left. |
| e5 | person | left | yes | 21.1 | 24.8 | 21.63 | +3.2 | no | Person crossing right. |
| e6 | person | right | no | 23.1 | 27.1 | 24.56 | +2.5 | yes | Person right. |
| e7 | person | right | no | 23.3 | 27.3 | 24.56 | +2.8 | yes | Person right. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e3 | person | left | 3.1 | 0.93-1.68 | +1.4 | no | Person right. |
| e4 | person | right | 21.7 | 18.81-19.62 | +2.1 | no | Person left. |
| e5 | person | left | 24.8 | 21.63-22.81 | +2.0 | no | Person crossing right. |

### sanpo_qFDP9gJD_0000_fastonly2

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | car | left | no | 0.3 | 4.1 | 1.12 | +3.0 | no | Truck right. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|

### sanpo_qn1eNtR0_0029_fastonly2

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | car | right | no | 0.0 | 3.6 | miss | n/a |  |  |
| e2 | person | left | yes | 11.9 | 13.9 | 12.02 | +1.9 | yes | Person left. |
| e3 | car | right | no | 16.4 | 17.5 | miss | n/a |  |  |
| e4 | car | right | no | 17.7 | 19.7 | miss | n/a |  |  |
| e5 | person | right | yes | 20.1 | 24.1 | 20.55 | +3.6 | no | Person crossing ahead. |
| e6 | person | left | yes | 20.8 | 24.8 | 21.82 | +3.0 | no | Person ahead. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e2 | person | left | 13.9 | 12.02-12.72 | +1.1 | yes | Person left. |
| e5 | person | right | 24.1 | 20.55-21.75 | +2.4 | no | Person crossing ahead. |
| e6 | person | left | 24.8 | 21.82-22.62 | +2.2 | no | Person ahead. |

### sanpo_qttyxdua_0000_fastonly2

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|

### sanpo_wXwTZnJH_0007_fastonly2

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | car | right | no | 0.3 | 4.3 | 2.67 | +1.6 | yes | Car right. |
| e2 | car | right | no | 8.9 | 12.9 | 13.65 | -0.7 | yes | Car right. |
| e3 | person | left | no | 20.7 | 24.7 | 24.52 | +0.1 | no | Person right. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|

### sanpo_x5OCPnbr_0078_fastonly2

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | car | right | no | 12.0 | 14.5 | 12.29 | +2.2 | yes | Truck crossing right. |
| e2 | person | left | no | 14.3 | 18.3 | 16.25 | +2.0 | yes | Person left. |
| e3 | car | right | no | 18.3 | 19.1 | miss | n/a |  |  |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
