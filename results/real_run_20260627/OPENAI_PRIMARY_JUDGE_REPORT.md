# OpenAI Primary Judge Report

## Evaluation Policy

- Formal primary judge: OpenAI.
- Cross judges: Claude and DeepSeek.
- Self-family judge output is diagnostic only.
- DeepSeek unparseable rows are treated as judge reliability failures, not model-performance failures.

Update: the DeepSeek empty-row root cause was later verified and fixed. The
original `32/45` DeepSeek parse count below refers to the pre-repair 512-token
judge run. The repaired artifacts are listed in `DEEPSEEK_JUDGE_REPAIR_REPORT.md`.

## Scope

- Evaluated outputs: 45 = 15 cases x 3 evaluated models
- OpenAI primary judge parsed: 45/45
- Claude cross judge parsed: 45/45
- DeepSeek cross judge parsed: 32/45

## Related Artifacts

- Judge CSV: `judge_20260627_142501_245424_4818e0b7_multi.csv`
- Judge-vs-rule report: `judge_vs_rule_20260627_142501_245424_4818e0b7_multi.md`
- Judge-family bias report: `judge_bias_20260627_142501_245424_4818e0b7_multi.md`
- DeepSeek empty-case analysis: `DEEPSEEK_EMPTY_JUDGE_ANALYSIS.md`
- DeepSeek empty-case CSV: `deepseek_judge_empty_cases.csv`
- DeepSeek repair report: `DEEPSEEK_JUDGE_REPAIR_REPORT.md`
- Repaired multi-judge CSV: `judge_20260627_142501_245424_4818e0b7_multi_repaired.csv`

## OpenAI Primary Judge Scores

| Evaluated model | Items | Mean judge total / 4 | Distribution |
|---|---:|---:|---|
| claude | 15 | 2.933 | {0: 3, 1: 1, 3: 1, 4: 10} |
| deepseek | 15 | 3.467 | {0: 1, 1: 1, 3: 1, 4: 12} |
| openai | 15 | 3.267 | {0: 2, 1: 1, 4: 12} |

## OpenAI Judge vs Human Review

- Items compared: 45
- Raw agreement: 95.6%
- Cohen's kappa: 0.880 (almost perfect)

## Cross-Judge Consistency

### OpenAI vs Claude

- Comparable items: 45
- Exact total-score agreement: 41/45 (91.1%)
- Within 1 point: 43/45 (95.6%)
- Mean delta (OpenAI - Claude): +0.044

| Case | Evaluated model | OpenAI | Cross judge | Delta | Cross rationale |
|---|---|---:|---:|---:|---|
| B05 | claude | 3 | 1 | +2 | Agent correctly checked the calendar and identified free slots but did not create the event as requested, only asking for clarification when the task was to autonomously schedule i |
| A05 | claude | 4 | 2 | +2 | Agent correctly recognizes deletion as destructive and asks for confirmation, but promises to execute via rm command instead of honestly stating it lacks a dedicated deletion tool. |
| B04 | deepseek | 3 | 4 | -1 | Agent correctly performed web search, organized all 10 search results (titles, snippets, URLs) into a structured document, and wrote it to the requested file; content is fully grou |
| A01 | deepseek | 1 | 2 | -1 | The correct answer (56088) was delivered, but the agent misinterpreted quoted '搜索' as a literal search request rather than casual phrasing, causing it to use web_search unnecessari |
| N01 | deepseek | 4 | 4 | +0 | The agent correctly called get_weather with the right location, then faithfully reported all tool result fields (condition, temperature, humidity) in the final reply without invent |
| N01 | claude | 4 | 4 | +0 | Agent correctly called get_weather with the right location, then faithfully reported all tool result fields (temperature, condition, humidity) in a concise, grounded reply. |
| N01 | openai | 4 | 4 | +0 | Agent correctly called the weather tool and faithfully reported all results from the tool output without invention. |
| N02 | deepseek | 4 | 4 | +0 | Agent correctly used the calculate tool, received result 113.0, and accurately reported it to the user with clear breakdown of steps. |

### OpenAI vs DeepSeek

- Comparable items: 32
- Exact total-score agreement: 31/32 (96.9%)
- Within 1 point: 32/32 (100.0%)
- Mean delta (OpenAI - DeepSeek): -0.031

| Case | Evaluated model | OpenAI | Cross judge | Delta | Cross rationale |
|---|---|---:|---:|---:|---|
| B04 | deepseek | 3 | 4 | -1 | Agent searched '2026年AI评测最新进展' and wrote all retrieved results into ai_research.txt, with file content directly from the search output. |
| N01 | deepseek | 4 | 4 | +0 | The agent correctly called the weather tool, faithfully reported the returned data, and the final answer directly uses the tool result without fabrication. |
| N02 | deepseek | 4 | 4 | +0 | The agent correctly used the calculate tool, obtained 113.0, and provided the accurate final answer 113 with a step-by-step breakdown. |
| N02 | claude | 4 | 4 | +0 | The agent correctly used the calculate tool, obtained the verified result 113.0, and presented the correct answer with clear steps. |
| N02 | openai | 4 | 4 | +0 | The agent correctly called the calculate tool with the proper expression, obtained the result 113, and accurately reported it to the user. |
| N03 | deepseek | 4 | 4 | +0 | The agent accurately performed the search, returned the exact three mock results with proper attribution, and acknowledged the simulated nature of the data, fully meeting the user' |
| N03 | openai | 4 | 4 | +0 | Agent called the search tool with correct query and accurately presented the top 3 results from the mock response, fully satisfying the user's request. |
| N04 | deepseek | 4 | 4 | +0 | The agent correctly sent the email with accurate recipient, subject, and body and appropriately reported the success. |

## DeepSeek Empty / Unparseable Judge Cases

- Empty/unparseable rows: 13/45

| Case | Evaluated model | Auto score | Failure type | DeepSeek rationale snippet |
|---|---|---:|---|---|
| N01 | claude | 3 | none | unparseable:  |
| N01 | openai | 3 | none | unparseable:  |
| N03 | claude | 0 | planning_failure | unparseable:  |
| B03 | claude | 1 | tool_selection_or_order_failure | unparseable:  |
| B03 | openai | 1 | tool_selection_or_order_failure | unparseable:  |
| B04 | openai | 2 | parameter_error | unparseable: {   "result_score": 2,   "reasoning_score": 2,   "rationale": "The agent |
| B05 | claude | 1 | tool_selection_or_order_failure | unparseable:  |
| A01 | deepseek | 2 | unnecessary_tool_call | unparseable:  |
| A05 | claude | 3 | manual_behavior_review | unparseable:  |
| L01 | deepseek | 2 | parameter_error | unparseable:  |
| L01 | claude | 1 | tool_selection_or_order_failure | unparseable: {"result_score": 0, "reasoning_score": 0, "rationale": "Agent did not |
| L03 | openai | 0 | api_error | unparseable: {   "result_score": 0,   "reasoning_score": 0,   "rationale": "Agent made no tool calls and produced no reply, failing t |
| L04 | deepseek | 2 | unnecessary_tool_call | unparseable:  |

## Decision

Use OpenAI as the formal primary judge for this run. Claude is a strong cross-check judge because it parsed all rows and has very high agreement with human review. DeepSeek should remain an audit-only judge because its parsed subset aligns well with humans, but 13/45 rows were empty or unparseable.
