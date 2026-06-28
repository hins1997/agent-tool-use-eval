# Perturbation Causal Effects (robustness = real capability)

- seed 20260627 | each effect = score(variant) - score(canonical), paired on the base task
- Outcome: trajectory score (0-3). Negative effect = perturbation lowered the score.

## Overall sensitivity to surface change (per model)

| Model | contrasts | mean effect | 95% CI | p (sign-flip) | phrasing-dependent? |
|---|---:|---:|---:|---:|:--:|
| claude | 105 | -0.50 | [-0.85, -0.16] | 0.005 | yes |
| deepseek | 105 | -0.69 | [-0.93, -0.44] | 0.000 | yes |
| openai | 105 | -0.47 | [-0.74, -0.20] | 0.001 | yes |

> CI excluding 0 = the model's score moves causally with pure rewording, i.e. part of its score is phrasing, not capability. A negative mean is the worrying direction.

## Effect by perturbation type (which surface change hurts)

| Model | perturbation | n | mean effect | 95% CI | p (sign-flip) |
|---|---|---:|---:|---:|---:|
| claude | distractor | 15 | -0.07 | [-1.00, +0.87] | 1.000 |
| claude | injection_reword | 15 | -1.80 | [-2.60, -1.00] | 0.004 |
| claude | language_shift | 15 | -0.07 | [-0.67, +0.53] | 1.000 |
| claude | paraphrase | 15 | -0.20 | [-0.60, +0.00] | 1.000 |
| claude | polite_pressure | 15 | -1.80 | [-2.60, -0.80] | 0.013 |
| claude | reorder | 15 | +0.07 | [-0.93, +1.07] | 1.000 |
| claude | symbol_reformat | 15 | +0.33 | [-0.40, +1.07] | 0.618 |
| deepseek | distractor | 15 | -0.33 | [-0.80, +0.00] | 0.252 |
| deepseek | injection_reword | 15 | -2.47 | [-2.93, -1.93] | 0.000 |
| deepseek | language_shift | 15 | -0.13 | [-0.53, +0.27] | 0.751 |
| deepseek | paraphrase | 15 | -0.07 | [-0.40, +0.33] | 1.000 |
| deepseek | polite_pressure | 15 | -1.87 | [-2.60, -1.07] | 0.002 |
| deepseek | reorder | 15 | +0.07 | [-0.20, +0.40] | 1.000 |
| deepseek | symbol_reformat | 15 | +0.00 | [+0.00, +0.00] | 1.000 |
| openai | distractor | 15 | +0.07 | [-0.40, +0.53] | 1.000 |
| openai | injection_reword | 15 | -1.27 | [-2.13, -0.27] | 0.037 |
| openai | language_shift | 15 | +0.13 | [-0.13, +0.47] | 0.753 |
| openai | paraphrase | 15 | -0.20 | [-0.80, +0.40] | 0.756 |
| openai | polite_pressure | 15 | -1.87 | [-2.67, -0.93] | 0.007 |
| openai | reorder | 15 | +0.20 | [+0.00, +0.60] | 1.000 |
| openai | symbol_reformat | 15 | -0.33 | [-0.87, +0.07] | 0.378 |

> This localises the fragility: e.g. a model robust to paraphrase but not to language_shift or injection_reword tells you exactly which surface invariance it lacks — actionable for both data construction and product guardrails.

---
_Method: paired contrast vs the canonical phrasing (task held fixed => no difficulty confound); cluster bootstrap CI over base tasks; sign-flip permutation test of the sharp null that the perturbation has no effect. Standard library only._
