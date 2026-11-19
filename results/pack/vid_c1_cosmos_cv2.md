# Pack run: vid_c1_cosmos_cv2 (Kaggle Data)

Options: {'video_model': 'cosmos', 'video_debug': '1'}. Engine load 0.0 s. Scoring rules in the scripts/eval_pack.py docstring.

| Modality | Pass | Median s | Max s |
|---|---|---|---|
| video | 6/15 | 1.54 | 4.20 |
| all | 6/15 | | |

## Failures

| id | answer | reference | note |
|---|---|---|---|
| p_vid_002 | The red square moves downward. | The red square moves to the right. |  |
| p_vid_003 | Red appears first, and green appears last. | A red circle appears first, then blue, and green appears last. |  |
| p_vid_004 | The sign says OPEN at the start and CLOSE at the end. | The sign says "OPEN" at the start and "CLOSED" at the end. |  |
| p_vid_006 | The blue square and red circle merge into a single shape. | The two shapes move toward each other until they touch. |  |
| p_vid_007 | 1 | A countdown from 5 to 1; the last number shown is 1. |  |
| p_vid_008 | 2 | 5 squares appear, 2 disappear, so 3 are left at the end. |  |
| p_vid_010 | Blue. | The background ends blue. |  |
| p_vid_013 | Yellow appears first, and blue appears last. | A yellow square appears first, then red, and blue appears last. |  |
| p_vid_014 | The sign says PUSH at the start and it says PULL at the end. | The sign says "PUSH" at the start and "PULL" at the end. |  |
