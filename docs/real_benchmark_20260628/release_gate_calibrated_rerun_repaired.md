# Release Gate Report

- Decision: **FAIL**
- Results: `results/real_p0_smoke_20260628/eval_results_FULL_REAL_SMOKE_CALIBRATED_RERUN_REPAIRED.csv`
- Rows: 108
- Mean trajectory score: 2.51
- P0 suite coverage: 4/4 (100%)
- Blocking failures: 2
- Warning failures: 22
- Dry-run-like rows: 0

## Gate Failures

- 2 blocking failure row(s)

## Warnings

- 22 warning failure row(s)

## P0 Coverage

| Suite | Observed rows |
|---|---:|
| tool_use_reliability | 33 |
| autonomy_boundary_single_turn | 9 |
| agent_planning | 9 |
| autonomy_boundary_multiturn | 9 |

## Failure Distribution

| Failure type | Rows |
|---|---:|
| none | 72 |
| parameter_error | 10 |
| response_quality_gap | 9 |
| multi_turn_premature_tool_call | 4 |
| tool_selection_or_order_failure | 2 |
| planning_quality_gap | 2 |
| multi_turn_response_quality_gap | 2 |
| planning_order_or_decomposition_failure | 1 |
| planning_premature_execution | 1 |
| planning_missing_required_signal | 1 |
| autonomy_overreach_unnecessary_tool | 1 |
| refuse_quality_gap | 1 |
| unnecessary_tool_call | 1 |
| false_completion_or_overclaim | 1 |
