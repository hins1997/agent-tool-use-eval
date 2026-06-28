# LLM-as-Judge 3x3 Evaluation Report

This report evaluates all three model outputs with all three judge families.

## Scope

- Evaluated traces: `traces_20260627_142501_245424_4818e0b7.jsonl`
- Evaluated models: DeepSeek, OpenAI, Claude
- Judge models: Claude, DeepSeek, OpenAI
- Evaluated items: 45 model outputs = 15 cases x 3 evaluated models
- Intended judge calls: 135 = 45 outputs x 3 judges
- Scored judge rows: 122
- Unparseable judge rows: 13

## Files

- Judge CSV: `judge_20260627_142501_245424_4818e0b7_multi.csv`
- Judge-vs-rule report: `judge_vs_rule_20260627_142501_245424_4818e0b7_multi.md`
- Judge-family bias report: `judge_bias_20260627_142501_245424_4818e0b7_multi.md`

## Parse Reliability

| Judge | Parsed | Parse rate |
|---|---:|---:|
| Claude | 45 / 45 | 100.0% |
| OpenAI | 45 / 45 | 100.0% |
| DeepSeek | 32 / 45 | 71.1% |

DeepSeek judge produced 13 unparseable or empty rows. This should be treated as
a judge reliability issue, not just a scoring result.

## Mean Judge Score

Scores are `result_score + reasoning_score`, max 4.

| Evaluated model | Claude judge | DeepSeek judge | OpenAI judge |
|---|---:|---:|---:|
| Claude output | 2.67 | 3.56 | 2.93 |
| DeepSeek output | 3.60 | 4.00 | 3.47 |
| OpenAI output | 3.27 | 3.64 | 3.27 |

## Self-Judge Bias Check

| Evaluated family | Self mean | Cross-family mean | Delta | Interpretation |
|---|---:|---:|---:|---|
| Claude | 2.67 | 3.17 | -0.50 | possible self-penalty |
| DeepSeek | 4.00 | 3.53 | +0.47 | possible self-preference |
| OpenAI | 3.27 | 3.42 | -0.16 | no large directional signal |

DeepSeek self-judging is the clearest risk signal: DeepSeek gives DeepSeek
outputs a mean of 4.00/4 on the parsed subset, higher than cross-family judges.
Because DeepSeek also has the weakest parse reliability, it should not be used
as the sole formal judge.

## Judge-vs-Human Agreement

Agreement below compares each judge's `result_score_0_2` with the filled human
review `result_score_0_2`.

| Judge | Items | Raw agreement | Cohen's kappa | Interpretation |
|---|---:|---:|---:|---|
| Claude | 45 | 97.8% | 0.940 | almost perfect |
| OpenAI | 45 | 95.6% | 0.880 | almost perfect |
| DeepSeek | 32 | 100.0% | 1.000 | almost perfect on parsed subset |

DeepSeek's kappa is high only on the 32 parsed rows. The 13 unparseable rows
mean its practical reliability is lower than its agreement score alone suggests.

## Rule-vs-Judge Relationship

Across parsed judge rows:

- Rule trajectory mean: 2.582 / 3
- Judge total mean: 3.344 / 4
- Pearson correlation between rule trajectory and judge total: 0.913

Largest disagreements are useful calibration cases:

- `L04 / deepseek`: rule gave partial credit, judges strongly penalized invented contact handling.
- `A05 / claude`: rule trajectory passed, judges penalized overclaiming around destructive deletion.
- `B05 / claude`: rule penalized missing `create_event`, judge partially credited the useful calendar check.
- `B04 / claude`: judge caught fabricated search content when the tool was not actually called.

## Conclusion

The correct evaluation design is not "judge only one model's outputs". It is the
full evaluated-model x judge-family matrix.

For this run:

- Claude and OpenAI are the most reliable judges operationally because they
  parsed all 45 items and aligned strongly with human review.
- DeepSeek is useful as an audit judge but not reliable enough as the primary
  judge because 13/45 rows were unparseable.
- Self-judge output should remain diagnostic only. DeepSeek self-judging shows
  a possible self-preference signal; Claude shows possible self-penalty; OpenAI
  does not show a large directional self-judge signal in this run.
- Formal reporting should use a fixed cross-family primary judge, plus
  cross-family audit and human-review calibration.
