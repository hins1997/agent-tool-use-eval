# Reliability (pass^k) Analysis

- Success = trajectory score >= 3 | seed 20260627

- Trials per (case, model): min 5, max 5

## Per-trial success vs multi-attempt reliability

| Model | cases | trials/case | mean per-case p | pass^1 | pass^2 | pass^3 | pass^5 | worst-case p (10th pct) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| claude | 8 | 5 | 0.12 | 0.12 | 0.09 | 0.08 | 0.06 | 0.02 |
| deepseek | 8 | 5 | 0.38 | 0.38 | 0.30 | 0.27 | 0.22 | 0.06 |
| openai | 8 | 5 | 0.60 | 0.60 | 0.47 | 0.40 | 0.31 | 0.10 |

> pass^1 is the ordinary success rate. The drop from pass^1 to pass^3/pass^5 is the reliability tax that single-shot eval hides. worst-case p surfaces the least reliable cases, not the average.

## Reliability profile (share of cases)

| Model | stably-pass (p>=0.8) | FLAKY (0.2<p<0.8) | stably-fail (p<=0.2) |
|---|---:|---:|---:|
| claude | 12% | 0% | 88% |
| deepseek | 38% | 0% | 62% |
| openai | 38% | 38% | 25% |

> Flaky cases are the operational risk a mean score erases: the agent sometimes does the task and sometimes doesn't. These are the cases to harden, and they only appear with K>1.

## Most flaky cases (per-case success closest to 50%)

- **claude**: no flaky cases (all stably pass or fail).
- **deepseek**: no flaky cases (all stably pass or fail).
- **openai**: BA_TAU03(p≈0.43, 2/5), BCD_DS04_TRANSLATE_RESULT_BINDING(p≈0.60, 3/5), DS02(p≈0.77, 4/5)

---
_Method: per-case success modelled as Beta-Binomial with an empirical-Bayes Beta prior (partial pooling), so small-K per-case estimates borrow strength from the model's global behaviour. pass^k uses posterior-mean per-case probabilities. Standard library only._
