# Pack run: coder_qwen25-3b_xh (data/extra/humaneval)

Options: {'coder': 'qwen25-3b', 'fallback': 'none'}. Engine load 0.0 s. Scoring rules in the scripts/eval_pack.py docstring.

| Modality | Pass | Median s | Max s |
|---|---|---|---|
| code | 34/40 | 7.54 | 48.37 |
| all | 34/40 | | |

## Failures

| id | answer | reference | note |
|---|---|---|---|
| xh_code_028 | import math  def poly(xs: list, x: float):     """     Evaluates polynomial with coefficients xs at point x.     return xs[0] + xs[1] * x + xs[1] * x^2 + .... x | import math   def poly(xs: list, x: float):     """     Evaluates polynomial with coefficients xs at | Traceback (most recent call last):   File "/tmp/tmpc12231jw/t.py", line 64, in < |
| xh_code_058 | def circular_shift(x, shift):     """Circular shift the digits of the integer x, shift the digits right by shift     and return the result as a string.     If s |  def circular_shift(x, shift):     """Circular shift the digits of the integer x, shift the digits r | Traceback (most recent call last):   File "/tmp/tmph_6cwlss/t.py", line 33, in < |
| xh_code_088 | def words_string(s):     """     You will be given a string of words separated by commas or spaces. Your task is     to split the string into words and return a |  def words_string(s):     """     You will be given a string of words separated by commas or spaces. | ck(words_string)   File "/tmp/tmpn_bdbsoa/t.py", line 21, in check     assert ca |
| xh_code_094 | from typing import List  def move_one_ball(arr: List[int]) -> bool:     if not arr:         return True          n = len(arr)     # Find the index where the arr |  def move_one_ball(arr):     """We have an array 'arr' of N integers arr[1], arr[2], ..., arr[N].The | Traceback (most recent call last):   File "/tmp/tmpia6nc026/t.py", line 28, in < |
| xh_code_100 | import math from typing import List  def max_fill(grid: List[List[int]], capacity: int) -> int:     total_water = sum(row.count(1) for row in grid)     return m |  def max_fill(grid, capacity):     import math     """     You are given a rectangular grid of wells | Traceback (most recent call last):   File "/tmp/tmpeibu8_h4/t.py", line 23, in < |
| xh_code_118 | def can_arrange(arr):     """Create a function which returns the largest index of an element which     is not greater than or equal to the element immediately p |  def can_arrange(arr):     """Create a function which returns the largest index of an element which  | Traceback (most recent call last):   File "/tmp/tmpn0yxyepa/t.py", line 28, in < |
