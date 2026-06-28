# Statistical Analysis

- Rows analysed: 426 | Models: claude, deepseek, openai | Cases per model: 142, 142, 142
- Bootstrap resamples: 10000 | Permutations: 20000 | Seed: 20260627

## 1. Mean trajectory score with 95% bootstrap CI

| Model | Mean / 3 | 95% CI | Full-score rate | 95% CI |
|---|---:|---:|---:|---:|
| claude | 1.56 | [1.37, 1.76] | 27% | [20%, 35%] |
| deepseek | 1.83 | [1.63, 2.04] | 43% | [35%, 51%] |
| openai | 2.08 | [1.89, 2.27] | 53% | [45%, 61%] |

> CIs this wide at n≈142 per model are the point: rank order is suggestive, not established. Report it honestly rather than implying precision the sample size does not support.

## 2. Pairwise model comparison (paired permutation test)

| Comparison | Mean diff | Cohen's d | p (raw) | p (Holm) | Significant @0.05 |
|---|---:|---:|---:|---:|:--:|
| claude vs deepseek | -0.27 | -0.22 | 0.033 | 0.056 | no |
| claude vs openai | -0.51 | -0.43 | 0.000 | 0.000 | yes |
| deepseek vs openai | -0.25 | -0.20 | 0.028 | 0.056 | no |

> Paired design: both models see the identical case set, so the test is on per-case score differences. Holm correction guards against false positives from running several comparisons.

## 3. Scoring-method agreement (Cohen's kappa)

No human-review / judge CSV supplied. Agreement quantifies how far the automatic trajectory label can be trusted as a stand-in for human judgement; fill a `human_review_*.csv` (or run `llm_judge.py`) and pass it with `--review` to populate raw agreement and Cohen's kappa here.

---
_Method: percentile bootstrap, two-sided paired permutation test with add-one smoothing, Holm-Bonferroni multiple-comparison correction, Cohen's kappa for categorical agreement. Standard library only; reproducible via the fixed seed above._
