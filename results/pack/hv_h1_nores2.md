# Pack run: hv_h1_nores2 (heldout)

Options: {'video_fps': '2'}. Engine load 0.0 s. Scoring rules in the scripts/eval_pack.py docstring.

| Modality | Pass | Median s | Max s |
|---|---|---|---|
| video | 18/24 | 1.15 | 2.85 |
| all | 18/24 | | |

## Failures

| id | answer | reference | note |
|---|---|---|---|
| h_vid_001 | 5 | 6 triangles appear one at a time. |  |
| h_vid_006 | Purple appears first, and purple appears last. | A purple triangle appears first, then orange, then white, and cyan appears last. |  |
| h_vid_016 | Three shapes remain at the end. | 6 hexagons appear, 4 disappear, so 2 are left at the end. |  |
| h_vid_019 | One bounce. The ball bounces once, then stops. | The ball bounces 5 times. |  |
| h_vid_022 | 4 | 5 small circles appear one at a time. |  |
| h_vid_023 | Once. | The ball bounces 2 times. |  |
