# Benchmark Release Candidate: No-Human-Review Track

Run date: 2026-06-28

This document is the benchmark release-candidate report for the real 108-row smoke run. Human review is intentionally skipped for this stage. The release decision therefore uses:

- rule-based trajectory scoring
- OpenAI as formal primary LLM judge
- Claude and DeepSeek as cross judges
- judge-vs-rule comparison
- judge-family bias audit
- statistical analysis
- release gate
- coding/browser execution verifiers

This is a **release candidate package**, not an approved benchmark release, because the release gate returns FAIL.

## Release Decision

| Signal | Result |
|---|---|
| Release package generated | yes |
| Real API model outputs | yes, 108 rows |
| P0 suite coverage | 4/4 |
| OpenAI primary judge | complete, 108/108 scored |
| Claude cross judge | complete after low-concurrency retry, 108/108 scored |
| DeepSeek cross judge | complete, 108/108 scored |
| Judge-family bias audit | complete |
| Human review | intentionally skipped |
| Release gate | **FAIL** |

Decision:

> Do not publish this as a passed benchmark release. Publish it as a real-run release candidate / evaluation evidence package, with explicit limitations.

## Why The Gate Failed

From `RELEASE_GATE_RELEASE_CANDIDATE_NO_HUMAN.md`:

| Gate item | Value |
|---|---:|
| Mean trajectory score | 2.19 / 3 |
| Required minimum | 2.40 / 3 |
| Blocking failures | 2 |
| Warning failures | 36 |
| Dry-run-like / zero-token rows | 6 |
| P0 suite coverage | 4 / 4 |

The benchmark package has good coverage but does not meet the quality bar. The gate is doing the right thing: it blocks overclaiming even though the execution pipeline succeeded.

## Rule Score Result

| Model | Rows | Mean trajectory score / 3 |
|---|---:|---:|
| claude | 36 | 1.89 |
| deepseek | 36 | 2.33 |
| openai | 36 | 2.33 |

Rule-score interpretation:

- OpenAI and DeepSeek tie in this smoke.
- Claude is lower.
- Tool-use reliability is stronger than planning and dynamic autonomy.

From `STATS_FULL_REAL_SMOKE.md`, Claude is significantly lower than OpenAI and DeepSeek under automatic trajectory scoring; OpenAI and DeepSeek are not significantly different.

## Primary Judge Result

OpenAI is used as the formal primary judge.

| Evaluated model | Rows | Mean OpenAI-judge total / 4 |
|---|---:|---:|
| claude | 36 | 2.94 |
| deepseek | 36 | 3.00 |
| openai | 36 | 3.72 |

Primary-judge interpretation:

- OpenAI judge prefers OpenAI outputs in this run.
- This should not be used alone as a final ranking because OpenAI is also one evaluated model.
- Cross-judge audit is required and was run.

## Cross-Judge Result

| Judge | Claude outputs | DeepSeek outputs | OpenAI outputs |
|---|---:|---:|---:|
| OpenAI primary | 2.94 | 3.00 | 3.72 |
| Claude cross | 2.94 | 3.42 | 3.89 |
| DeepSeek cross | 2.97 | 3.39 | 3.81 |

Cross-judge interpretation:

- All three judges rank OpenAI highest on semantic judge total in this run.
- Claude outputs are consistently lowest.
- DeepSeek is between Claude and OpenAI under judge scores, despite tying OpenAI on rule trajectory score.

## Judge Bias Audit

From `JUDGE_BIAS_FULL_REAL_SMOKE.md`:

| Family | Self mean | Cross-family mean | Delta |
|---|---:|---:|---:|
| claude | 2.94 | 2.96 | -0.01 |
| deepseek | 3.39 | 3.21 | +0.18 |
| openai | 3.72 | 3.85 | -0.12 |

Interpretation:

- No large directional self-judge inflation is observed in this run.
- There are still high-spread individual cases, so cross-judge disagreement should be inspected before using judge scores as final truth.
- The highest-spread cases are useful targets for future human review or gold calibration.

## Judge-vs-Rule Comparison

From `JUDGE_VS_RULE_OPENAI_PRIMARY_FULL_REAL_SMOKE.md`:

| Metric | Value |
|---|---:|
| Items compared | 108 |
| Rule trajectory mean | 2.185 / 3 |
| Judge result mean | 1.676 / 2 |
| Judge reasoning mean | 1.546 / 2 |
| Judge total mean | 3.222 / 4 |
| Pearson(rule trajectory, judge total) | 0.576 |

Interpretation:

- Rule score and judge score are positively correlated but not redundant.
- Large disagreements reveal where the rule scorer may be strict or where the judge may miss hard compliance constraints.
- This is exactly why the release package includes both rule and judge evidence.

## Main Failure Modes

Top failure types from the release-gate report:

| Failure type | Rows |
|---|---:|
| parameter_error | 22 |
| response_quality_gap | 9 |
| multi_turn_response_quality_gap | 5 |
| planning_order_or_decomposition_failure | 3 |
| planning_missing_required_signal | 3 |
| multi_turn_premature_tool_call | 3 |
| tool_selection_or_order_failure | 2 |
| multi_turn_false_completion_or_overclaim | 2 |
| multi_turn_action_timing_failure | 2 |
| api_error | 2 |

Main diagnosis:

1. Parameter precision is still the most common issue.
2. Planning remains the weakest P0 suite.
3. Dynamic and multi-turn autonomy expose failures that single-turn cases hide.
4. Some zero-token / empty-response artifacts need provider-level inspection.

## Execution Verifiers

Coding sandbox:

- 6 coding rows checked
- 6 passed
- 0 failed

Browser sandbox:

- Browser cases BW01 and BW03 checked across all three models
- 6 browser rows passed
- Current backend: static fallback
- Playwright available in current environment: false

## Release-Candidate Artifacts

| Artifact | Path |
|---|---|
| Combined results | `eval_results_FULL_REAL_SMOKE_COMBINED.csv` |
| Combined traces | `traces_FULL_REAL_SMOKE_COMBINED.jsonl` |
| OpenAI primary judge | `JUDGE_OPENAI_PRIMARY_FULL_REAL_SMOKE.csv` |
| Claude cross judge repaired | `JUDGE_CLAUDE_CROSS_REPAIRED_FULL_REAL_SMOKE.csv` |
| DeepSeek cross judge | `JUDGE_DEEPSEEK_CROSS_FULL_REAL_SMOKE.csv` |
| Multi-judge repaired | `JUDGE_MULTI_REPAIRED_FULL_REAL_SMOKE.csv` |
| Scorecard | `SCORECARD_RELEASE_CANDIDATE_NO_HUMAN.md` |
| Release gate | `RELEASE_GATE_RELEASE_CANDIDATE_NO_HUMAN.md` |
| Judge-vs-rule | `JUDGE_VS_RULE_OPENAI_PRIMARY_FULL_REAL_SMOKE.md` |
| Judge bias | `JUDGE_BIAS_FULL_REAL_SMOKE.md` |
| Statistics | `STATS_FULL_REAL_SMOKE.md` |
| Coding sandbox | `CODING_SANDBOX_REAL_SMOKE.md` |
| Browser sandbox | `BROWSER_SANDBOX_REAL_SMOKE.md` |

## What Can Be Claimed

Safe claim:

> The project has been run against real OpenAI, Claude, and DeepSeek APIs across the main Agent behavior evaluation suites. It produced traces, rule scores, primary/cross LLM judge scores, statistical analysis, scorecard, release gate, and execution-verifier evidence. The release gate correctly blocked formal release because quality thresholds were not met.

Do not claim:

- This is a passed benchmark release.
- This is a final model leaderboard.
- LLM judge has replaced human review permanently.
- Browser/OS evidence is production-grade.

## Next Release Actions

1. Fix planning failure modes and rerun the PL suite.
2. Inspect zero-token / empty-response rows.
3. Add Playwright runtime and rerun browser sandbox with real browser backend.
4. Use the highest judge-disagreement cases as a small gold review set.
5. Rerun release gate after score improvements and blocking failures are resolved.

