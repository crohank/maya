# Pack run: final_xh_a (data/extra/humaneval)

Options: defaults. Engine load 0.0 s. Scoring rules in the scripts/eval_pack.py docstring.

| Modality | Pass | Median s | Max s |
|---|---|---|---|
| code | 70/72 | 7.45 | 120.50 |
| all | 70/72 | | |

## Failures

| id | answer | reference | note |
|---|---|---|---|
| xh_code_023 | from typing import List  def remove_duplicates(numbers: List[int]) -> List[int]:     seen = set()     result = []     for num in numbers:         if num not in  | from typing import List   def remove_duplicates(numbers: List[int]) -> List[int]:     """ From a lis | Traceback (most recent call last):   File "/tmp/tmpqe_qu8v6/t.py", line 26, in < |
| xh_code_028 | import math  def poly(xs: list, x: float):     """     Evaluates polynomial with coefficients xs at point x.     return xs[0] + xs[1] * x + xs[1] * x^2 + .... x | import math   def poly(xs: list, x: float):     """     Evaluates polynomial with coefficients xs at | Traceback (most recent call last):   File "/tmp/tmpu63peov7/t.py", line 69, in < |
