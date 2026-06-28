# DeepSeek Judge Root-Cause and Repair Report

## Root Cause Verified

The previous DeepSeek judge empty rows were caused primarily by insufficient completion budget, not by unjudgeable cases.

Raw API probing showed:

- `finish_reason = length`
- visible `content_len = 0`
- `completion_tokens = 512`
- `reasoning_tokens = 512`

DeepSeek consumed the entire 512-token completion budget in internal reasoning, leaving no visible JSON for the parser. This explains complete empty outputs such as `unparseable:`. Some rows also had malformed or truncated JSON, so the parser was made more tolerant as a second fix.

## Code Fix

- Increased judge max output budget from 512 to configurable `JUDGE_MAX_TOKENS`, default `2048`.
- Added `response_format={"type":"json_object"}` for DeepSeek judge calls.
- Added partial-JSON recovery for truncated JSON containing `result_score` and `reasoning_score`.
- Added regression test for truncated JSON recovery.

## Repair Validation

| Dataset | DeepSeek parsed | Empty/unparseable |
|---|---:|---:|
| Before fix, full 3x3 run | 32 / 45 | 13 |
| After fix, targeted 13-case repair | 13 / 13 | 0 |
| After merging repaired rows | 45 / 45 | 0 |

## Judge-vs-Human After Repair

| Judge | Items | Mean total / 4 | Raw agreement | Cohen's kappa |
|---|---:|---:|---:|---:|
| openai | 45 | 3.222 | 95.6% | 0.880 |
| claude | 45 | 3.178 | 97.8% | 0.940 |
| deepseek | 45 | 3.178 | 93.3% | 0.811 |

## DeepSeek Scores After Repair by Evaluated Model

| Evaluated model | Items | Mean DeepSeek judge total / 4 | Distribution |
|---|---:|---:|---|
| claude | 15 | 2.533 | {0: 4, 1: 2, 4: 9} |
| deepseek | 15 | 3.667 | {0: 1, 3: 1, 4: 13} |
| openai | 15 | 3.333 | {0: 2, 2: 1, 4: 12} |

## Decision Update

The failure was fixable. DeepSeek should no longer be rejected because of empty outputs under the old 512-token budget. However, OpenAI remains the formal primary judge for this project because that is the selected evaluation policy and it remains stable with high human agreement. Claude and DeepSeek can both serve as cross judges after the repair, with DeepSeek parse reliability now verified on the repaired set.

## Repaired Artifacts

- `judge_deepseek_empty_cases_repaired.csv`
- `judge_20260627_142501_245424_4818e0b7_multi_repaired.csv`
- `judge_bias_20260627_142501_245424_4818e0b7_multi_repaired.md`
- `judge_vs_rule_20260627_142501_245424_4818e0b7_multi_repaired.md`
