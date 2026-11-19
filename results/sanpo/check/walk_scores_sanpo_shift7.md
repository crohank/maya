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
| sanpo_7X41_wkj_0000_shift7 | sanpo_7X41_wkj_0000 | 16 | 32.9 | 4/4 (100%) | 6/8 (75%) | +0.3 | -0.4 | +0.9 | 0/6 (0%) | 12 (2) |
| sanpo_8WF0e5NO_0195_shift7 | sanpo_8WF0e5NO_0195 | 4 | 10.4 | 0/2 (0%) | 0/2 (0%) | n/a | n/a | n/a | n/a (no hits) | 4 (0) |
| sanpo_RqOwmltc_0000_shift7 | sanpo_RqOwmltc_0000 | 24 | 48.3 | 8/8 (100%) | 27/28 (96%) | +1.9 | +1.6 | +1.9 | 3/27 (11%) | 4 (0) |
| sanpo_UGNwBEZM_0353_shift7 | sanpo_UGNwBEZM_0353 | 11 | 22.5 | 3/6 (50%) | 4/9 (44%) | +0.1 | -0.0 | +0.3 | 3/4 (75%) | 7 (0) |
| sanpo_cBVSUvSN_0000_shift7 | sanpo_cBVSUvSN_0000 | 25 | 50.2 | 7/7 (100%) | 15/17 (88%) | +2.2 | +1.6 | +2.2 | 8/15 (53%) | 8 (4) |
| sanpo_eHxtA669_0000_shift7 | sanpo_eHxtA669_0000 | 11 | 22.6 | 1/3 (33%) | 5/7 (71%) | +2.4 | +2.4 | +1.3 | 3/5 (60%) | 6 (0) |
| sanpo_qFDP9gJD_0000_shift7 | sanpo_qFDP9gJD_0000 | 18 | 38.0 | n/a (0 events) | 1/1 (100%) | n/a | n/a | +2.3 | 1/1 (100%) | 16 (0) |
| sanpo_qn1eNtR0_0029_shift7 | sanpo_qn1eNtR0_0029 | 12 | 24.8 | 0/3 (0%) | 2/6 (33%) | n/a | n/a | +0.0 | 2/2 (100%) | 10 (3) |
| sanpo_qttyxdua_0000_shift7 | sanpo_qttyxdua_0000 | 10 | 22.8 | n/a (0 events) | n/a (0 events) | n/a | n/a | n/a | n/a (no hits) | 10 (0) |
| sanpo_wXwTZnJH_0007_shift7 | sanpo_wXwTZnJH_0007 | 11 | 25.9 | n/a (0 events) | 1/3 (33%) | n/a | n/a | +1.6 | 0/1 (0%) | 10 (0) |
| sanpo_x5OCPnbr_0078_shift7 | sanpo_x5OCPnbr_0078 | 20 | 41.7 | n/a (0 events) | 3/3 (100%) | n/a | n/a | +0.7 | 1/3 (33%) | 14 (0) |
| TOTAL shift7 (11 clips) | all | 162 | 31.5 | 23/33 (70%) | 64/84 (76%) | +1.8 | -0.4 | +1.6 | 21/64 (33%) | 101 (9) |

## Strict

must_warn events only. On time: names the class and the speech ends by t_close; one utterance credits one event. Spare: seconds between speech end and t_close. Warn precision: share of all spoken utterances that name a must_warn event near its time. Rules in the scripts/score_walk.py docstring.

| run | on time | on time, side right | spare median (s) | warn precision | utt/min |
|---|---|---|---|---|---|
| sanpo_7X41_wkj_0000_shift7 | 2/4 (50%) | 0/4 (0%) | +1.9 | 5/16 (31%) | 32.9 |
| sanpo_8WF0e5NO_0195_shift7 | 0/2 (0%) | 0/2 (0%) | n/a | 0/4 (0%) | 10.4 |
| sanpo_RqOwmltc_0000_shift7 | 8/8 (100%) | 1/8 (12%) | +1.7 | 19/24 (79%) | 48.3 |
| sanpo_UGNwBEZM_0353_shift7 | 2/6 (33%) | 1/6 (17%) | +1.1 | 6/11 (55%) | 22.5 |
| sanpo_cBVSUvSN_0000_shift7 | 7/7 (100%) | 4/7 (57%) | +1.5 | 15/25 (60%) | 50.2 |
| sanpo_eHxtA669_0000_shift7 | 1/3 (33%) | 1/3 (33%) | +1.6 | 4/11 (36%) | 22.6 |
| sanpo_qFDP9gJD_0000_shift7 | n/a (0 events) | n/a (0 events) | n/a | 0/18 (0%) | 38.0 |
| sanpo_qn1eNtR0_0029_shift7 | 0/3 (0%) | 0/3 (0%) | n/a | 0/12 (0%) | 24.8 |
| sanpo_qttyxdua_0000_shift7 | n/a (0 events) | n/a (0 events) | n/a | 0/10 (0%) | 22.8 |
| sanpo_wXwTZnJH_0007_shift7 | n/a (0 events) | n/a (0 events) | n/a | 0/11 (0%) | 25.9 |
| sanpo_x5OCPnbr_0078_shift7 | n/a (0 events) | n/a (0 events) | n/a | 0/20 (0%) | 41.7 |
| TOTAL shift7 (11 clips) | 20/33 (61%) | 7/33 (21%) | +1.6 | 49/162 (30%) | 31.5 |

## Per-event detail

### sanpo_7X41_wkj_0000_shift7

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | left | yes | 5.1 | 7.6 | 8.00 | -0.4 | no | Person right. |
| e2 | person | left | yes | 6.2 | 8.7 | 8.00 | +0.7 | no | Person right. |
| e3 | person | left | no | 8.0 | 10.5 | 9.40 | +1.1 | no | Person ahead. |
| e4 | car | left | no | 8.6 | 11.1 | miss | n/a |  |  |
| e5 | person | left | no | 8.6 | 11.1 | 9.40 | +1.7 | no | Person ahead. |
| e6 | car | ahead | no | 11.6 | 12.5 | miss | n/a |  |  |
| e7 | person | left | yes | 14.3 | 14.9 | 14.94 | -0.0 | no | Person ahead. |
| e8 | person | left | yes | 14.6 | 17.1 | 14.94 | +2.1 | no | Person ahead. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e1 | person | left | 7.6 | miss | n/a |  |  |
| e2 | person | left | 8.7 | miss | n/a |  |  |
| e7 | person | left | 14.9 | 12.30-13.40 | +1.5 | no | Person crossing right. |
| e8 | person | left | 17.1 | 14.11-14.86 | +2.2 | no | Person right. |

### sanpo_8WF0e5NO_0195_shift7

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | right | yes | 3.4 | 5.9 | miss | n/a |  |  |
| e2 | person | left | yes | 22.0 | 24.5 | miss | n/a |  |  |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e1 | person | right | 5.9 | miss | n/a |  |  |
| e2 | person | left | 24.5 | miss | n/a |  |  |

### sanpo_RqOwmltc_0000_shift7

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | right | no | 4.6 | 6.4 | 5.95 | +0.4 | no | Person left. |
| e2 | person | right | no | 5.5 | 8.0 | 5.95 | +2.0 | no | Person left. |
| e3 | person | right | no | 5.6 | 8.1 | 5.95 | +2.1 | no | Person left. |
| e4 | person | right | no | 5.7 | 8.2 | 5.95 | +2.2 | no | Person left. |
| e5 | person | right | no | 5.7 | 8.2 | 5.95 | +2.2 | no | Person left. |
| e6 | person | right | yes | 6.4 | 8.9 | 7.11 | +1.8 | no | Person crossing left. |
| e7 | person | right | yes | 7.5 | 10.0 | 8.29 | +1.7 | no | Person left. |
| e8 | person | left | no | 8.9 | 11.4 | 10.64 | +0.8 | no | Person right. |
| e9 | person | right | no | 10.7 | 13.2 | 12.04 | +1.2 | no | Person crossing ahead. |
| e10 | person | right | no | 10.8 | 13.3 | 12.04 | +1.2 | no | Person crossing ahead. |
| e11 | person | right | yes | 11.7 | 14.2 | 12.04 | +2.2 | no | Person crossing ahead. |
| e12 | person | right | no | 14.1 | 14.5 | 14.45 | +0.0 | no | Person ahead. |
| e13 | person | right | yes | 14.4 | 16.9 | 14.45 | +2.5 | no | Person ahead. |
| e14 | car | left | no | 16.1 | 18.6 | miss | n/a |  |  |
| e15 | person | left | yes | 18.3 | 20.8 | 19.23 | +1.6 | no | Person ahead. |
| e16 | person | right | yes | 19.3 | 21.8 | 19.99 | +1.8 | no | Person left. |
| e17 | person | left | yes | 19.4 | 21.9 | 19.99 | +1.9 | yes | Person left. |
| e18 | person | ahead | no | 20.3 | 22.8 | 20.71 | +2.1 | no | Person right. |
| e19 | person | right | no | 21.2 | 23.7 | 21.44 | +2.2 | no | Person ahead. |
| e20 | person | right | no | 23.1 | 25.6 | 23.69 | +1.9 | no | Person crossing left. |
| e21 | person | right | no | 25.5 | 25.9 | 25.86 | +0.0 | no | Person ahead. |
| e22 | person | right | yes | 23.4 | 25.9 | 23.69 | +2.2 | no | Person crossing left. |
| e23 | person | right | no | 23.9 | 26.4 | 25.04 | +1.4 | yes | Person right. |
| e24 | person | right | no | 25.4 | 27.9 | 25.86 | +2.1 | no | Person ahead. |
| e25 | person | left | no | 27.0 | 29.5 | 27.60 | +1.9 | no | Person right. |
| e26 | person | right | no | 27.8 | 29.7 | 28.35 | +1.3 | yes | Person crossing right. |
| e27 | person | ahead | no | 28.2 | 29.7 | 28.35 | +1.4 | no | Person crossing right. |
| e28 | person | ahead | no | 27.4 | 29.9 | 27.60 | +2.3 | no | Person right. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e6 | person | right | 8.9 | 5.95-6.70 | +2.2 | no | Person left. |
| e7 | person | right | 10.0 | 7.11-8.32 | +1.7 | no | Person crossing left. |
| e11 | person | right | 14.2 | 12.04-13.23 | +1.0 | no | Person crossing ahead. |
| e13 | person | right | 16.9 | 14.45-15.27 | +1.7 | no | Person ahead. |
| e15 | person | left | 20.8 | 18.10-18.83 | +2.0 | no | Person right. |
| e16 | person | right | 21.8 | 19.23-19.95 | +1.9 | no | Person ahead. |
| e17 | person | left | 21.9 | 19.99-20.66 | +1.3 | yes | Person left. |
| e22 | person | right | 25.9 | 23.69-24.99 | +0.9 | no | Person crossing left. |

### sanpo_UGNwBEZM_0353_shift7

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | left | yes | 0.0 | 2.3 | 2.29 | -0.0 | yes | Person left. |
| e2 | person | ahead | no | 5.9 | 8.4 | 7.96 | +0.4 | no | Person left. |
| e3 | person | left | yes | 6.8 | 9.3 | 7.96 | +1.4 | yes | Person left. |
| e4 | person | left | yes | 10.2 | 12.7 | miss | n/a |  |  |
| e5 | person | left | yes | 16.5 | 17.7 | miss | n/a |  |  |
| e6 | person | left | yes | 16.8 | 19.3 | miss | n/a |  |  |
| e7 | person | left | yes | 18.2 | 20.7 | 20.55 | +0.1 | yes | Person left. |
| e8 | person | right | no | 26.4 | 28.9 | miss | n/a |  |  |
| e9 | person | right | no | 27.4 | 29.9 | miss | n/a |  |  |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e1 | person | left | 2.3 | miss | n/a |  |  |
| e3 | person | left | 9.3 | 7.96-8.69 | +0.6 | yes | Person left. |
| e4 | person | left | 12.7 | miss | n/a |  |  |
| e5 | person | left | 17.7 | 15.34-16.09 | +1.6 | no | Person ahead. |
| e6 | person | left | 19.3 | miss | n/a |  |  |
| e7 | person | left | 20.7 | miss | n/a |  |  |

### sanpo_cBVSUvSN_0000_shift7

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | right | no | 0.0 | 0.0 | miss | n/a |  |  |
| e2 | person | left | yes | 0.6 | 3.1 | 1.35 | +1.7 | yes | Person left. |
| e3 | person | right | no | 1.0 | 3.5 | 1.35 | +2.1 | no | Person left. |
| e4 | person | left | yes | 5.0 | 7.5 | 5.86 | +1.6 | no | Person ahead. |
| e5 | person | ahead | no | 11.0 | 13.5 | miss | n/a |  |  |
| e6 | person | left | yes | 14.7 | 17.2 | 15.57 | +1.6 | no | Person crossing right. |
| e7 | person | ahead | no | 16.2 | 18.7 | 17.04 | +1.6 | yes | Person crossing ahead. |
| e8 | person | ahead | no | 17.2 | 19.7 | 18.24 | +1.5 | no | Person left. |
| e9 | person | left | yes | 22.6 | 25.1 | 22.72 | +2.4 | yes | Person crossing left. |
| e10 | person | left | no | 23.6 | 26.1 | 23.80 | +2.3 | yes | Person left. |
| e11 | person | left | yes | 23.8 | 26.3 | 23.80 | +2.5 | yes | Person left. |
| e12 | person | right | no | 26.7 | 26.9 | 27.43 | -0.5 | yes | Person right. |
| e13 | person | left | yes | 25.0 | 27.5 | 25.27 | +2.2 | yes | Person left. |
| e14 | person | left | no | 27.4 | 29.9 | 27.43 | +2.4 | no | Person right. |
| e15 | person | right | no | 27.4 | 29.9 | 27.43 | +2.4 | yes | Person right. |
| e16 | person | ahead | no | 27.4 | 29.9 | 27.43 | +2.4 | no | Person right. |
| e17 | person | ahead | yes | 27.4 | 29.9 | 27.43 | +2.4 | no | Person right. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e2 | person | left | 3.1 | 1.35-2.07 | +1.0 | yes | Person left. |
| e4 | person | left | 7.5 | 4.70-5.81 | +1.7 | no | Person crossing right. |
| e6 | person | left | 17.2 | 15.57-16.77 | +0.4 | no | Person crossing right. |
| e9 | person | left | 25.1 | 22.72-23.75 | +1.3 | yes | Person crossing left. |
| e11 | person | left | 26.3 | 23.80-24.53 | +1.7 | yes | Person left. |
| e13 | person | left | 27.5 | 25.27-26.02 | +1.5 | yes | Person left. |
| e17 | person | ahead | 29.9 | 27.43-28.17 | +1.7 | no | Person right. |

### sanpo_eHxtA669_0000_shift7

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | person | left | no | 0.0 | 0.1 | 0.66 | -0.5 | yes | Person left. |
| e2 | person | left | no | 0.0 | 0.5 | 0.66 | -0.1 | yes | Person left. |
| e3 | person | left | yes | 0.6 | 3.1 | 0.66 | +2.4 | yes | Person left. |
| e4 | person | right | yes | 19.2 | 21.7 | miss | n/a |  |  |
| e5 | person | left | yes | 22.3 | 24.8 | miss | n/a |  |  |
| e6 | person | right | no | 24.6 | 27.1 | 25.81 | +1.3 | no | Person left. |
| e7 | person | right | no | 24.8 | 27.3 | 25.81 | +1.5 | no | Person left. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e3 | person | left | 3.1 | 0.66-1.43 | +1.6 | yes | Person left. |
| e4 | person | right | 21.7 | miss | n/a |  |  |
| e5 | person | left | 24.8 | miss | n/a |  |  |

### sanpo_qFDP9gJD_0000_shift7

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | car | left | no | 1.6 | 4.1 | 1.79 | +2.3 | yes | Car crossing left. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|

### sanpo_qn1eNtR0_0029_shift7

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | car | right | no | 1.1 | 3.6 | miss | n/a |  |  |
| e2 | person | left | yes | 11.9 | 13.9 | miss | n/a |  |  |
| e3 | car | right | no | 16.4 | 17.5 | 17.38 | +0.1 | yes | Car right. |
| e4 | car | right | no | 17.7 | 19.7 | 19.79 | -0.1 | yes | Car right. |
| e5 | person | right | yes | 21.6 | 24.1 | miss | n/a |  |  |
| e6 | person | left | yes | 22.3 | 24.8 | miss | n/a |  |  |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
| e2 | person | left | 13.9 | miss | n/a |  |  |
| e5 | person | right | 24.1 | miss | n/a |  |  |
| e6 | person | left | 24.8 | miss | n/a |  |  |

### sanpo_qttyxdua_0000_shift7

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|

### sanpo_wXwTZnJH_0007_shift7

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | car | right | no | 1.8 | 4.3 | miss | n/a |  |  |
| e2 | car | right | no | 10.4 | 12.9 | 11.32 | +1.6 | no | Car ahead. |
| e3 | person | left | no | 22.2 | 24.7 | miss | n/a |  |  |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|

### sanpo_x5OCPnbr_0078_shift7

| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |
|---|---|---|---|---|---|---|---|---|---|
| e1 | car | right | no | 12.0 | 14.5 | 13.81 | +0.7 | no | Car ahead. |
| e2 | person | left | no | 15.8 | 18.3 | 16.95 | +1.3 | no | Person ahead. |
| e3 | car | right | no | 18.3 | 19.1 | 19.29 | -0.2 | yes | Truck crossing right. |

Strict (must_warn):

| id | cls | side | t_close | speech | spare | side ok | answer |
|---|---|---|---|---|---|---|---|
