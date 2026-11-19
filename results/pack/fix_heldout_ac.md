# Pack run: fix_heldout_ac (heldout)

Options: defaults. Engine load 0.0 s. Scoring rules in the scripts/eval_pack.py docstring.

| Modality | Pass | Median s | Max s |
|---|---|---|---|
| audio | 6/6 | 2.16 | 5.42 |
| code | 7/8 | 9.46 | 90.90 |
| all | 13/14 | | |

## Failures

| id | answer | reference | note |
|---|---|---|---|
| h_code_007 | def parse_duration(text):     """text is a duration such as "1h30m15s": hours (h), minutes (m) and seconds (s),     each part optional but always in that order, |  def parse_duration(text):     """text is a duration such as "1h30m15s": hours (h), minutes (m) and  | Traceback (most recent call last):   File "/tmp/tmpikz_xxur/t.py", line 50, in < |
