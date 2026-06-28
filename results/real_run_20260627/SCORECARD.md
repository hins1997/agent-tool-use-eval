# Agent Eval Scorecard

- Framework: Agent Behavior Eval Framework
- Manifest version: 0.3.0
- Positioning: Trace-first agent behavior evaluation for tool-use reliability and autonomy boundary control.

## Executive Decision

- Best human-reviewed model in this run: deepseek (6.40 / 7 mean reviewed total).
- Best primary-judge model in this run: deepseek (3.47 / 4 mean OpenAI-judge total).
- Ranking strength: directional only; the statistical report did not find pairwise significance at alpha=0.05.
- Coverage warning: 2 P0 suite(s) have no observed rows in this run.

## Suite Coverage

| Suite | Case file | Module | Manifest cases | Priority | Observed rows |
|---|---|---|---:|---|---:|
| tool_use_reliability | cases_all40.jsonl | tool_use | 44 | P0 | 45 |
| autonomy_boundary_single_turn | cases_autonomy_boundary.jsonl | autonomy_boundary | 16 | P0 | 0 |
| autonomy_boundary_multiturn | cases_autonomy_multiturn.jsonl | autonomy_boundary | 9 | P0 | 0 |
| permission_boundary | cases_permission_boundary.jsonl | autonomy_boundary | 12 | P1 | 0 |
| stateful_tool_sandbox | cases_stateful_tools.jsonl | tool_use | 6 | P1 | 0 |
| dynamic_user_simulation | cases_dynamic_autonomy.jsonl | autonomy_boundary | 4 | P1 | 0 |
| agentic_coding | cases_agentic_coding.jsonl | tool_use | 4 | P2 | 0 |
| browser_web | cases_browser_web.jsonl | tool_use | 4 | P2 | 0 |
| tool_use_multiturn | cases_multiturn.jsonl | tool_use | n/a | P1 | 0 |
| paraphrase_robustness | cases_paraphrase_robustness.jsonl | robustness | n/a | P1 | 0 |

Missing P0 coverage:

- autonomy_boundary_single_turn (16 manifest cases) has no observed rows in this run.
- autonomy_boundary_multiturn (9 manifest cases) has no observed rows in this run.

## Rule Score By Model

| Model | Rows | Mean total score | Mean trajectory score |
|---|---:|---:|---:|
| claude | 15 | n/a | 2.27 |
| deepseek | 15 | n/a | 2.80 |
| openai | 15 | n/a | 2.40 |

## Human Review Coverage

- Review rows: 45
- Rows with human scores: 45

| Model | Rows | Mean reviewed total | Mean result | Mean reasoning |
|---|---:|---:|---:|---:|
| claude | 15 | 5.07 | 1.40 | 1.40 |
| deepseek | 15 | 6.40 | 1.87 | 1.73 |
| openai | 15 | 5.73 | 1.67 | 1.67 |

## Judge Score By Model

- Primary judge: openai
- Cross judges: claude, deepseek

| Judge | Evaluated model | Rows | Mean result | Mean reasoning | Self-judge rows |
|---|---|---:|---:|---:|---:|
| claude | claude | 15 | 1.33 | 1.33 | 15 |
| claude | deepseek | 15 | 1.87 | 1.73 | 0 |
| claude | openai | 15 | 1.67 | 1.60 | 0 |
| deepseek | claude | 15 | 1.27 | 1.27 | 0 |
| deepseek | deepseek | 15 | 1.87 | 1.80 | 15 |
| deepseek | openai | 15 | 1.73 | 1.60 | 0 |
| openai | claude | 15 | 1.47 | 1.47 | 0 |
| openai | deepseek | 15 | 1.80 | 1.67 | 0 |
| openai | openai | 15 | 1.67 | 1.60 | 15 |

Primary-judge totals:

| Evaluated model | Rows | Mean primary-judge total / 4 |
|---|---:|---:|
| claude | 15 | 2.93 |
| deepseek | 15 | 3.47 |
| openai | 15 | 3.27 |

## Top Failure Types

| Failure type | Count |
|---|---:|
| manual_behavior_review | 6 |
| tool_selection_or_order_failure | 5 |
| parameter_error | 2 |
| unnecessary_tool_call | 2 |
| api_error | 2 |
| planning_failure | 1 |

## Evidence Index

| Artifact | Path |
|---|---|
| Results CSV | `results/real_run_20260627/eval_results_20260627_142501_245424_4818e0b7.csv` |
| Human review CSV | `results/real_run_20260627/human_review_20260627_142501_245424_4818e0b7.csv` |
| Judge CSV | `results/real_run_20260627/judge_20260627_142501_245424_4818e0b7_multi_repaired.csv` |
| Statistics report | `results/real_run_20260627/stats_analysis.md` |
| Causal report | `results/real_run_20260627/causal_analysis.md` |
| Power report | `results/real_run_20260627/power_analysis.md` |
| Judge-vs-rule report | `results/real_run_20260627/judge_vs_rule_20260627_142501_245424_4818e0b7_multi_repaired.md` |
| Judge bias report | `results/real_run_20260627/judge_bias_20260627_142501_245424_4818e0b7_multi_repaired.md` |
| Full analysis report | `results/real_run_20260627/ANALYSIS_REPORT.md` |

## Supporting Signals

### Stats

- Rows analysed: 45 | Models: claude, deepseek, openai | Cases per model: 15, 15, 15
- CIs this wide at n=15 are the point: rank order is suggestive, not established. Report it honestly rather than implying precision the sample size does not support.
- | Comparison | Mean diff | Cohen's d | p (raw) | p (Holm) | Significant @0.05 |
- | Cohen's kappa | 0.614 (substantial) |
- _Method: percentile bootstrap, two-sided paired permutation test with add-one smoothing, Holm-Bonferroni multiple-comparison correction, Cohen's kappa for categorical agreement. Standard library only; reproducible via the fixed seed above._

### Causal

- Chi-square 0.000, MC p=1.000 -> balanced, comparison not confounded by allocation
- | Comparison | Blocked effect (a-b) | 95% CI | Var. reduction from blocking | McNemar discordant (a>b / b>a) | McNemar p |
- Blocking on case (the paired design) is what makes a small benchmark usable: it strips out case-difficulty variance so the model effect is read from within-case differences. McNemar tests the binary success outcome correctly via discordant pairs.
- No paraphrase-robustness results supplied. Run `cases_paraphrase_robustness.jsonl` and pass `--robustness-results` + `--robustness-cases` to estimate the rewording effect.
- _Methods: SRM Monte-Carlo multinomial guard; case-blocked paired effect with cluster bootstrap; McNemar exact binomial on discordant pairs; CUPED with leave-one-out difficulty covariate; paired perturbation contrast. Standard library only; reproducible via the fixed seed._

### Power

- Cases in this run: 15 | Models: claude, deepseek, openai | alpha=0.05, power=0.8
- | Comparison | Observed mean diff | SD of paired diff | MDE (80% power) | Detectable now? |
- If the observed difference is below the MDE, the design literally cannot call it significant. At this N you can only detect very large gaps — which is exactly why every comparison came back non-significant. That is a statement about sample size, not models.
- Reading: detecting a ~0.10 (trajectory) or ~10pp (success) gap needs on the order of 100-200 cases, not 15. Detecting 5pp needs many hundreds. This sets the case budget.
- Practical split: pick N from section 2 (power for the comparison you care about), then add K=5-8 only at temperature>0 to measure reliability and average out per-call noise.

### Judge Compare

- Items compared: 135
- Pearson(rule trajectory, judge total): 0.880
- Items compared: 45
- Cohen's kappa: 0.880 (almost perfect)

### Judge Bias

- Self-judge rows: 45

## Limitations And Required Next Runs

- Current tools are local mocks; this is appropriate for deterministic behavior evaluation but not yet a substitute for browser, OS, or production API environment tests.
- This scorecard should not be treated as a full framework-level release result until the missing P0 suites above are run.
- Current ranking should be framed with the statistical and power reports; small-N directional ordering is not the same as a significant model-quality claim.
- Self-family judge rows are reported for bias diagnostics and should not be the sole evidence for a model's official score.
- The next frontier-style additions are larger realistic environments, OS/computer-use tasks, and real API/browser harnesses.

