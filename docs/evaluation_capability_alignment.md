# Evaluation Capability Alignment

This document audits the framework against common industry patterns in LLM and Agent evaluation. It is intentionally written as a project capability map.

## Overall Judgment

The project is strongest as a trace-first, behavior-focused Agent evaluation framework. Its strongest coverage is:

1. Agent behavior benchmark design.
2. Tool-use reliability and autonomy-boundary evaluation.
3. Trace-based failure diagnosis.
4. LLM-as-Judge governance and judge-bias control.
5. Statistical reliability and experimental rigor.
6. Model-card style scorecards and release gates.

The project is intentionally weaker on distributed production platforms, full OS/browser environments, broad domain safety, multimodal evaluation, and post-training algorithm research.

## Capability Clusters

| Capability cluster | Why it matters | Current project coverage |
|---|---|---|
| Agent evaluation data and scenarios | Agent systems need planning, tool use, multi-turn, instruction following, and boundary cases | Strong; planning is a standalone suite |
| Evaluation framework / benchmark design | Model-quality claims need repeatable suites, scoring rules, and reporting protocols | Strong |
| Trace-based failure diagnosis | Final-answer grading misses wrong tools, bad parameters, false completion, and unsafe side effects | Strong |
| Tool-use / Agent task execution | Tool-call accuracy, reasoning-chain stability, and multi-step recovery are core Agent behaviors | Strong |
| LLM-as-Judge / multi-judge bias control | Semantic scoring is useful only when judge reliability and bias are measured | Strong; includes a fixed judge calibration gold set |
| Statistical and experimental rigor | Small benchmark means and one-off runs are easy to overinterpret | Strong |
| Productized reporting and iteration loop | Evaluation should produce actionable model, data, and product evidence | Medium-High |
| Real sandbox / execution-based eval | Agent eval should increasingly verify state changes, not only text claims | Medium-High for coding and local browser; OS still mock |
| CI/CD and production platform | Repeatable evaluation requires automation and regression checks | Medium; production orchestration remains shallow |
| Public benchmark literacy | SWE-bench, TAU-bench, WebArena, OSWorld, GAIA, and related benchmarks shape the evaluation landscape | Medium-High |
| Training/data strategy linkage | Failures become data recipes, regression cases, rubric checks, and rerun plans | Medium-High |
| Safety taxonomy breadth | Autonomy, permission, prompt injection, and side effects are covered; broader cyber/domain risks are not | Medium |
| Multimodal/domain-specific eval | Useful but outside the current project scope | Low by design |
| Algorithm/post-training research | Related but not the project focus | Low-Medium |

## Coverage Against Evaluation Responsibilities

| Responsibility | Current artifact | Coverage |
|---|---|---:|
| Build high-quality Agent eval datasets | `cases_all40.jsonl`, `cases_autonomy_*`, `cases_permission_boundary.jsonl` | High |
| Cover planning, tool use, multi-turn, instruction following | `cases_agent_planning.jsonl`, tool-use, autonomy, multi-turn, dynamic-user suites | High |
| Analyze model shortcomings and failure modes | failure taxonomy, trace logs, analysis reports | High |
| Build scalable/verifiable task construction | `benchmark_manifest.json`, `eval_runner.py`, `run_full_eval.py` | Medium-High |
| Evaluate Agent trace and distinguish planning/context/tool/reasoning failures | Trace logging plus scoring/failure types | High |
| Build LLM-as-Judge / execution-based / trace-based eval | `llm_judge.py`, final-state scoring, trace scorer | High |
| Control judge bias and multi-judge disagreement | OpenAI primary, Claude/DeepSeek cross judges, kappa/bias reports | High |
| Scientific experiment design and statistical rigor | `stats.py`, `causal_eval.py`, `power_analysis.py`, `reliability.py` | High |
| Productized model-card reporting | `scorecard.py`, generated scorecards | High |
| Eval-to-data strategy loop | `badcase_data_recipes.jsonl`, `cases_badcase_regression.jsonl`, `docs/badcase_to_data_loop_zh.md` | Medium-High |
| Search / Deep Research eval | `cases_search_research.jsonl` covers query formulation, freshness, citation support, uncertainty, and search-result injection | Medium-High |
| Safety eval beyond autonomy | Permission/side-effect/prompt-injection cases exist | Medium |
| Real browser/OS/coding execution environments | Mock stateful suites plus `coding_sandbox.py` and Playwright-compatible `browser_sandbox.py` exist | Medium |
| Platform engineering, CI/CD, distributed operation | Scripts and tests exist | Medium-Low |
| Public benchmark / open-source alignment | Industry analysis and public-benchmark-aligned suites exist | Medium |

## Main Gaps

1. Expanded suites need more full real-model runs and review coverage.
2. Browser/coding/OS environments are local or partial, not full OSWorld/Terminal-Bench/WebArena-scale.
3. Safety coverage is strongest on autonomy and side effects, weaker on cyber, persuasion, compliance, and domain-specific medical/finance policy.
4. Human review is currently lightweight and not a full multi-annotator adjudication workflow.
5. The project is reproducible and report-driven, but not yet a public leaderboard or production benchmark service.

## Recommended Emphasis

The framework should present its core depth in this order:

1. Benchmark and rubric design.
2. Trace-level Agent behavior diagnosis.
3. Badcase-to-data iteration.
4. LLM-as-Judge governance.
5. Statistical reliability and pass^k.
6. Scorecard and release gate.

Engineering modules such as stateful tools, browser verification, coding sandbox, and CI should remain visible as execution coverage, but they should not replace the main evaluation-methodology narrative.
