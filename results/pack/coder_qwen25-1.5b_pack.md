# Pack run: coder_qwen25-1.5b_pack (Kaggle Data)

Options: {'coder': 'qwen25-1.5b', 'fallback': 'none'}. Engine load 0.0 s. Scoring rules in the scripts/eval_pack.py docstring.

| Modality | Pass | Median s | Max s |
|---|---|---|---|
| code | 13/20 | 6.34 | 18.53 |
| all | 13/20 | | |

## Failures

| id | answer | reference | note |
|---|---|---|---|
| p_code_002 | def split_words(txt):     import re     # Split on whitespace     words = txt.split()          # If no whitespaces, check for commas     if not words:         w |  def split_words(txt):     '''     Given a string of words, return a list of words split on whitespa | Traceback (most recent call last):   File "/tmp/tmpdrzyee2n/t.py", line 27, in < |
| p_code_006 | def make_a_pile(n):     """     Given a positive integer n, you have to make a pile of n levels of stones.     The first level has n stones.     The number of s |  def make_a_pile(n):     """     Given a positive integer n, you have to make a pile of n levels of  | Traceback (most recent call last):   File "/tmp/tmpo5a5bahl/t.py", line 39, in < |
| p_code_008 | import re  def file_name_check(file_name):     pattern = r'^[a-zA-Z][a-zA-Z0-9]{0,2}\.[txt/exe/dll]$     return "Yes" if re.match(pattern, file_name) else "No" |  def file_name_check(file_name):     """Create a function which takes a string representing a file's |   File "/tmp/tmp0_419oe2/t.py", line 4     pattern = r'^[a-zA-Z][a-zA-Z0-9]{0,2} |
| p_code_013 | def next_smallest(lst):     if len(lst) < 2:         return None          lst.sort()     return lst[1] |  def next_smallest(lst):     """     You are given a list of integers.     Write a function next_sma | Traceback (most recent call last):   File "/tmp/tmpwo1y5odp/t.py", line 23, in < |
| p_code_014 | from math import sqrt  def prime_fib(n: int) -> int:     def is_prime(num: int) -> bool:         if num <= 1:             return False         for i in range(2, |   def prime_fib(n: int):     """     prime_fib returns n-th number that is a Fibonacci number and it | t.py", line 38, in <module>     check(prime_fib)   File "/tmp/tmpny49fagf/t.py", |
| p_code_018 | def rounded_avg(n, m):     if n > m:         return -1          total = sum(range(n, m + 1))     avg = round(total / (m - n + 1))          return bin(avg)[2:] |  def rounded_avg(n, m):     """You are given two positive integers n and m, and your task is to comp | Traceback (most recent call last):   File "/tmp/tmpkw458i_l/t.py", line 30, in < |
| p_code_020 | def f(n):     result = []     for i in range(1, n + 1):         if i % 2 == 0:             result.append(i)         else:             result.append(sum(range(1, |  def f(n):     """ Implement the function f that takes n as a parameter,     and returns a list of s | Traceback (most recent call last):   File "/tmp/tmpj09b4wqe/t.py", line 18, in < |
