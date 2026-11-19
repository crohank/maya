# Pack run: vid_a1_nores2 (Kaggle Data)

Options: {'video_fps': '2'}. Engine load 0.0 s. Scoring rules in the scripts/eval_pack.py docstring.

| Modality | Pass | Median s | Max s |
|---|---|---|---|
| video | 11/15 | 1.48 | 9.85 |
| all | 11/15 | | |

## Failures

| id | answer | reference | note |
|---|---|---|---|
| p_vid_001 | 5 shapes appear in the video. | 4 circles appear one at a time. |  |
| p_vid_009 | Once. | The ball bounces 3 times. |  |
| p_vid_011 | 7 | 8 squares appear one at a time. |  |
| p_vid_013 | Red appears first, and blue appears last. | A yellow square appears first, then red, and blue appears last. |  |
