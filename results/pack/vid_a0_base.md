# Practice pack run: vid_a0_base

Options: {'video_debug': '1'}. Engine load 0.0 s. Scoring rules in the scripts/eval_pack.py docstring.

| Modality | Pass | Median s | Max s |
|---|---|---|---|
| video | 9/15 | 2.18 | 16.44 |
| all | 9/15 | | |

## Failures

| id | answer | reference | note |
|---|---|---|---|
| p_vid_001 | 5 shapes appear in the video. | 4 circles appear one at a time. |  |
| p_vid_003 | Blue appears first, and green appears last. | A red circle appears first, then blue, and green appears last. |  |
| p_vid_007 | 4 | A countdown from 5 to 1; the last number shown is 1. |  |
| p_vid_009 | Once. | The ball bounces 3 times. |  |
| p_vid_011 | 7 | 8 squares appear one at a time. |  |
| p_vid_013 | Red appears first, and yellow appears last. | A yellow square appears first, then red, and blue appears last. |  |
