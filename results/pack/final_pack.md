# Pack run: final_pack (Kaggle Data)

Options: defaults. Engine load 0.0 s. Scoring rules in the scripts/eval_pack.py docstring.

| Modality | Pass | Median s | Max s |
|---|---|---|---|
| image | 23/25 | 0.34 | 6.91 |
| audio | 19/20 | 1.69 | 3.15 |
| text | 19/20 | 2.52 | 5.08 |
| video | 15/15 | 1.44 | 2.63 |
| code | 20/20 | 6.66 | 39.96 |
| all | 96/100 | | |

## Failures

| id | answer | reference | note |
|---|---|---|---|
| p_img_010 | 5 | 6 (6 people). A group of friends hanging out in a kitchen together. |  |
| p_img_013 | 3 | There are 4 zebras. |  |
| p_aud_009 | The tale about solans is about to be told to Socrates. | A tale of Solon's, told to Socrates. |  |
| p_txt_005 | The architect or engineer. | the project coordinator |  |
