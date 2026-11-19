# Pack run: hv_h0_resample2 (heldout)

Options: {'video_fps': '2', 'video_resample': '1'}. Engine load 0.0 s. Scoring rules in the scripts/eval_pack.py docstring.

| Modality | Pass | Median s | Max s |
|---|---|---|---|
| video | 13/24 | 0.94 | 2.66 |
| all | 13/24 | | |

## Failures

| id | answer | reference | note |
|---|---|---|---|
| h_vid_001 | 5 | 6 triangles appear one at a time. |  |
| h_vid_006 | Orange appears first, and purple appears last. | A purple triangle appears first, then orange, then white, and cyan appears last. |  |
| h_vid_007 | The beige color shows up first, and the black color shows up last. | A brown star appears first, then pink, and black appears last. |  |
| h_vid_014 | 5 | It counts up from 1 to 6; the last number shown is 6. |  |
| h_vid_015 | The final number displayed is 1. | A countdown from 9 to 3; the final number displayed is 3. |  |
| h_vid_016 | Three hexagons remain.   The shapes are orange, cyan, and teal. | 6 hexagons appear, 4 disappear, so 2 are left at the end. |  |
| h_vid_017 | Five shapes are left at the end. | 7 stars appear, 3 disappear, so 4 are left at the end. |  |
| h_vid_019 | One bounce. | The ball bounces 5 times. |  |
| h_vid_021 | Purple. | The background starts pink. |  |
| h_vid_022 | 4 | 5 small circles appear one at a time. |  |
| h_vid_023 | One. | The ball bounces 2 times. |  |
