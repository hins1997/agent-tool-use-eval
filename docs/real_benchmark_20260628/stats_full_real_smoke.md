# Statistical Analysis

- Rows analysed: 108 | Models: claude, deepseek, openai | Cases per model: 36, 36, 36
- Bootstrap resamples: 10000 | Permutations: 20000 | Seed: 20260627

## 1. Mean trajectory score with 95% bootstrap CI

| Model | Mean / 3 | 95% CI | Full-score rate | 95% CI |
|---|---:|---:|---:|---:|
| claude | 1.89 | [1.56, 2.22] | 31% | [17%, 44%] |
| deepseek | 2.33 | [2.03, 2.61] | 53% | [36%, 69%] |
| openai | 2.33 | [2.06, 2.61] | 53% | [36%, 69%] |

> CIs this wide at n=15 are the point: rank order is suggestive, not established. Report it honestly rather than implying precision the sample size does not support.

## 2. Pairwise model comparison (paired permutation test)

| Comparison | Mean diff | Cohen's d | p (raw) | p (Holm) | Significant @0.05 |
|---|---:|---:|---:|---:|:--:|
| claude vs deepseek | -0.44 | -0.46 | 0.002 | 0.005 | yes |
| claude vs openai | -0.44 | -0.47 | 0.015 | 0.031 | yes |
| deepseek vs openai | +0.00 | +0.00 | 1.000 | 1.000 | no |

> Paired design: both models see the identical case set, so the test is on per-case score differences. Holm correction guards against false positives from running several comparisons.

## 3. Scoring-method agreement (Cohen's kappa)

No human-review / judge CSV supplied. Agreement quantifies how far the automatic trajectory label can be trusted as a stand-in for human judgement; fill a `human_review_*.csv` (or run `llm_judge.py`) and pass it with `--review` to populate raw agreement and Cohen's kappa here.

---
_Method: percentile bootstrap, two-sided paired permutation test with add-one smoothing, Holm-Bonferroni multiple-comparison correction, Cohen's kappa for categorical agreement. Standard library only; reproducible via the fixed seed above._
