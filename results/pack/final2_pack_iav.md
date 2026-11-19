# Pack run: final2_pack_iav (Kaggle Data)

Options: defaults. Engine load 0.0 s. Scoring rules in the scripts/eval_pack.py docstring.

| Modality | Pass | Median s | Max s |
|---|---|---|---|
| image | 24/25 | 0.61 | 12.54 |
| audio | 19/20 | 1.71 | 3.82 |
| video | 15/15 | 1.60 | 2.81 |
| all | 58/60 | | |

## Failures

| id | answer | reference | note |
|---|---|---|---|
| p_img_013 | 3 zebras. | There are 4 zebras. |  |
| p_aud_009 | The tale about solans is about to be told to Socrates. | A tale of Solon's, told to Socrates. |  |
