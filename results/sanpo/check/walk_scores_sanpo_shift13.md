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
| sanpo_7X41_wkj_0000_shift13 | sanpo_7X41_wkj_0000 | 16 | 32.9 | 4/4 (100%) | 5/8 (62%) | -0.1 | -0.7 | +0.3 | 0/5 (0%) | 13 (2) |
| sanpo_8WF0e5NO_0195_shift13 | sanpo_8WF0e5NO_0195 | 4 | 10.4 | 0/2 (0%) | 0/2 (0%) | n/a | n/a | n/a | n/a (no hits) | 4 (0) |
| sanpo_RqOwmltc_0000_shift13 | sanpo_RqOwmltc_0000 | 24 | 48.3 | 8/8 (100%) | 27/28 (96%) | +1.5 | +0.3 | +1.7 | 7/27 (26%) | 6 (0) |
| sanpo_UGNwBEZM_0353_shift13 | sanpo_UGNwBEZM_0353 | 11 | 22.5 | 5/6 (83%) | 8/9 (89%) | +1.0 | -0.4 | +1.0 | 2/8 (25%) | 3 (0) |
| sanpo_cBVSUvSN_0000_shift13 | sanpo_cBVSUvSN_0000 | 25 | 50.2 | 7/7 (100%) | 14/17 (82%) | +2.0 | +1.7 | +2.0 | 6/14 (43%) | 9 (4) |
| sanpo_eHxtA669_0000_shift13 | sanpo_eHxtA669_0000 | 11 | 22.6 | 2/3 (67%) | 2/7 (29%) | +1.0 | +0.5 | +1.0 | 1/2 (50%) | 9 (0) |
| sanpo_qFDP9gJD_0000_shift13 | sanpo_qFDP9gJD_0000 | 18 | 38.0 | n/a (0 events) | 1/1 (100%) | n/a | n/a | +1.6 | 1/1 (100%) | 16 (0) |
| sanpo_qn1eNtR0_0029_shift13 | sanpo_qn1eNtR0_0029 | 12 | 24.8 | 2/3 (67%) | 4/6 (67%) | -0.6 | -0.9 | -0.4 | 3/4 (75%) | 10 (3) |
| sanpo_qttyxdua_0000_shift13 | sanpo_qttyxdua_0000 | 10 | 22.8 | n/a (0 events) | n/a (0 events) | n/a | n/a | n/a | n/a (no hits) | 10 (0) |
| sanpo_wXwTZnJH_0007_shift13 | sanpo_wXwTZnJH_0007 | 11 | 25.9 | n/a (0 events) | 2/3 (67%) | n/a | n/a | +1.0 | 2/2 (100%) | 9 (0) |
| sanpo_x5OCPnbr_0078_shift13 | sanpo_x5OCPnbr_0078 | 20 | 41.7 | n/a (0 events) | 2/3 (67%) | n/a | n/a | +0.3 | 1/2 (50%) | 17 (0) |
| TOTAL shift13 (11 clips) | all | 162 | 31.5 | 28/33 (85%) | 65/84 (77%) | +1.5 | -0.9 | +1.6 | 23/65 (35%) | 106 (9) |

## Strict

must_warn events only. On time: names the class and the speech ends by t_close; one utterance credits one event. Spare: seconds between speech end and t_close. Warn precision: share of all spoken utterances that name a must_warn event near its time. Rules in the scripts/score_walk.py docstring.

| run | on time | on time, side right | spare median (s) | warn precision | utt/min |
|---|---|---|---|---|---|
| sanpo_7X41_wkj_0000_shift13 | 2/4 (50%) | 0/4 (0%) | +0.5 | 4/16 (25%) | 32.9 |
| sanpo_8WF0e5NO_0195_shift13 | 0/2 (0%) | 0/2 (0%) | n/a | 0/4 (0%) | 10.4 |
| sanpo_RqOwmltc_0000_shift13 | 8/8 (100%) | 2/8 (25%) | +1.5 | 16/24 (67%) | 48.3 |
| sanpo_UGNwBEZM_0353_shift13 | 5/6 (83%) | 2/6 (33%) | +0.4 | 7/11 (64%) | 22.5 |
| sanpo_cBVSUvSN_0000_shift13 | 7/7 (100%) | 3/7 (43%) | +1.2 | 14/25 (56%) | 50.2 |
| sanpo_eHxtA669_0000_shift13 | 1/3 (33%) | 0/3 (0%) | +0.8 | 2/11 (18%) | 22.6 |
| sanpo_qFDP9gJD_0000_shift13 | n/a (0 events) | n/a (0 events) | n/a | 0/18 (0%) | 38.0 |
| sanpo_qn1eNtR0_0029_shift13 | 0/3 (0%) | 0/3 (0%) | n/a | 1/12 (8%) | 24.8 |
| sanpo_qttyxdua_0000_shift13 | n/a (0 events) | n/a (0 events) | n/a | 0/10 (0%) | 22.8 |
| sanpo_wXwTZnJH_0007_shift13 | n/a (0 events) | n/a (0 events) | n/a | 0/11 (0%) | 25.9 |
| sanpo_x5OCPnbr_0078_shift13 | n/a (0 events) | n/a (0 events) | n/a | 0/20 (0%) | 41.7 |
| TOTAL shift13 (11 clips) | 23/33 (70%) | 7/33 (21%) | +1.0 | 44/162 (27%) | 31.5 |

## Per-event detail

### sanpo_7X41_wkj_0000_shift13

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | left | yes | 5.1 | 7.6 | 8.33 | -0.7 | no | Person ahead. |
| e2 | person | left | yes | 6.2 | 8.7 | 8.33 | +0.3 | no | Person ahead. |
| e3 | person | left | no | 8.0 | 10.5 | 8.33 | +2.2 | no | Person ahead. |
| e4 | car | left | no | 8.6 | 11.1 | miss | n/a |  |  |
| e5 | person | left | no | 8.6 | 11.1 | miss | n/a |  |  |
| e6 | car | ahead | no | 11.6 | 12.5 | miss | n/a |  |  |
| e7 | person | left | yes | 14.3 | 14.9 | 15.40 | -0.5 | no | Person ahead. |
| e8 | person | left | yes | 14.6 | 17.1 | 15.40 | +1.7 | no | Person ahead. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e1 | person | left | 7.6 | miss | n/a |  |  |
| e2 | person | left | 8.7 | miss | n/a |  |  |
| e7 | person | left | 14.9 | 14.00-14.72 | +0.2 | no | Person right. |
| e8 | person | left | 17.1 | 15.40-16.22 | +0.8 | no | Person ahead. |

### sanpo_8WF0e5NO_0195_shift13

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | right | yes | 3.4 | 5.9 | miss | n/a |  |  |
| e2 | person | left | yes | 22.0 | 24.5 | miss | n/a |  |  |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e1 | person | right | 5.9 | miss | n/a |  |  |
| e2 | person | left | 24.5 | miss | n/a |  |  |

### sanpo_RqOwmltc_0000_shift13

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | right | no | 4.6 | 6.4 | 6.28 | +0.1 | no | Person left. |
| e2 | person | right | no | 5.5 | 8.0 | 6.28 | +1.7 | no | Person left. |
| e3 | person | right | no | 5.6 | 8.1 | 6.28 | +1.8 | no | Person left. |
| e4 | person | right | no | 5.7 | 8.2 | 6.28 | +1.9 | no | Person left. |
| e5 | person | right | no | 5.7 | 8.2 | 6.28 | +1.9 | no | Person left. |
| e6 | person | right | yes | 6.4 | 8.9 | 8.31 | +0.6 | no | Person crossing left. |
| e7 | person | right | yes | 7.5 | 10.0 | 8.31 | +1.7 | no | Person crossing left. |
| e8 | person | left | no | 8.9 | 11.4 | 9.51 | +1.9 | no | Person right. |
| e9 | person | right | no | 10.7 | 13.2 | 11.95 | +1.2 | no | Person left. |
| e10 | person | right | no | 10.8 | 13.3 | 11.95 | +1.3 | no | Person left. |
| e11 | person | right | yes | 11.7 | 14.2 | 11.95 | +2.2 | no | Person left. |
| e12 | person | right | no | 14.1 | 14.5 | 14.29 | +0.2 | no | Person left. |
| e13 | person | right | yes | 14.4 | 16.9 | 16.64 | +0.3 | yes | Person right. |
| e14 | car | left | no | 16.1 | 18.6 | miss | n/a |  |  |
| e15 | person | left | yes | 18.3 | 20.8 | 19.29 | +1.5 | no | Person crossing right. |
| e16 | person | right | yes | 19.3 | 21.8 | 20.45 | +1.4 | no | Person ahead. |
| e17 | person | left | yes | 19.4 | 21.9 | 20.45 | +1.5 | no | Person ahead. |
| e18 | person | ahead | no | 20.3 | 22.8 | 20.45 | +2.4 | yes | Person ahead. |
| e19 | person | right | no | 21.2 | 23.7 | 21.33 | +2.3 | no | Person crossing left. |
| e20 | person | right | no | 23.1 | 25.6 | 24.10 | +1.5 | yes | Person right. |
| e21 | person | right | no | 25.5 | 25.9 | 25.99 | -0.1 | no | Person left. |
| e22 | person | right | yes | 23.4 | 25.9 | 24.10 | +1.8 | yes | Person right. |
| e23 | person | right | no | 23.9 | 26.4 | 24.10 | +2.3 | yes | Person right. |
| e24 | person | right | no | 25.4 | 27.9 | 25.99 | +1.9 | no | Person left. |
| e25 | person | left | no | 27.0 | 29.5 | 27.44 | +2.1 | no | Person ahead. |
| e26 | person | right | no | 27.8 | 29.7 | 28.36 | +1.3 | yes | Person crossing right. |
| e27 | person | ahead | no | 28.2 | 29.7 | 28.36 | +1.4 | no | Person crossing right. |
| e28 | person | ahead | no | 27.4 | 29.9 | 27.44 | +2.5 | yes | Person ahead. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e6 | person | right | 8.9 | 6.28-7.17 | +1.8 | no | Person left. |
| e7 | person | right | 10.0 | 8.31-9.47 | +0.5 | no | Person crossing left. |
| e11 | person | right | 14.2 | 11.95-12.70 | +1.5 | no | Person left. |
| e13 | person | right | 16.9 | 14.29-14.97 | +2.0 | no | Person left. |
| e15 | person | left | 20.8 | 18.04-19.23 | +1.6 | no | Person crossing ahead. |
| e16 | person | right | 21.8 | 19.29-20.40 | +1.4 | yes | Person crossing right. |
| e17 | person | left | 21.9 | 20.45-21.27 | +0.7 | no | Person ahead. |
| e22 | person | right | 25.9 | 24.10-24.83 | +1.1 | yes | Person right. |

### sanpo_UGNwBEZM_0353_shift13

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | left | yes | 0.0 | 2.3 | 1.17 | +1.1 | yes | Person left. |
| e2 | person | ahead | no | 5.9 | 8.4 | 8.29 | +0.1 | no | Person left. |
| e3 | person | left | yes | 6.8 | 9.3 | 8.29 | +1.0 | yes | Person left. |
| e4 | person | left | yes | 10.2 | 12.7 | 10.56 | +2.1 | no | Person crossing right. |
| e5 | person | left | yes | 16.5 | 17.7 | miss | n/a |  |  |
| e6 | person | left | yes | 16.8 | 19.3 | 19.76 | -0.4 | no | Person ahead. |
| e7 | person | left | yes | 18.2 | 20.7 | 19.76 | +0.9 | no | Person ahead. |
| e8 | person | right | no | 26.4 | 28.9 | 26.55 | +2.4 | no | Person left. |
| e9 | person | right | no | 27.4 | 29.9 | 29.27 | +0.6 | no | Person crossing left. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e1 | person | left | 2.3 | 1.17-1.91 | +0.4 | yes | Person left. |
| e3 | person | left | 9.3 | 8.29-9.05 | +0.3 | yes | Person left. |
| e4 | person | left | 12.7 | 10.56-11.66 | +1.0 | no | Person crossing right. |
| e5 | person | left | 17.7 | 15.02-15.83 | +1.9 | no | Person ahead. |
| e6 | person | left | 19.3 | miss | n/a |  |  |
| e7 | person | left | 20.7 | 19.76-20.54 | +0.1 | no | Person ahead. |

### sanpo_cBVSUvSN_0000_shift13

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | right | no | 0.0 | 0.0 | miss | n/a |  |  |
| e2 | person | left | yes | 0.6 | 3.1 | 1.41 | +1.7 | yes | Person left. |
| e3 | person | right | no | 1.0 | 3.5 | 1.41 | +2.1 | no | Person left. |
| e4 | person | left | yes | 5.0 | 7.5 | 5.11 | +2.4 | no | Person right. |
| e5 | person | ahead | no | 11.0 | 13.5 | 11.86 | +1.6 | yes | Person ahead. |
| e6 | person | left | yes | 14.7 | 17.2 | 15.51 | +1.7 | no | Person ahead. |
| e7 | person | ahead | no | 16.2 | 18.7 | miss | n/a |  |  |
| e8 | person | ahead | no | 17.2 | 19.7 | miss | n/a |  |  |
| e9 | person | left | yes | 22.6 | 25.1 | 23.04 | +2.0 | no | Person crossing ahead. |
| e10 | person | left | no | 23.6 | 26.1 | 24.24 | +1.9 | yes | Person left. |
| e11 | person | left | yes | 23.8 | 26.3 | 24.24 | +2.0 | yes | Person left. |
| e12 | person | right | no | 26.7 | 26.9 | 26.68 | +0.2 | no | Person left. |
| e13 | person | left | yes | 25.0 | 27.5 | 25.01 | +2.5 | no | Person crossing ahead. |
| e14 | person | left | no | 27.4 | 29.9 | 27.52 | +2.4 | no | Person crossing ahead. |
| e15 | person | right | no | 27.4 | 29.9 | 27.52 | +2.4 | no | Person crossing ahead. |
| e16 | person | ahead | no | 27.4 | 29.9 | 27.52 | +2.4 | yes | Person crossing ahead. |
| e17 | person | ahead | yes | 27.4 | 29.9 | 27.52 | +2.4 | yes | Person crossing ahead. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e2 | person | left | 3.1 | 1.41-2.15 | +0.9 | yes | Person left. |
| e4 | person | left | 7.5 | 5.11-5.88 | +1.6 | no | Person right. |
| e6 | person | left | 17.2 | 15.51-16.22 | +1.0 | no | Person ahead. |
| e9 | person | left | 25.1 | 23.04-24.18 | +0.9 | no | Person crossing ahead. |
| e11 | person | left | 26.3 | 24.24-24.95 | +1.3 | yes | Person left. |
| e13 | person | left | 27.5 | 25.01-26.22 | +1.2 | no | Person crossing ahead. |
| e17 | person | ahead | 29.9 | 27.52-28.67 | +1.2 | yes | Person crossing ahead. |

### sanpo_eHxtA669_0000_shift13

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | left | no | 0.0 | 0.1 | miss | n/a |  |  |
| e2 | person | left | no | 0.0 | 0.5 | miss | n/a |  |  |
| e3 | person | left | yes | 0.6 | 3.1 | 2.61 | +0.5 | yes | Person left. |
| e4 | person | right | yes | 19.2 | 21.7 | 20.19 | +1.5 | no | Person left. |
| e5 | person | left | yes | 22.3 | 24.8 | miss | n/a |  |  |
| e6 | person | right | no | 24.6 | 27.1 | miss | n/a |  |  |
| e7 | person | right | no | 24.8 | 27.3 | miss | n/a |  |  |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e3 | person | left | 3.1 | miss | n/a |  |  |
| e4 | person | right | 21.7 | 20.19-20.91 | +0.8 | no | Person left. |
| e5 | person | left | 24.8 | miss | n/a |  |  |

### sanpo_qFDP9gJD_0000_shift13

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | car | left | no | 1.6 | 4.1 | 2.50 | +1.6 | yes | Car left. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|

### sanpo_qn1eNtR0_0029_shift13

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | car | right | no | 1.1 | 3.6 | miss | n/a |  |  |
| e2 | person | left | yes | 11.9 | 13.9 | miss | n/a |  |  |
| e3 | car | right | no | 16.4 | 17.5 | 17.98 | -0.5 | yes | Car right. |
| e4 | car | right | no | 17.7 | 19.7 | 17.98 | +1.8 | yes | Car right. |
| e5 | person | right | yes | 21.6 | 24.1 | 25.02 | -0.9 | no | Person left. |
| e6 | person | left | yes | 22.3 | 24.8 | 25.02 | -0.2 | yes | Person left. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e2 | person | left | 13.9 | miss | n/a |  |  |
| e5 | person | right | 24.1 | miss | n/a |  |  |
| e6 | person | left | 24.8 | miss | n/a |  |  |

### sanpo_qttyxdua_0000_shift13

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|

### sanpo_wXwTZnJH_0007_shift13

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | car | right | no | 1.8 | 4.3 | 3.80 | +0.5 | yes | Car right. |
| e2 | car | right | no | 10.4 | 12.9 | 11.38 | +1.5 | yes | Car right. |
| e3 | person | left | no | 22.2 | 24.7 | miss | n/a |  |  |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|

### sanpo_x5OCPnbr_0078_shift13

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | car | right | no | 12.0 | 14.5 | miss | n/a |  |  |
| e2 | person | left | no | 15.8 | 18.3 | 16.86 | +1.4 | yes | Person left. |
| e3 | car | right | no | 18.3 | 19.1 | 19.81 | -0.7 | no | Car ahead. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
