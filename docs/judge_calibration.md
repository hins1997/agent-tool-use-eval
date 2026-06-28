# Judge Calibration Gold Set

`judge_calibration_gold.csv` is a small fixed gold set for checking whether an LLM-as-Judge is usable before its scores are treated as formal evidence.

## Purpose

The judge is an evaluation instrument, not ground truth. This file gives the primary judge and cross judges a stable calibration slice across:

- normal tool use
- missing dependencies
- false completion and fabricated evidence
- standalone planning
- autonomy boundary decisions
- stateful final-state checks
- browser prompt-injection resistance

## Current Policy

1. OpenAI is the formal primary judge.
2. Claude and DeepSeek are cross judges.
3. The rule score must not be shown to the judge.
4. Judge output must be structured JSON.
5. Human/gold agreement should be reported before using judge scores for model ranking.
6. Self-family judging is diagnostic only; it must not be the sole evidence for a model's score.

## Suggested Gate

For portfolio use, report the judge/gold agreement. For release-gate use, require:

- Cohen's kappa >= 0.60 against the gold set.
- No systematic inflation on self-family rows.
- Manual inspection of all judge/gold disagreements where the gold score is 0.

## How To Use

The project supports judge-vs-human agreement through `llm_judge.py agreement` and fixed gold calibration through `llm_judge.py calibrate`.

```bash
python3 llm_judge.py calibrate \
  --gold judge_calibration_gold.csv \
  --judge-csv results/judge_calibration_<judge>.csv \
  --out results/judge_calibration_<judge>.md
```

The judge CSV must contain:

- `gold_id` or `case_id`
- `judge_result_score_0_2`
- `judge_reasoning_score_0_2`
- optional `judge_rationale`, `judge_alias`, and `judge_family`

The report includes result-score kappa, reasoning-score kappa, exact result+reasoning agreement, severe misses, family-level error breakdown, and a disagreement table.
