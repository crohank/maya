# Pack run: coder_qwen25-7b_pack (Kaggle Data)

Options: {'coder': 'qwen25-7b', 'fallback': 'none'}. Engine load 0.0 s. Scoring rules in the scripts/eval_pack.py docstring.

| Modality | Pass | Median s | Max s |
|---|---|---|---|
| code | 19/20 | 3.68 | 13.00 |
| all | 19/20 | | |

## Failures

| id | answer | reference | note |
|---|---|---|---|
| p_code_008 | import re  def file_name_check(file_name):     pattern = r'^[a-zA-Z][^\d]*\d{0,3}[^\d]*\.(txt/exe/dll)$'     return 'Yes' if re.match(pattern, file_name) else ' |  def file_name_check(file_name):     """Create a function which takes a string representing a file's | Traceback (most recent call last):   File "/tmp/tmpruc0tmbi/t.py", line 42, in < |
