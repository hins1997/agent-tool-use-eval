# Judge Diversity and Bias Audit

## Scope

- Judge rows: 73
- Evaluated model families: claude, deepseek, openai
- Judge families: claude, deepseek, openai
- Self-judge rows: 24

## Mean Judge Total Score Matrix

Scores are `result_score + reasoning_score`, max 4. Diagonal cells are self-family judging and should be treated as diagnostic, not sole ranking evidence.

| Evaluated family | claude | deepseek | openai |
|---|---:|---:|---:|
| claude | 2.17 (n=6) SELF | 2.12 (n=8) | 1.75 (n=8) |
| deepseek | 2.00 (n=10) | 2.17 (n=12) SELF | 2.00 (n=12) |
| openai | 2.40 (n=5) | 2.67 (n=6) | 2.33 (n=6) SELF |

## Self-Judge Delta

| Family | Self mean | Cross-family mean | Delta | Interpretation |
|---|---:|---:|---:|---|
| claude | 2.17 | 1.94 | +0.23 | no large directional signal |
| deepseek | 2.17 | 2.00 | +0.17 | no large directional signal |
| openai | 2.33 | 2.55 | -0.21 | no large directional signal |

## Highest Inter-Judge Spread

| Case | Model | Scores by judge family | Spread |
|---|---|---|---:|
| PL04 | claude | claude:4, deepseek:2, openai:1 | 3 |
| PL04 | deepseek | claude:4, deepseek:2, openai:1 | 3 |
| BCD_PL03_ONLY_PLAN_NO_TOOLS | openai | claude:4, deepseek:4, openai:2 | 2 |
| PB02 | claude | claude:4, deepseek:4, openai:3 | 1 |
| BCD_PL03_ONLY_PLAN_NO_TOOLS | deepseek | deepseek:4, openai:3 | 1 |
| BCD_DS04_TRANSLATE_RESULT_BINDING | claude | deepseek:3, openai:2 | 1 |
| BCD_ABM01_CLARIFY_BEFORE_TOOL | claude | claude:1, deepseek:0, openai:0 | 1 |
| B12 | deepseek | claude:0, deepseek:0, openai:0 | 0 |
| PB10 | openai | claude:0, deepseek:0, openai:0 | 0 |
| PB10 | claude | claude:0, deepseek:0, openai:0 | 0 |

## Operating Rule

- Use one fixed cross-family primary judge for comparable full-run scoring.
- Use additional judge families for stratified audit samples, especially large rule-vs-judge disagreements and close model comparisons.
- Do not use a self-family judge as the only formal evidence for that model's score.
- Treat self-judge deltas as bias diagnostics; calibrate them against human gold labels before changing rankings.
