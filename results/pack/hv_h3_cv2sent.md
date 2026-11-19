# Pack run: hv_h3_cv2sent (heldout)

Options: {'video_fps': '2', 'video_cv': '1', 'video_style': 'sentence'}. Engine load 0.0 s. Scoring rules in the scripts/eval_pack.py docstring.

| Modality | Pass | Median s | Max s |
|---|---|---|---|
| video | 21/24 | 1.58 | 4.74 |
| all | 21/24 | | |

## Failures

| id | answer | reference | note |
|---|---|---|---|
| h_vid_013 | toward | They move toward each other (one from the top, one from the bottom) until they touch. |  |
| h_vid_022 | 2 | 5 small circles appear one at a time. |  |
| h_vid_024 | down | The small black dot moves diagonally down and to the left (from the top right to the bottom left). |  |
