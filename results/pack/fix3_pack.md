# Pack run: fix3_pack (Kaggle Data)

Options: defaults. Engine load 0.0 s. Scoring rules in the scripts/eval_pack.py docstring.

| Modality | Pass | Median s | Max s |
|---|---|---|---|
| image | 24/25 | 1.04 | 13.96 |
| audio | 19/20 | 2.14 | 4.98 |
| video | 15/15 | 1.77 | 3.67 |
| all | 58/60 | | |

## Failures

| id | answer | reference | note |
|---|---|---|---|
| p_img_013 | 3 zebras. | There are 4 zebras. |  |
| p_aud_009 | The tale about solans is about to be told to Socrates. | A tale of Solon's, told to Socrates. |  |
