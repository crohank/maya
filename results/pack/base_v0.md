# Practice pack run: base_v0

Options: defaults. Engine load 5.9 s. Scoring rules in the scripts/eval_pack.py docstring.

| Modality | Pass | Median s | Max s |
|---|---|---|---|
| image | 23/25 | 0.36 | 2.86 |
| audio | 8/20 | 1.60 | 16.89 |
| text | 17/20 | 0.59 | 1.10 |
| video | 8/15 | 0.62 | 1.69 |
| code | 18/20 | 7.55 | 57.76 |
| all | 74/100 | | |

## Failures

| id | answer | reference | note |
|---|---|---|---|
| p_img_010 | 5 | 6 (6 people). A group of friends hanging out in a kitchen together. |  |
| p_img_013 | 3 | There are 4 zebras. |  |
| p_aud_004 | The old servant told him quietly as they crept back to gamewell that this passageway led from the hut in the Pleasants to Sherwood and that Jeffrey for the time | The old servant told him quietly as they crept back to gamewell that this passage way led from the h | wer=0.103 |
| p_aud_009 | The tale about to be told is Solace’s, and it is being addressed to Socrates. | A tale of Solon's, told to Socrates. |  |
| p_aud_011 | I am not sure what this sound is. | Chainsaw. |  |
| p_aud_012 | I am not sure what this sound is. | Clock ticking. |  |
| p_aud_013 | I am not sure what this sound is. | Crackling fire. |  |
| p_aud_014 | I am not sure what this sound is. | Baby crying. |  |
| p_aud_015 | I am not sure what this sound is. | Dog barking. |  |
| p_aud_016 | I am not sure what this sound is. | Helicopter. |  |
| p_aud_017 | I am not sure what this sound is. | Rain. |  |
| p_aud_018 | I am not sure what this sound is. | Rooster crowing. |  |
| p_aud_019 | I am not sure what this sound is. | Ocean waves. |  |
| p_aud_020 | I am not sure what this sound is. | Sneezing. |  |
| p_txt_005 | Architect or engineer | the project coordinator |  |
| p_txt_012 | 2001 | The document does not say. |  |
| p_txt_016 | plants | The document does not say. |  |
| p_vid_001 | 5 shapes appear in the video. | 4 circles appear one at a time. |  |
| p_vid_003 | Green appears first, and red appears last. | A red circle appears first, then blue, and green appears last. |  |
| p_vid_006 | The red circle moves toward the blue rectangle and overlaps with it. | The two shapes move toward each other until they touch. |  |
| p_vid_009 | Once. | The ball bounces 3 times. |  |
| p_vid_010 | Red. | The background ends blue. |  |
| p_vid_011 | 7 | 8 squares appear one at a time. |  |
| p_vid_013 | Red appears first, and yellow appears last. | A yellow square appears first, then red, and blue appears last. |  |
| p_code_006 | def make_a_pile(n):     pile = []     current = n     while current > 0:         pile.append(current)         if n % 2 == 1:  # n is odd             current = c |  def make_a_pile(n):     """     Given a positive integer n, you have to make a pile of n levels of  | timeout |
| p_code_014 | def prime_fib(n: int):     """     prime_fib returns n-th number that is a Fibonacci number and it's also prime.     >>> prime_fib(1)     2     >>> prime_fib(2) |   def prime_fib(n: int):     """     prime_fib returns n-th number that is a Fibonacci number and it | /tmp3l9naq79/t.py", line 61, in <module>     check(prime_fib)   File "/tmp/tmp3l |
