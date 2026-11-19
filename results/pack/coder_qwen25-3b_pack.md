# Pack run: coder_qwen25-3b_pack (Kaggle Data)

Options: {'coder': 'qwen25-3b', 'fallback': 'none'}. Engine load 0.0 s. Scoring rules in the scripts/eval_pack.py docstring.

| Modality | Pass | Median s | Max s |
|---|---|---|---|
| code | 18/20 | 9.28 | 16.34 |
| all | 18/20 | | |

## Failures

| id | answer | reference | note |
|---|---|---|---|
| p_code_002 | def split_words(txt):     '''     Given a string of words, return a list of words split on whitespace, if no whitespaces exists in the text you     should split |  def split_words(txt):     '''     Given a string of words, return a list of words split on whitespa | Traceback (most recent call last):   File "/tmp/tmpk23drxov/t.py", line 30, in < |
| p_code_008 | import re  def file_name_check(file_name):     """Create a function which takes a string representing a file's name, and returns     'Yes' if the the file's nam |  def file_name_check(file_name):     """Create a function which takes a string representing a file's | Traceback (most recent call last):   File "/tmp/tmpqx8zpi8z/t.py", line 61, in < |
