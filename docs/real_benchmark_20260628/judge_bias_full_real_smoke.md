# Judge Diversity and Bias Audit

## Scope

- Judge rows: 324
- Evaluated model families: claude, deepseek, openai
- Judge families: claude, deepseek, openai
- Self-judge rows: 108

## Mean Judge Total Score Matrix

Scores are `result_score + reasoning_score`, max 4. Diagonal cells are self-family judging and should be treated as diagnostic, not sole ranking evidence.

| Evaluated family | claude | deepseek | openai |
|---|---:|---:|---:|
| claude | 2.94 (n=36) SELF | 2.97 (n=36) | 2.94 (n=36) |
| deepseek | 3.42 (n=36) | 3.39 (n=36) SELF | 3.00 (n=36) |
| openai | 3.89 (n=36) | 3.81 (n=36) | 3.72 (n=36) SELF |

## Self-Judge Delta

| Family | Self mean | Cross-family mean | Delta | Interpretation |
|---|---:|---:|---:|---|
| claude | 2.94 | 2.96 | -0.01 | no large directional signal |
| deepseek | 3.39 | 3.21 | +0.18 | no large directional signal |
| openai | 3.72 | 3.85 | -0.12 | no large directional signal |

## Highest Inter-Judge Spread

| Case | Model | Scores by judge family | Spread |
|---|---|---|---:|
| L01 | deepseek | claude:4, deepseek:0, openai:3 | 4 |
| PL01 | deepseek | claude:4, deepseek:4, openai:0 | 4 |
| PL03 | deepseek | claude:4, deepseek:4, openai:0 | 4 |
| AB11 | claude | claude:0, deepseek:0, openai:4 | 4 |
| AB11 | deepseek | claude:3, deepseek:4, openai:0 | 4 |
| L01 | openai | claude:4, deepseek:1, openai:4 | 3 |
| SR05 | deepseek | claude:4, deepseek:4, openai:1 | 3 |
| AC02 | openai | claude:4, deepseek:4, openai:1 | 3 |
| AC02 | deepseek | claude:1, deepseek:0, openai:3 | 3 |
| PL01 | claude | claude:4, deepseek:4, openai:2 | 2 |

## Operating Rule

- Use one fixed cross-family primary judge for comparable full-run scoring.
- Use additional judge families for stratified audit samples, especially large rule-vs-judge disagreements and close model comparisons.
- Do not use a self-family judge as the only formal evidence for that model's score.
- Treat self-judge deltas as bias diagnostics; calibrate them against human gold labels before changing rankings.
