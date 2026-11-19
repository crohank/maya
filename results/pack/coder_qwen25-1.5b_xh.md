# Pack run: coder_qwen25-1.5b_xh (data/extra/humaneval)

Options: {'coder': 'qwen25-1.5b', 'fallback': 'none'}. Engine load 0.0 s. Scoring rules in the scripts/eval_pack.py docstring.

| Modality | Pass | Median s | Max s |
|---|---|---|---|
| code | 30/40 | 3.50 | 49.39 |
| all | 30/40 | | |

## Failures

| id | answer | reference | note |
|---|---|---|---|
| xh_code_028 | import math  def poly(xs: list, x: float):     """     Evaluates polynomial with coefficients xs at point x.     return xs[0] + xs[1] * x + xs[1] * x^2 + .... x | import math   def poly(xs: list, x: float):     """     Evaluates polynomial with coefficients xs at | timeout |
| xh_code_031 | def fizz_buzz(n: int) -> int:     count = 0     for i in range(11, n, 11):  # Iterate through numbers divisible by 11         count += str(i).count('7')  # Coun |   def fizz_buzz(n: int):     """Return the number of times the digit 7 appears in integers less than | Traceback (most recent call last):   File "/tmp/tmpgsj3rxwd/t.py", line 25, in < |
| xh_code_052 | import math  def largest_prime_factor(n: int):     """Return the largest prime factor of n. Assume n > 1 and is not a prime.     >>> largest_prime_factor(13195) |   def largest_prime_factor(n: int):     """Return the largest prime factor of n. Assume n > 1 and is | Traceback (most recent call last):   File "/tmp/tmpl0o6c7lg/t.py", line 38, in < |
| xh_code_055 | def derivative(xs: list):     return [i * x for i in range(1, len(xs))] |   def derivative(xs: list):     """ xs represent coefficients of a polynomial.     xs[0] + xs[1] * x |    File "/tmp/tmpgelame6l/t.py", line 2, in derivative     return [i * x for i i |
| xh_code_076 | def anti_shuffle(s):     return ' '.join(sorted(word) for word in s.split()) |  def anti_shuffle(s):     """     Write a function that takes a string and returns an ordered versio | n check     assert candidate('Hi') == 'Hi'            ^^^^^^^^^^^^^^^   File "/t |
| xh_code_079 | def encrypt(s):     alphabet = "abcdefghijklmnopqrstuvwxyz"     shifted_alphabet = alphabet[2*2:] + alphabet[:2*2]     result = ""     for char in s:         if |  def encrypt(s):     """Create a function encrypt that takes a string as an argument and     returns | t.py", line 30, in <module>     check(encrypt)   File "/tmp/tmpkrs3724m/t.py", l |
| xh_code_088 | def words_string(s):     # Split the string using comma or space as delimiters     words = s.split(', ')     return words |  def words_string(s):     """     You will be given a string of words separated by commas or spaces. |  "/tmp/tmp_h4av_zf/t.py", line 21, in <module>     check(words_string)   File "/ |
| xh_code_100 | import math  def max_fill(grid, capacity):     total_water = sum(sum(row) for row in grid)     return math.ceil(total_water / capacity) |  def max_fill(grid, capacity):     import math     """     You are given a rectangular grid of wells | Traceback (most recent call last):   File "/tmp/tmpedyh70xh/t.py", line 22, in < |
| xh_code_103 | def get_closest_vowel(word):     vowels = 'aeiouAEIOU'     for i in range(len(word) - 2, -1, -1):         if word[i] not in vowels and word[i + 1] in vowels:    |  def get_closest_vowel(word):     """You are given a word. Your task is to find the closest vowel th | Traceback (most recent call last):   File "/tmp/tmpt6o3juze/t.py", line 29, in < |
| xh_code_118 | def can_arrange(arr):     for i in range(1, len(arr)):         if arr[i] > arr[i-1]:             return i     return -1 |  def can_arrange(arr):     """Create a function which returns the largest index of an element which  | Traceback (most recent call last):   File "/tmp/tmpn6wraog1/t.py", line 19, in < |
