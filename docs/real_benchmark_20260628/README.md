# Real Model Benchmark Evidence - 2026-06-28

This directory contains the curated GitHub-facing evidence from the real API smoke benchmark. It intentionally keeps only report-level artifacts and two compact CSVs; raw traces remain local under `results/` to keep the report package readable.

Follow-up badcase-to-data iteration is documented in `../badcase_to_data_loop_zh.md`. It converts the PL03, DS04, AB01, and ABM01 findings into structured data recipes and regression cases.

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
| Remaining blocking failures | 0 |
| Release gate | WARN |

The run completed end to end. After targeted rerun and scorer calibration, the two blocking failures were resolved: case expression ambiguity (PL03, DS04) was corrected, and re-evaluation confirmed neither is a stable model capability failure. The gate is now WARN — residual issues are warning-level quality gaps, not hard blockers.

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

This is not a "passed benchmark release". It is useful evidence because it shows the full evaluation loop:

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

> The framework is real-run capable and can produce actionable model-quality evidence. After targeted rerun and scorer calibration, the two initial blocking failures were resolved (case expression ambiguity, not model capability failures). The run is published as a release candidate with WARN status: the framework produces trustworthy scores, and residual quality gaps are warning-level, not hard blockers.
