# Pack run: code_xh_a_default (data/extra/humaneval)

Options: defaults. Engine load 0.0 s. Scoring rules in the scripts/eval_pack.py docstring.

| Modality | Pass | Median s | Max s |
|---|---|---|---|
| code | 19/20 | 8.93 | 94.82 |
| all | 19/20 | | |

## Failures

| id | answer | reference | note |
|---|---|---|---|
| xh_code_028 | import math  def poly(xs: list, x: float):     """     Evaluates polynomial with coefficients xs at point x.     return xs[0] + xs[1] * x + xs[1] * x^2 + .... x | import math   def poly(xs: list, x: float):     """     Evaluates polynomial with coefficients xs at | Traceback (most recent call last):   File "/tmp/tmps2gd3m3r/t.py", line 69, in < |
