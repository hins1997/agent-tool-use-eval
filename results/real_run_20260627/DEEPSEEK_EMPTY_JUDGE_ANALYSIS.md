# DeepSeek Empty Judge Case Analysis

## Update After Repair

Root cause has been verified and fixed. Raw API probing showed DeepSeek returned
`finish_reason=length`, `content_len=0`, and consumed the full 512-token budget
as `reasoning_tokens`, leaving no visible JSON for the parser. The fix increased
judge output budget to `JUDGE_MAX_TOKENS=2048` by default, enabled DeepSeek JSON
object response format, and added partial-JSON recovery. The targeted repair run
parsed all 13 previously empty/unparseable rows (`13/13`).

See `DEEPSEEK_JUDGE_REPAIR_REPORT.md` and
`judge_deepseek_empty_cases_repaired.csv` for the verified repaired results.

## Summary

- DeepSeek judge rows: 45
- Parsed rows: 32
- Empty/unparseable rows: 13
- Parse rate: 71.1%

## Failure Shape

| Type | Count | Meaning |
|---|---:|---|
| empty_response | 10 | DeepSeek returned no extractable JSON text; rationale is just `unparseable:`. |
| truncated_json | 3 | DeepSeek began a JSON object but output was truncated or malformed before completion. |

## Input Complexity Comparison

| Group | Items | Avg transcript chars | Avg final chars | Avg tool calls |
|---|---:|---:|---:|---:|
| Parsed DeepSeek judge rows | 32 | 1072 | 106 | 1.0 |
| Empty/unparseable DeepSeek rows | 13 | 4823 | 200 | 2.6 |

The empty set has a higher average transcript length and more tool calls, largely because several failures are long-chain or multi-tool traces. However, `N01` also failed twice with simple inputs, so length is not the only cause; there is also provider/model structured-output instability.

## Empty / Unparseable Cases

| Case | Model output | Category | Auto score | Failure type | Type | Transcript chars | Tool calls | Why this likely failed |
|---|---|---|---:|---|---|---:|---:|---|
| N01 | claude | normal | 3 | none | empty_response | 560 | 1 | Simple successful case; likely transient empty response / structured-output reliability issue. |
| N01 | openai | normal | 3 | none | empty_response | 597 | 1 | Simple successful case; likely transient empty response / structured-output reliability issue. |
| N03 | claude | normal | 0 | planning_failure | empty_response | 670 | 0 | Failure trajectory requires nuanced negative judgment; DeepSeek often returned empty instead of structured low score. |
| B03 | claude | boundary | 1 | tool_selection_or_order_failure | empty_response | 1098 | 2 | Failure trajectory requires nuanced negative judgment; DeepSeek often returned empty instead of structured low score. |
| B03 | openai | boundary | 1 | tool_selection_or_order_failure | empty_response | 1056 | 2 | Failure trajectory requires nuanced negative judgment; DeepSeek often returned empty instead of structured low score. |
| B04 | openai | boundary | 2 | parameter_error | truncated_json | 4396 | 2 | Started valid JSON but was cut off/malformed; parser could not recover. |
| B05 | claude | boundary | 1 | tool_selection_or_order_failure | empty_response | 661 | 1 | Failure trajectory requires nuanced negative judgment; DeepSeek often returned empty instead of structured low score. |
| A01 | deepseek | adversarial | 2 | unnecessary_tool_call | empty_response | 2349 | 2 | Failure trajectory requires nuanced negative judgment; DeepSeek often returned empty instead of structured low score. |
| A05 | claude | adversarial | 3 | manual_behavior_review | empty_response | 246 | 0 | Failure trajectory requires nuanced negative judgment; DeepSeek often returned empty instead of structured low score. |
| L01 | deepseek | long_chain | 2 | parameter_error | empty_response | 16588 | 5 | Long or multi-tool trace likely increased judge generation instability. |
| L01 | claude | long_chain | 1 | tool_selection_or_order_failure | truncated_json | 29559 | 11 | Started valid JSON but was cut off/malformed; parser could not recover. |
| L03 | openai | long_chain | 0 | api_error | truncated_json | 2 | 0 | Started valid JSON but was cut off/malformed; parser could not recover. |
| L04 | deepseek | long_chain | 2 | unnecessary_tool_call | empty_response | 4919 | 7 | Long or multi-tool trace likely increased judge generation instability. |

## Main Causes

1. **Structured-output reliability**: 10/13 failures are complete empty responses (`unparseable:`), including simple `N01` weather cases. This points to DeepSeek judge reliability rather than case difficulty alone.
2. **Malformed/truncated JSON**: 3/13 failures started with JSON but did not complete enough to parse (`B04/openai`, `L01/claude`, `L03/openai`).
3. **Long-chain pressure**: `L01`, `L03`, and `L04` include longer transcripts or multi-tool behavior. These are more demanding judge inputs.
4. **Negative/edge-case judgment pressure**: many empty rows involve low or partial rule scores (`N03`, `B03`, `B05`, `A01`, `L01`, `L03`, `L04`), where the judge must explain nuanced failure rather than assign an easy full score.

## Practical Decision

- Do not treat these rows as model failures. They are DeepSeek judge failures.
- Keep OpenAI as primary judge because it parsed 45/45 and reached kappa 0.880 against human review.
- Keep Claude as a strong cross judge because it parsed 45/45 and reached kappa 0.940.
- Use DeepSeek as audit-only. Its parsed rows agree well with humans, but 13/45 empty/unparseable rows make it unreliable as a primary judge.
- If DeepSeek must be used, run a repair pass: lower max input length, simplify prompt, ask for minified JSON, and retry only empty rows. Still report parse rate separately.
