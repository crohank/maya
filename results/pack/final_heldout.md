# Pack run: final_heldout (heldout)

Options: defaults. Engine load 0.0 s. Scoring rules in the scripts/eval_pack.py docstring.

| Modality | Pass | Median s | Max s |
|---|---|---|---|
| image | 11/12 | 0.77 | 8.00 |
| audio | 6/6 | 2.09 | 2.85 |
| text | 18/18 | 1.98 | 4.03 |
| video | 22/24 | 1.33 | 3.10 |
| code | 7/8 | 10.31 | 141.39 |
| all | 64/68 | | |

## Failures

| id | answer | reference | note |
|---|---|---|---|
| h_img_009 | 6 | There are 7 apples. |  |
| h_vid_022 | 2 | 5 small circles appear one at a time. |  |
| h_vid_023 | 1 | The ball bounces 2 times. |  |
| h_code_007 | def parse_duration(text):     """text is a duration such as "1h30m15s": hours (h), minutes (m) and seconds (s),     each part optional but always in that order, |  def parse_duration(text):     """text is a duration such as "1h30m15s": hours (h), minutes (m) and  | Traceback (most recent call last):   File "/tmp/tmps789pwnq/t.py", line 50, in < |
