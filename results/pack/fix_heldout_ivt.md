# Pack run: fix_heldout_ivt (heldout)

Options: defaults. Engine load 0.0 s. Scoring rules in the scripts/eval_pack.py docstring.

| Modality | Pass | Median s | Max s |
|---|---|---|---|
| image | 11/12 | 0.71 | 7.73 |
| text | 18/18 | 1.79 | 4.19 |
| video | 22/24 | 1.25 | 3.24 |
| all | 51/54 | | |

## Failures

| id | answer | reference | note |
|---|---|---|---|
| h_img_009 | 6 | There are 7 apples. |  |
| h_vid_022 | 2 | 5 small circles appear one at a time. |  |
| h_vid_023 | 1 | The ball bounces 2 times. |  |
