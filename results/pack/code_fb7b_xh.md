# Pack run: code_fb7b_xh (data/extra/humaneval)

Options: {'fallback': 'qwen25-7b'}. Engine load 0.0 s. Scoring rules in the scripts/eval_pack.py docstring.

| Modality | Pass | Median s | Max s |
|---|---|---|---|
| code | 37/40 | 6.44 | 124.97 |
| all | 37/40 | | |

## Failures

| id | answer | reference | note |
|---|---|---|---|
| xh_code_028 | import math  def poly(xs: list, x: float):     """     Evaluates polynomial with coefficients xs at point x.     return xs[0] + xs[1] * x + xs[1] * x^2 + .... x | import math   def poly(xs: list, x: float):     """     Evaluates polynomial with coefficients xs at | Traceback (most recent call last):   File "/tmp/tmp2pgij09_/t.py", line 69, in < |
| xh_code_100 | def max_fill(grid, capacity):     import math          total_water = 0     for row in grid:         total_water += sum(row)          # Each bucket can hold 'cap |  def max_fill(grid, capacity):     import math     """     You are given a rectangular grid of wells | Traceback (most recent call last):   File "/tmp/tmpav_0maq9/t.py", line 27, in < |
| xh_code_118 | def can_arrange(arr):     if len(arr) <= 1:         return -1          for i in range(1, len(arr)):         if arr[i] <= arr[i-1]:             return i          |  def can_arrange(arr):     """Create a function which returns the largest index of an element which  | Traceback (most recent call last):   File "/tmp/tmpyn7zifxc/t.py", line 23, in < |
