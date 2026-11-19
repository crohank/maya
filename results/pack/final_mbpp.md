# Pack run: final_mbpp (data/extra/mbpp)

Options: defaults. Engine load 0.0 s. Scoring rules in the scripts/eval_pack.py docstring.

| Modality | Pass | Median s | Max s |
|---|---|---|---|
| code | 25/30 | 6.74 | 52.28 |
| all | 25/30 | | |

## Failures

| id | answer | reference | note |
|---|---|---|---|
| xm_code_002 | def trim_tuple(test_list, K):     """Write a function to trim each tuple by k in the given tuple list.     Example: trim_tuple([(5, 3, 2, 1, 4), (3, 4, 9, 2, 1) | def trim_tuple(test_list, K):   res = []   for ele in test_list:     N = len(ele)     res.append(tup | p/tmpu3or9y0p/t.py", line 16, in check     assert candidate([(5, 3, 2, 1, 4), (3 |
| xm_code_014 | def count_bidirectional(test_list):     """Write a function to count bidirectional tuple pairs.     Example: count_bidirectional([(5, 6), (1, 2), (6, 5), (9, 1) | def count_bidirectional(test_list):   res = 0   for idx in range(0, len(test_list)):     for iidx in | ile "/tmp/tmp4g40w_t4/t.py", line 28, in <module>     check(count_bidirectional) |
| xm_code_018 | import re  def start_withp(words):     """Write a function to return two words from a list of words starting with letter 'p'.     Example: start_withp(["Python  | import re def start_withp(words):  for w in words:         m = re.match("(P\w+)\W(P\w+)", w)         | tmp/tmpspkbtqu1/t.py", line 27, in <module>     check(start_withp)   File "/tmp/ |
| xm_code_023 | def get_Char(strr):     total = sum(ord(char) - ord('a') for char in strr)     result_char = chr((total % 26) + ord('a'))     return chr(((ord(result_char) - or | def get_Char(strr):       summ = 0     for i in range(len(strr)):          summ += (ord(strr[i]) - o | Traceback (most recent call last):   File "/tmp/tmpzka3eopa/t.py", line 14, in < |
| xm_code_027 | def sum_of_digits(nums):     total = 0     for num in nums:         total += sum(int(digit) for digit in str(num))     return total | def sum_of_digits(nums):     return sum(int(el) for n in nums for el in str(n) if el.isdigit()) | of_digits     total += sum(int(digit) for digit in str(num))              ^^^^^^ |
