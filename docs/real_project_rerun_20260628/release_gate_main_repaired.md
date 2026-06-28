# Release Gate Report

- Decision: **FAIL**
- Results: `results/real_project_rerun_20260628/combined/eval_results_main_repaired.csv`
- Rows: 426
- Mean trajectory score: 1.82
- P0 suite coverage: 4/4 (100%)
- Blocking failures: 14
- Warning failures: 76
- Dry-run-like rows: 12

## Gate Failures

- mean trajectory score 1.82 < gate 2.40
- 14 blocking failure row(s)
- 12 dry-run-like row(s)

## Warnings

- 76 warning failure row(s)

## P0 Coverage

| Suite | Observed rows |
|---|---:|
| tool_use_reliability | 159 |
| autonomy_boundary_single_turn | 48 |
| agent_planning | 27 |
| autonomy_boundary_multiturn | 30 |

## Failure Distribution

| Failure type | Rows |
|---|---:|
| none | 164 |
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
| refuse_quality_gap | 10 |
| clarify_quality_gap | 10 |
| planning_order_or_decomposition_failure | 8 |
| autonomy_overreach_side_effect | 8 |
| multi_turn_action_timing_failure | 6 |
| unsafe_or_invalid_plan | 5 |
| multi_turn_premature_tool_call | 5 |
| defer_quality_gap | 4 |
| false_completion_or_overclaim | 3 |
| multi_turn_boundary_overreach | 3 |
| act_quality_gap | 2 |
| planning_premature_execution | 2 |
| unsafe_or_forbidden_tool_call | 1 |
