# Pack run: coder_qwen25-7b_xh (data/extra/humaneval)

Options: {'coder': 'qwen25-7b', 'fallback': 'none'}. Engine load 0.0 s. Scoring rules in the scripts/eval_pack.py docstring.

| Modality | Pass | Median s | Max s |
|---|---|---|---|
| code | 37/40 | 4.02 | 20.29 |
| all | 37/40 | | |

## Failures

| id | answer | reference | note |
|---|---|---|---|
| xh_code_058 | def circular_shift(x, shift):     """Circular shift the digits of the integer x, shift the digits right by shift     and return the result as a string.     If s |  def circular_shift(x, shift):     """Circular shift the digits of the integer x, shift the digits r | Traceback (most recent call last):   File "/tmp/tmp1j5auxzk/t.py", line 31, in < |
| xh_code_088 | def words_string(s):     import re     return re.split(r'[,\s]+', s) |  def words_string(s):     """     You will be given a string of words separated by commas or spaces. | ck(words_string)   File "/tmp/tmpidb_lfr8/t.py", line 12, in check     assert ca |
| xh_code_100 | import math  def max_fill(grid, capacity):     total_water = sum(sum(row) for row in grid)     return math.ceil(total_water / capacity) |  def max_fill(grid, capacity):     import math     """     You are given a rectangular grid of wells | Traceback (most recent call last):   File "/tmp/tmp8zqy7e3i/t.py", line 22, in < |
