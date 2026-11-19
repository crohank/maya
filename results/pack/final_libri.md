# Pack run: final_libri (data/extra/librispeech)

Options: defaults. Engine load 0.0 s. Scoring rules in the scripts/eval_pack.py docstring.

| Modality | Pass | Median s | Max s |
|---|---|---|---|
| audio | 34/40 | 1.99 | 4.85 |
| all | 34/40 | | |

## Failures

| id | answer | reference | note |
|---|---|---|---|
| xl_aud_001 | That is all quite true, Mr. Neverbend," said Sir Ferdinand O'Brown. | That is all quite true mister neverbend said sir ferdinando brown. | wer=0.273 |
| xl_aud_002 | In autumn, the woodcutters always came and felled some of the largest trees. | In autumn the wood cutters always came and felled some of the largest trees. | wer=0.143 |
| xl_aud_007 | Those pretty wrongs that liberty commits, When I am some time absent from thy heart, Thy beauty and thy years fall well befits, For still temptation follows whe | Those pretty wrongs that liberty commits when i am sometime absent from thy heart thy beauty and thy | wer=0.103 |
| xl_aud_011 | Why a tongue impressed with honey from every wind? | Why a tongue impress'd with honey from every wind. | wer=0.111 |
| xl_aud_021 | Rao | Raoul. |  |
| xl_aud_028 | Mayhall looked with perplexity up into the top of the hansom. | Alexander Mainhall. |  |
