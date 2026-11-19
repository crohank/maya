# Walk v4: SANPO per-event detail (identity scorer, cues)

## v2 (fused_harness defaults)

| clip | id | side | t_close | matched tracks | first cue | its side | track side at t_close |
|---|---|---|---|---|---|---|---|
| sanpo_7X41_wkj_0000 | e1 | left | 7.60 | 52,173 | miss |  | left |
| sanpo_7X41_wkj_0000 | e2 | left | 8.67 | 152,240,272 | word 7.07-7.76 #240 Person right. | right | left |
| sanpo_7X41_wkj_0000 | e7 | left | 14.93 | 396 | miss |  | ahead |
| sanpo_7X41_wkj_0000 | e8 | left | 17.07 | 411 | miss |  | left |
| sanpo_8WF0e5NO_0195 | e1 | right | 5.87 | 18,19,23 | word 3.19-3.87 #19 Person right. | right | right |
| sanpo_8WF0e5NO_0195 | e2 | left | 24.53 | 144 | miss |  | left |
| sanpo_RqOwmltc_0000 | e6 | right | 8.93 | 119,127,136,137,141 | miss |  | right |
| sanpo_RqOwmltc_0000 | e7 | right | 10.00 | 136,148,150,169 | word 9.57-10.27 #150 Person left. | left | right |
| sanpo_RqOwmltc_0000 | e11 | right | 14.20 | 180,182 | word 12.24-13.07 #182 Person ahead. | ahead | right |
| sanpo_RqOwmltc_0000 | e13 | right | 16.93 | 215,216,230 | miss |  | right |
| sanpo_RqOwmltc_0000 | e15 | left | 20.80 | 214,231,246,264 | miss |  | ahead |
| sanpo_RqOwmltc_0000 | e16 | right | 21.80 | 235,265,296 | miss |  | right |
| sanpo_RqOwmltc_0000 | e17 | left | 21.93 | 231,280,284,349,350 | miss |  | left |
| sanpo_RqOwmltc_0000 | e22 | right | 25.93 | 146,391,409,415,420,438,455,459 | miss |  | ahead |
| sanpo_UGNwBEZM_0353 | e1 | left | 2.27 | 3,4,19 | word 0.97-1.66 #4 Person left. | left | left |
| sanpo_UGNwBEZM_0353 | e3 | left | 9.33 | 41,54,72,75,85,89,97,104,106,107,110,111,112,116,120,130,131 | word 6.77-7.61 #106 Person ahead. | ahead | left |
| sanpo_UGNwBEZM_0353 | e4 | left | 12.67 | 112,128,129,132,133,137 | miss |  | left |
| sanpo_UGNwBEZM_0353 | e5 | left | 17.73 | 158,162,172 | miss |  | left |
| sanpo_UGNwBEZM_0353 | e6 | left | 19.33 | 161,189,190 | miss |  | ahead |
| sanpo_UGNwBEZM_0353 | e7 | left | 20.67 | 204,213,223,229 | miss |  | left |
| sanpo_cBVSUvSN_0000 | e2 | left | 3.07 | 1,31 | miss |  | left |
| sanpo_cBVSUvSN_0000 | e4 | left | 7.47 | 55 | miss |  | left |
| sanpo_cBVSUvSN_0000 | e6 | left | 17.20 | 228,230,267,301 | word 14.45-15.62 #230 Person crossing ahead. | ahead | left |
| sanpo_cBVSUvSN_0000 | e9 | left | 25.07 | 391,405,409,443 | word 22.77-23.87 #405 Person crossing right. | right | left |
| sanpo_cBVSUvSN_0000 | e11 | left | 26.27 | 405,409,434,440,446,459 | word 24.99-25.83 #446 Person ahead. | ahead | left |
| sanpo_cBVSUvSN_0000 | e13 | left | 27.47 | 416,446,451,463,468,470 | word 26.64-27.48 #468 Person ahead. | ahead | left |
| sanpo_cBVSUvSN_0000 | e17 | ahead | 29.87 | 468,502 | miss |  | ahead |
| sanpo_eHxtA669_0000 | e3 | left | 3.07 | 4,6,54,61 | word 0.90-1.59 #4 Person right. | right | left |
| sanpo_eHxtA669_0000 | e4 | right | 21.73 | 727,892 | word 18.82-19.51 #727 Person left. | left | right |
| sanpo_eHxtA669_0000 | e5 | left | 24.80 | 839,868,877,881,904,909,921 | word 22.79-23.48 #921 Person left. | left | left |
| sanpo_qn1eNtR0_0029 | e2 | left | 13.87 | 72 | miss |  | left |
| sanpo_qn1eNtR0_0029 | e5 | right | 24.13 | 131,142,145 | word 21.73-22.56 #142 Person ahead. | ahead | right |
| sanpo_qn1eNtR0_0029 | e6 | left | 24.80 | 147,150 | word 23.41-24.11 #150 Person left. | left | left |

## v3 (walk_v3 BASE)

| clip | id | side | t_close | matched tracks | first cue | its side | track side at t_close |
|---|---|---|---|---|---|---|---|
| sanpo_7X41_wkj_0000 | e1 | left | 7.60 | 52,173 | miss |  | left |
| sanpo_7X41_wkj_0000 | e2 | left | 8.67 | 152,240,272 | tone 7.02-7.17 #240 [tone right, mid] | right | left |
| sanpo_7X41_wkj_0000 | e7 | left | 14.93 | 396 | miss |  | ahead |
| sanpo_7X41_wkj_0000 | e8 | left | 17.07 | 411 | tone 15.98-16.13 #411 [tone left, mid] | left | left |
| sanpo_8WF0e5NO_0195 | e1 | right | 5.87 | 18,19,23 | tone 3.13-3.28 #19 [tone right, mid] | right | right |
| sanpo_8WF0e5NO_0195 | e2 | left | 24.53 | 144 | miss |  | left |
| sanpo_RqOwmltc_0000 | e6 | right | 8.93 | 119,127,136,137,141 | tone 8.44-8.59 #136 [tone left, mid] | left | right |
| sanpo_RqOwmltc_0000 | e7 | right | 10.00 | 136,148,150,169 | tone 9.44-9.59 #150 [tone ahead, high] | ahead | right |
| sanpo_RqOwmltc_0000 | e11 | right | 14.20 | 180,182 | tone 12.18-12.33 #182 [tone left, mid] | left | right |
| sanpo_RqOwmltc_0000 | e13 | right | 16.93 | 215,216,230 | tone 15.18-15.33 #215 [tone right, low] | right | right |
| sanpo_RqOwmltc_0000 | e15 | left | 20.80 | 214,231,246,264 | miss |  | ahead |
| sanpo_RqOwmltc_0000 | e16 | right | 21.80 | 235,265,296 | miss |  | right |
| sanpo_RqOwmltc_0000 | e17 | left | 21.93 | 231,280,284,349,350 | miss |  | left |
| sanpo_RqOwmltc_0000 | e22 | right | 25.93 | 146,391,409,415,420,438,455,459 | word 26.23-26.91 #415 Person right. | right | ahead |
| sanpo_UGNwBEZM_0353 | e1 | left | 2.27 | 3,4,19 | word 0.96-1.65 #4 Person left. | left | left |
| sanpo_UGNwBEZM_0353 | e3 | left | 9.33 | 41,54,72,75,85,89,97,104,106,107,110,111,112,116,120,130,131 | tone 6.91-7.06 #106 [tone right, mid] | right | left |
| sanpo_UGNwBEZM_0353 | e4 | left | 12.67 | 112,128,129,132,133,137 | tone 11.11-11.26 #133 [tone left, high] | left | left |
| sanpo_UGNwBEZM_0353 | e5 | left | 17.73 | 158,162,172 | tone 16.84-16.99 #162 [tone left, mid] | left | left |
| sanpo_UGNwBEZM_0353 | e6 | left | 19.33 | 161,189,190 | tone 17.84-17.99 #189 [tone left, high] | left | ahead |
| sanpo_UGNwBEZM_0353 | e7 | left | 20.67 | 204,213,223,229 | miss |  | left |
| sanpo_cBVSUvSN_0000 | e2 | left | 3.07 | 1,31 | tone 2.30-2.45 #31 [tone ahead, high] | ahead | left |
| sanpo_cBVSUvSN_0000 | e4 | left | 7.47 | 55 | miss |  | left |
| sanpo_cBVSUvSN_0000 | e6 | left | 17.20 | 228,230,267,301 | tone 16.18-16.33 #228 [tone right, mid] | right | left |
| sanpo_cBVSUvSN_0000 | e9 | left | 25.07 | 391,405,409,443 | tone 22.44-22.59 #391 [tone right, mid] | right | left |
| sanpo_cBVSUvSN_0000 | e11 | left | 26.27 | 405,409,434,440,446,459 | tone 23.44-23.59 #405 [tone right, mid] | right | left |
| sanpo_cBVSUvSN_0000 | e13 | left | 27.47 | 416,446,451,463,468,470 | word 26.35-27.19 #468 Person ahead. | ahead | left |
| sanpo_cBVSUvSN_0000 | e17 | ahead | 29.87 | 468,502 | miss |  | ahead |
| sanpo_eHxtA669_0000 | e3 | left | 3.07 | 4,6,54,61 | word 0.89-1.58 #4 Person right. | right | left |
| sanpo_eHxtA669_0000 | e4 | right | 21.73 | 727,892 | tone 21.57-21.72 #892 [tone right, mid] | right | right |
| sanpo_eHxtA669_0000 | e5 | left | 24.80 | 839,868,877,881,904,909,921 | tone 22.57-22.72 #921 [tone ahead, mid] | ahead | left |
| sanpo_qn1eNtR0_0029 | e2 | left | 13.87 | 72 | tone 13.04-13.19 #72 [tone left, mid] | left | left |
| sanpo_qn1eNtR0_0029 | e5 | right | 24.13 | 131,142,145 | word 21.70-22.53 #145 Person ahead. | ahead | right |
| sanpo_qn1eNtR0_0029 | e6 | left | 24.80 | 147,150 | tone 23.19-23.34 #150 [tone left, mid] | left | left |

## v4 pick (v3 BASE + {"side": "pred_full", "side_cap": 4.0})

| clip | id | side | t_close | matched tracks | first cue | its side | track side at t_close |
|---|---|---|---|---|---|---|---|
| sanpo_7X41_wkj_0000 | e1 | left | 7.60 | 52,173 | miss |  | left |
| sanpo_7X41_wkj_0000 | e2 | left | 8.67 | 152,240,272 | tone 7.02-7.17 #240 [tone right, mid] | right | left |
| sanpo_7X41_wkj_0000 | e7 | left | 14.93 | 396 | miss |  | ahead |
| sanpo_7X41_wkj_0000 | e8 | left | 17.07 | 411 | miss |  | left |
| sanpo_8WF0e5NO_0195 | e1 | right | 5.87 | 18,19,23 | tone 3.13-3.28 #19 [tone left, mid] | left | right |
| sanpo_8WF0e5NO_0195 | e2 | left | 24.53 | 144 | miss |  | left |
| sanpo_RqOwmltc_0000 | e6 | right | 8.93 | 119,127,136,137,141 | tone 8.44-8.59 #136 [tone right, mid] | right | right |
| sanpo_RqOwmltc_0000 | e7 | right | 10.00 | 136,148,150,169 | tone 9.44-9.59 #150 [tone right, high] | right | right |
| sanpo_RqOwmltc_0000 | e11 | right | 14.20 | 180,182 | tone 12.18-12.33 #182 [tone left, mid] | left | right |
| sanpo_RqOwmltc_0000 | e13 | right | 16.93 | 215,216,230 | tone 15.18-15.33 #215 [tone right, low] | right | right |
| sanpo_RqOwmltc_0000 | e15 | left | 20.80 | 214,231,246,264 | miss |  | ahead |
| sanpo_RqOwmltc_0000 | e16 | right | 21.80 | 235,265,296 | miss |  | right |
| sanpo_RqOwmltc_0000 | e17 | left | 21.93 | 231,280,284,349,350 | miss |  | left |
| sanpo_RqOwmltc_0000 | e22 | right | 25.93 | 146,391,409,415,420,438,455,459 | word 26.23-26.91 #415 Person right. | right | ahead |
| sanpo_UGNwBEZM_0353 | e1 | left | 2.27 | 3,4,19 | word 0.96-1.79 #4 Person ahead. | ahead | left |
| sanpo_UGNwBEZM_0353 | e3 | left | 9.33 | 41,54,72,75,85,89,97,104,106,107,110,111,112,116,120,130,131 | tone 6.91-7.06 #106 [tone right, mid] | right | left |
| sanpo_UGNwBEZM_0353 | e4 | left | 12.67 | 112,128,129,132,133,137 | word 11.16-11.85 #133 Person left. | left | left |
| sanpo_UGNwBEZM_0353 | e5 | left | 17.73 | 158,162,172 | tone 17.04-17.19 #162 [tone right, mid] | right | left |
| sanpo_UGNwBEZM_0353 | e6 | left | 19.33 | 161,189,190 | tone 18.04-18.19 #189 [tone left, high] | left | ahead |
| sanpo_UGNwBEZM_0353 | e7 | left | 20.67 | 204,213,223,229 | miss |  | left |
| sanpo_cBVSUvSN_0000 | e2 | left | 3.07 | 1,31 | tone 2.30-2.45 #31 [tone ahead, high] | ahead | left |
| sanpo_cBVSUvSN_0000 | e4 | left | 7.47 | 55 | miss |  | left |
| sanpo_cBVSUvSN_0000 | e6 | left | 17.20 | 228,230,267,301 | tone 16.18-16.33 #228 [tone right, mid] | right | left |
| sanpo_cBVSUvSN_0000 | e9 | left | 25.07 | 391,405,409,443 | tone 22.44-22.59 #391 [tone right, mid] | right | left |
| sanpo_cBVSUvSN_0000 | e11 | left | 26.27 | 405,409,434,440,446,459 | tone 23.44-23.59 #405 [tone right, mid] | right | left |
| sanpo_cBVSUvSN_0000 | e13 | left | 27.47 | 416,446,451,463,468,470 | word 26.35-27.19 #468 Person ahead. | ahead | left |
| sanpo_cBVSUvSN_0000 | e17 | ahead | 29.87 | 468,502 | miss |  | ahead |
| sanpo_eHxtA669_0000 | e3 | left | 3.07 | 4,6,54,61 | word 0.89-1.58 #4 Person right. | right | left |
| sanpo_eHxtA669_0000 | e4 | right | 21.73 | 727,892 | tone 21.57-21.72 #892 [tone right, mid] | right | right |
| sanpo_eHxtA669_0000 | e5 | left | 24.80 | 839,868,877,881,904,909,921 | tone 22.57-22.72 #921 [tone right, mid] | right | left |
| sanpo_qn1eNtR0_0029 | e2 | left | 13.87 | 72 | tone 13.04-13.19 #72 [tone left, mid] | left | left |
| sanpo_qn1eNtR0_0029 | e5 | right | 24.13 | 131,142,145 | word 21.70-22.39 #145 Person left. | left | right |
| sanpo_qn1eNtR0_0029 | e6 | left | 24.80 | 147,150 | tone 23.19-23.34 #150 [tone left, mid] | left | left |

