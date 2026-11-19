# Pack run: vid_a2_nores4 (Kaggle Data)

Options: {'video_fps': '4'}. Engine load 0.0 s. Scoring rules in the scripts/eval_pack.py docstring.

| Modality | Pass | Median s | Max s |
|---|---|---|---|
| video | 11/15 | 2.10 | 3.83 |
| all | 11/15 | | |

## Failures

| id | answer | reference | note |
|---|---|---|---|
| p_vid_001 | 5 | 4 circles appear one at a time. |  |
| p_vid_009 | 1 | The ball bounces 3 times. |  |
| p_vid_011 | 7 | 8 squares appear one at a time. |  |
| p_vid_013 | Red appears first, and yellow appears last. | A yellow square appears first, then red, and blue appears last. |  |
