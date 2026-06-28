# Real Model Benchmark Evidence - 2026-06-28

This directory contains the curated GitHub-facing evidence from the real API smoke benchmark. It intentionally keeps only report-level artifacts and two compact CSVs; raw traces remain local under `results/` to keep the portfolio readable.

## What Was Run

| Item | Value |
|---|---:|
| Evaluated models | OpenAI, Claude, DeepSeek |
| Real model rows | 108 |
| P0 suite coverage | 4/4 |
| Primary judge | OpenAI |
| Cross judges | Claude, DeepSeek |
| Human review | skipped for this no-human-review release-candidate track |
| Final calibrated mean trajectory score | 2.51 / 3 |
| Dry-run/API evidence rows after targeted rerun | 0 |
| Remaining blocking failures | 2 |
| Release gate | FAIL |

The run completed end to end. The release gate remains FAIL because it found two real high-risk Agent behavior failures, not because the pipeline failed.

## Recommended Reading Order

1. `benchmark_release_candidate.md` - executive release-candidate summary.
2. `release_gate_calibrated_rerun_repaired.md` - final gate after scorer calibration and Claude evidence rerun.
3. `blocking_and_evidence_rerun_analysis.md` - why the gate still fails and how zero-token/API rows were repaired.
4. `blocking_case_passk_analysis_zh.md` - pass^k reliability analysis for the two DeepSeek blocking cases.
5. `scorer_calibration_delta.md` - rule scorer calibration and before/after impact.
6. `stats_full_real_smoke.md` - statistical analysis for model comparisons.
7. `judge_bias_full_real_smoke.md` - judge-family bias audit.

## Minimal Reproducibility Artifacts

| Artifact | Purpose |
|---|---|
| `eval_results_calibrated_rerun_repaired.csv` | Final 108-row calibrated result after targeted evidence repair. |
| `eval_results_blocking_passk_combined.csv` | 16-row pass^k trial result for the two blocking cases. |

## How To Interpret The Result

This is not a "passed benchmark release". It is stronger as portfolio evidence because it shows the full evaluation loop:

- real model execution;
- trace-based rule scoring;
- LLM-as-Judge with primary/cross judges;
- judge-bias audit;
- scorer calibration;
- evidence-gap rerun;
- release gate;
- pass^k reliability analysis;
- concrete failure-mode diagnosis.

The honest conclusion is:

> The framework is real-run capable and can produce actionable model-quality evidence. The current run should be published as a release candidate, not as a passed leaderboard, because two DeepSeek Agent behavior failures remain blocking.
