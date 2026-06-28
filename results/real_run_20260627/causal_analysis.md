# Causal / Experimental-Design Analysis

- Seed 20260627 | bootstrap 10000 | MC 50000 | models: claude, deepseek, openai
- Outcome for binary tests: trajectory full score (==3).

## 0. SRM (sample-ratio mismatch) guard

- Per-model case counts: {'deepseek': 15, 'claude': 15, 'openai': 15}
- Chi-square 0.000, MC p=1.000 -> balanced, comparison not confounded by allocation

## 1. Paired model comparison: blocked effect + McNemar exact

| Comparison | Blocked effect (a-b) | 95% CI | Var. reduction from blocking | McNemar discordant (a>b / b>a) | McNemar p |
|---|---:|---:|---:|:--:|---:|
| claude vs deepseek | -0.53 | [-1.13, +0.00] | -2% | 2 / 4 | 0.688 |
| claude vs openai | -0.13 | [-0.80, +0.53] | 31% | 1 / 2 | 1.000 |
| deepseek vs openai | +0.40 | [-0.07, +1.00] | 12% | 3 / 2 | 1.000 |

> Blocking on case (the paired design) is what makes a small benchmark usable: it strips out case-difficulty variance so the model effect is read from within-case differences. McNemar tests the binary success outcome correctly via discordant pairs.

## 2. CUPED variance reduction on each model's mean score

| Model | Mean/3 | SE before | SE after | Variance reduction | theta |
|---|---:|---:|---:|---:|---:|
| claude | 2.27 | 0.284 | 0.274 | 7% | +0.46 |
| deepseek | 2.80 | 0.107 | 0.106 | 1% | +0.04 |
| openai | 2.40 | 0.289 | 0.270 | 13% | +0.70 |

> CUPED uses a pre-defined covariate (here case difficulty, computed leave-one-out so it carries no information about the focal model) to shrink the variance of the mean estimate without bias — the same lever used to make online experiments more sensitive.

## 3. Causal effect of rewording (paraphrase robustness)

No paraphrase-robustness results supplied. Run `cases_paraphrase_robustness.jsonl` and pass `--robustness-results` + `--robustness-cases` to estimate the rewording effect.

---
_Methods: SRM Monte-Carlo multinomial guard; case-blocked paired effect with cluster bootstrap; McNemar exact binomial on discordant pairs; CUPED with leave-one-out difficulty covariate; paired perturbation contrast. Standard library only; reproducible via the fixed seed._
