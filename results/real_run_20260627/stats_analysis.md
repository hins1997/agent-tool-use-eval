# Statistical Analysis

- Rows analysed: 45 | Models: claude, deepseek, openai | Cases per model: 15, 15, 15
- Bootstrap resamples: 10000 | Permutations: 20000 | Seed: 20260627

## 1. Mean trajectory score with 95% bootstrap CI

| Model | Mean / 3 | 95% CI | Full-score rate | 95% CI |
|---|---:|---:|---:|---:|
| claude | 2.27 | [1.67, 2.73] | 67% | [40%, 87%] |
| deepseek | 2.80 | [2.60, 3.00] | 80% | [60%, 100%] |
| openai | 2.40 | [1.80, 2.87] | 73% | [53%, 93%] |

> CIs this wide at n=15 are the point: rank order is suggestive, not established. Report it honestly rather than implying precision the sample size does not support.

## 2. Pairwise model comparison (paired permutation test)

| Comparison | Mean diff | Cohen's d | p (raw) | p (Holm) | Significant @0.05 |
|---|---:|---:|---:|---:|:--:|
| claude vs deepseek | -0.53 | -0.64 | 0.155 | 0.464 | no |
| claude vs openai | -0.13 | -0.12 | 0.873 | 0.873 | no |
| deepseek vs openai | +0.40 | +0.47 | 0.279 | 0.558 | no |

> Paired design: both models see the identical case set, so the test is on per-case score differences. Holm correction guards against false positives from running several comparisons.

## 3. Scoring-method agreement (Cohen's kappa)

Compared automatic trajectory bucket (pass/partial/fail) against the human result score on 45 reviewed items.

| Metric | Value |
|---|---:|
| Raw agreement | 84.4% |
| Cohen's kappa | 0.614 (substantial) |

> Low kappa means the cheap automatic score and the expensive human score disagree often, so the automatic number cannot replace review for those cases; high kappa justifies trusting automation and reviewing only a sample.

---
_Method: percentile bootstrap, two-sided paired permutation test with add-one smoothing, Holm-Bonferroni multiple-comparison correction, Cohen's kappa for categorical agreement. Standard library only; reproducible via the fixed seed above._
