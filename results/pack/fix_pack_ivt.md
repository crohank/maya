# Pack run: fix_pack_ivt (Kaggle Data)

Options: defaults. Engine load 0.0 s. Scoring rules in the scripts/eval_pack.py docstring.

| Modality | Pass | Median s | Max s |
|---|---|---|---|
| image | 23/25 | 0.35 | 7.61 |
| text | 19/20 | 2.83 | 5.42 |
| video | 15/15 | 1.45 | 2.94 |
| all | 57/60 | | |

## Failures

| id | answer | reference | note |
|---|---|---|---|
| p_img_010 | 5 | 6 (6 people). A group of friends hanging out in a kitchen together. |  |
| p_img_013 | 3 | There are 4 zebras. |  |
| p_txt_005 | The architect or engineer. | the project coordinator |  |
