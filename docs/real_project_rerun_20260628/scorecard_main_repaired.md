# Agent Eval Scorecard

- Framework: Agent Behavior Eval Framework
- Manifest version: 0.3.0
- Positioning: Trace-first agent behavior evaluation for tool-use reliability and autonomy boundary control.

## Executive Decision

- Best primary-judge model in this run: openai (2.33 / 4 mean OpenAI-judge total).
- Ranking strength: at least one pairwise comparison is statistically significant at alpha=0.05.
- Coverage warning: no missing P0 suites detected for this result file.

## Suite Coverage

| Suite | Case file | Module | Manifest cases | Priority | Observed rows |
|---|---|---|---:|---|---:|
| tool_use_reliability | cases_all40.jsonl | tool_use | 44 | P0 | 159 |
| autonomy_boundary_single_turn | cases_autonomy_boundary.jsonl | autonomy_boundary | 16 | P0 | 48 |
| agent_planning | cases_agent_planning.jsonl | agent_planning | 8 | P0 | 27 |
| search_deep_research | cases_search_research.jsonl | tool_use | 6 | P1 | 18 |
| autonomy_boundary_multiturn | cases_autonomy_multiturn.jsonl | autonomy_boundary | 9 | P0 | 30 |
| permission_boundary | cases_permission_boundary.jsonl | autonomy_boundary | 12 | P1 | 48 |
| stateful_tool_sandbox | cases_stateful_tools.jsonl | tool_use | 6 | P1 | 18 |
| dynamic_user_simulation | cases_dynamic_autonomy.jsonl | autonomy_boundary | 4 | P1 | 27 |
| agentic_coding | cases_agentic_coding.jsonl | tool_use | 4 | P2 | 24 |
| browser_web | cases_browser_web.jsonl | tool_use | 4 | P2 | 24 |
| benchmark_aligned_agent_tasks | cases_benchmark_aligned.jsonl | mixed | 20 | P1 | n/a |
| badcase_to_data_regression | cases_badcase_regression.jsonl | mixed | 4 | P1 | n/a |
| tool_use_multiturn | cases_multiturn.jsonl | tool_use | n/a | P1 | 15 |
| paraphrase_robustness | cases_paraphrase_robustness.jsonl | robustness | n/a | P1 | 0 |

## Rule Score By Model

| Model | Rows | Mean total score | Mean trajectory score |
|---|---:|---:|---:|
| claude | 142 | n/a | 1.56 |
| deepseek | 142 | n/a | 1.83 |
| openai | 142 | n/a | 2.08 |

## Judge Score By Model

- Primary judge: openai
- Cross judges: claude, deepseek

| Judge | Evaluated model | Rows | Mean result | Mean reasoning | Self-judge rows |
|---|---|---:|---:|---:|---:|
| claude | claude | 8 | 1.00 | 1.17 | 8 |
| claude | deepseek | 12 | 1.00 | 1.00 | 0 |
| claude | openai | 6 | 1.20 | 1.20 | 0 |
| deepseek | claude | 8 | 1.00 | 1.12 | 0 |
| deepseek | deepseek | 12 | 1.08 | 1.08 | 12 |
| deepseek | openai | 6 | 1.33 | 1.33 | 0 |
| openai | claude | 8 | 0.88 | 0.88 | 0 |
| openai | deepseek | 12 | 1.00 | 1.00 | 0 |
| openai | openai | 6 | 1.17 | 1.17 | 6 |

Primary-judge totals:

| Evaluated model | Rows | Mean primary-judge total / 4 |
|---|---:|---:|
| claude | 8 | 1.75 |
| deepseek | 12 | 2.00 |
| openai | 6 | 2.33 |

## Top Failure Types

| Failure type | Count |
|---|---:|
| api_error | 50 |
| parameter_error | 39 |
| unnecessary_tool_call | 20 |
| response_quality_gap | 18 |
| multi_turn_response_quality_gap | 13 |
| autonomy_overreach_unnecessary_tool | 12 |
| planning_failure | 11 |
| tool_selection_or_order_failure | 11 |
| planning_missing_required_signal | 11 |
| manual_behavior_review | 10 |

## Evidence Index

| Artifact | Path |
|---|---|
| Results CSV | `results/real_project_rerun_20260628/combined/eval_results_main_repaired.csv` |
| Judge CSV | `results/real_project_rerun_20260628/combined/judge_focus_multi.csv` |
| Statistics report | `results/real_project_rerun_20260628/combined/stats_main_repaired.md` |
| Judge-vs-rule report | `results/real_project_rerun_20260628/combined/judge_vs_rule_focus.md` |
| Judge bias report | `results/real_project_rerun_20260628/combined/judge_bias_focus.md` |

## Supporting Signals

### Stats

- Rows analysed: 426 | Models: claude, deepseek, openai | Cases per model: 142, 142, 142
- CIs this wide at n≈142 per model are the point: rank order is suggestive, not established. Report it honestly rather than implying precision the sample size does not support.
- | Comparison | Mean diff | Cohen's d | p (raw) | p (Holm) | Significant @0.05 |
- No human-review / judge CSV supplied. Agreement quantifies how far the automatic trajectory label can be trusted as a stand-in for human judgement; fill a `human_review_*.csv` (or run `llm_judge.py`) and pass it with `--review` to populate raw agreement and Cohen's kappa here.
- _Method: percentile bootstrap, two-sided paired permutation test with add-one smoothing, Holm-Bonferroni multiple-comparison correction, Cohen's kappa for categorical agreement. Standard library only; reproducible via the fixed seed above._

### Judge Compare

- Items compared: 73
- Pearson(rule trajectory, judge total): 0.624

### Judge Bias

- Self-judge rows: 24

## Limitations And Required Next Runs

- Current tools are local mocks; this is appropriate for deterministic behavior evaluation but not yet a substitute for browser, OS, or production API environment tests.
- Current ranking should be framed with the statistical and power reports; small-N directional ordering is not the same as a significant model-quality claim.
- Self-family judge rows are reported for bias diagnostics and should not be the sole evidence for a model's official score.
- The next frontier-style additions are larger realistic environments, OS/computer-use tasks, and real API/browser harnesses.

