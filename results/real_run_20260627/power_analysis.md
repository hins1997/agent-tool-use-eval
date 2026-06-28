# Power & Sample-Size Design

- Cases in this run: 15 | Models: claude, deepseek, openai | alpha=0.05, power=0.8
- Outcome: trajectory score (0-3) for mean tests; full-score (==3) for success tests.

## Observed success (full-score) rates

| Model | success rate |
|---|---:|
| claude | 67% |
| deepseek | 80% |
| openai | 73% |

## 1. Minimum detectable effect at the current N=15

| Comparison | Observed mean diff | SD of paired diff | MDE (80% power) | Detectable now? |
|---|---:|---:|---:|:--:|
| claude vs deepseek | -0.53 | 1.19 | 0.86 | NO |
| claude vs openai | -0.13 | 1.30 | 0.94 | NO |
| deepseek vs openai | +0.40 | 1.12 | 0.81 | NO |

> If the observed difference is below the MDE, the design literally cannot call it significant. At this N you can only detect very large gaps — which is exactly why every comparison came back non-significant. That is a statement about sample size, not models.

## 2. Cases needed to detect a target difference (80% power)

Representative SD of paired trajectory diff (from this run): 1.24

| Target diff | Paired mean test (cases) | Success-rate test 0.80 vs (0.80-Δ), McNemar (cases) |
|---|---:|---:|
| 0.50 | 49 | 31 |
| 0.30 | 135 | 79 |
| 0.20 | 302 | 184 |
| 0.10 | 1207 | 761 |
| 0.05 | 4827 | 3093 |

> Reading: detecting a ~0.10 (trajectory) or ~10pp (success) gap needs on the order of 100-200 cases, not 15. Detecting 5pp needs many hundreds. This sets the case budget.

## 3. Trials per case needed to measure per-case reliability

To estimate ONE case's success probability p to +/- margin (95% CI):

| p (case success) | margin +/-0.20 | margin +/-0.15 | margin +/-0.10 |
|---|---:|---:|---:|
| 0.5 | 25 | 43 | 97 |
| 0.7 | 21 | 36 | 81 |
| 0.8 | 16 | 28 | 62 |
| 0.9 | 9 | 16 | 35 |

> With **1 trial per case** a case's success is a single 0/1 — its per-case reliability is unmeasurable. Even a coarse +/-0.20 estimate needs ~25 trials. So trials-per-case is the lever for *reliability*, not for the headline mean.

## 4. pass^k reliability decay (all k attempts succeed)

| per-trial p | pass^1 | pass^2 | pass^3 | pass^5 | pass^8 |
|---|---:|---:|---:|---:|---:|
| 0.95 | 0.95 | 0.90 | 0.86 | 0.77 | 0.66 |
| 0.90 | 0.90 | 0.81 | 0.73 | 0.59 | 0.43 |
| 0.80 | 0.80 | 0.64 | 0.51 | 0.33 | 0.17 |
| 0.70 | 0.70 | 0.49 | 0.34 | 0.17 | 0.06 |

> tau-bench's point: a 90%-per-trial agent is only 59% reliable over 5 attempts. You cannot even compute this column with 1 trial per case — it requires K>1.

## 5. Cases vs trials under a fixed call budget (the formal answer)

Variance of the headline mean across N cases x K trials:

```
Var(mean)  =  sigma_between^2 / N   +   sigma_within^2 / (N*K)
with fixed total calls C = N*K:
Var(mean)  =  sigma_between^2 / N   +   sigma_within^2 / C
```

- The **within-case term is fixed by the total budget C** regardless of how you split it. Only **N** shrinks the **between-case term**, which dominates on a benchmark. 
- => For the **headline mean / model ranking**, spend the budget on **more CASES** (K small).
- => For **reliability (pass^k) and variance-reducing a paired comparison at temperature>0**, you separately need **K>1 trials per case** (K~5-8). K=1 makes reliability unmeasurable.
- Practical split: pick N from section 2 (power for the comparison you care about), then add K=5-8 only at temperature>0 to measure reliability and average out per-call noise.

---
_Methods: paired/McNemar sample-size formulae, binomial precision, pass^k, and the two-level variance decomposition. See METHODOLOGY_AGENT_EVAL.md for sources. At very small N even these are optimistic — Bowyer et al. (2025) show CLT/bootstrap intervals under-cover below a few hundred points; prefer Bayesian intervals there._
