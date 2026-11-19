# Pack run: code_xh_b_nocheck (data/extra/humaneval)

Options: {'coder': 'vlm', 'selfcheck': '0'}. Engine load 0.0 s. Scoring rules in the scripts/eval_pack.py docstring.

| Modality | Pass | Median s | Max s |
|---|---|---|---|
| code | 17/20 | 6.85 | 19.48 |
| all | 17/20 | | |

## Failures

| id | answer | reference | note |
|---|---|---|---|
| xh_code_079 | def encrypt(s):     encrypted = ""     for char in s:         if 'a' <= char <= 'z':             # Shift down by 2 places in the alphabet (0-25)             shi |  def encrypt(s):     """Create a function encrypt that takes a string as an argument and     returns | t.py", line 33, in <module>     check(encrypt)   File "/tmp/tmpqnm1lbu5/t.py", l |
| xh_code_100 | def max_fill(grid, capacity):     import math          total_water = 0     for row in grid:         total_water += sum(row)          # Each bucket can hold 'cap |  def max_fill(grid, capacity):     import math     """     You are given a rectangular grid of wells | Traceback (most recent call last):   File "/tmp/tmpsnlauofd/t.py", line 27, in < |
| xh_code_118 | def can_arrange(arr):     if len(arr) <= 1:         return -1          for i in range(1, len(arr)):         if arr[i] <= arr[i-1]:             return i          |  def can_arrange(arr):     """Create a function which returns the largest index of an element which  | Traceback (most recent call last):   File "/tmp/tmpgcxvt7bd/t.py", line 23, in < |
