# Pack run: code_xh_b_default (data/extra/humaneval)

Options: defaults. Engine load 0.0 s. Scoring rules in the scripts/eval_pack.py docstring.

| Modality | Pass | Median s | Max s |
|---|---|---|---|
| code | 18/20 | 6.53 | 41.44 |
| all | 18/20 | | |

## Failures

| id | answer | reference | note |
|---|---|---|---|
| xh_code_100 | def max_fill(grid, capacity):     import math          total_water = 0     for row in grid:         total_water += sum(row)          # Each bucket can hold 'cap |  def max_fill(grid, capacity):     import math     """     You are given a rectangular grid of wells | Traceback (most recent call last):   File "/tmp/tmpgeeeq0of/t.py", line 27, in < |
| xh_code_118 | def can_arrange(arr):     if len(arr) <= 1:         return -1          for i in range(1, len(arr)):         if arr[i] <= arr[i-1]:             return i          |  def can_arrange(arr):     """Create a function which returns the largest index of an element which  | Traceback (most recent call last):   File "/tmp/tmpm8jgf3lw/t.py", line 23, in < |
