# Agent Tool-Use Reliability Eval

A reproducible evaluation project for LLM agent tool-calling reliability.

The project compares how models handle tool selection, parameter filling, multi-step state transfer, adversarial instructions, and error recovery. It uses structured cases, deterministic local mock tools, full execution traces, automatic trajectory scoring, and a human-review layer.

## Why This Project

Final answers alone hide important failures in agent workflows. A model may produce a plausible response while calling the wrong tool, inventing parameters, continuing after a tool error, or causing an unsafe side effect. This project treats the execution trace as first-class evidence and separates three layers:

- Result quality: whether the final user task was completed.
- Trajectory quality: whether the tool sequence, parameters, and stop conditions were reliable.
- Reasoning review: whether a human reviewer agrees with the behavior under ambiguous cases.

## What Is Included

- `cases_first15.jsonl`: first-pass benchmark with 15 cases.
- `cases_all40.jsonl`: expanded benchmark with 40 cases.
- `eval_runner.py`: evaluation runner with provider adapters, mock tools, trace logging, scoring, retries, and token-cost estimates.
- `analyze_results.py`: merges automatic results with human review and produces metrics.
- `test_eval_runner.py`: focused regression tests for case validation, scoring, dry-run behavior, and analysis.
- `results/README.md`: rules for generated result artifacts.

## Case Design

The 40 cases cover four categories:

| Category | Count | What it tests |
|---|---:|---|
| Normal | 10 | Basic tool selection and parameter extraction |
| Boundary | 12 | Missing context, ambiguous inputs, unavailable contacts, append vs overwrite |
| Adversarial | 12 | Prompt injection, refusing unsafe/no-tool requests, arithmetic/tool choice traps |
| Long chain | 6 | Multi-step plans, intermediate state transfer, error handling, stop conditions |

All tools are local mocks. The project does not send real emails, edit real files outside the mock environment, or touch a real calendar.

## Quick Start

The core scripts use only the Python standard library.

```bash
python3 eval_runner.py --validate --cases cases_all40.jsonl --limit 40
python3 eval_runner.py --dry-run --cases cases_all40.jsonl --models deepseek,qwen,claude --limit 40
python3 -m unittest test_eval_runner.py -v
```

Dry-run validates the engineering path only. It should never be used as model-performance evidence.

## Real Model Runs

Real runs require API keys in environment variables:

```bash
export DEEPSEEK_API_KEY="..."
export DASHSCOPE_API_KEY="..."
export ANTHROPIC_API_KEY="..."
```

Optional model overrides:

```bash
export DEEPSEEK_MODEL="deepseek-chat"
export QWEN_MODEL="qwen3.5-plus"
export ANTHROPIC_MODEL="claude-sonnet-4-6"
```

Start with a smoke test:

```bash
python3 eval_runner.py --case-ids N01,B03,A03 --models deepseek,qwen,claude --budget-cny 30
```

Then run the first formal batch:

```bash
python3 eval_runner.py --cases cases_first15.jsonl --models deepseek,qwen,claude --limit 15 --budget-cny 250
```

## Output Files

Each run writes unique, timestamped artifacts under `results/`:

- `eval_results_*.csv`: automatic trajectory-scoring output.
- `traces_*.jsonl`: raw model/tool trace.
- `human_review_*.csv`: human-review worksheet.
- `summary_*.md`: automatic run summary.
- `merged_results_*.csv`: merged automatic and human scores.
- `analysis_*.md`: analysis draft.

## Analysis Workflow

After filling the human-review CSV:

```bash
python3 analyze_results.py \
  --results results/eval_results_<run_id>.csv \
  --review results/human_review_<run_id>.csv
```

The analyzer refuses dry-run inputs to reduce the chance of accidentally treating simulated outputs as real evidence.

## Current Status

- 40 structured cases are complete and locally valid.
- The runner supports deterministic dry-run plus real provider calls.
- Regression tests cover validation, scoring edge cases, long-chain behavior, and review merging.
- Formal model-performance numbers should be added only after real API runs and human review.

## Portfolio Notes

This is a personal evaluation-engineering project. AI coding tools helped with implementation speed, but the benchmark framing, risk taxonomy, case design, scoring strategy, and review workflow are the parts I use to demonstrate evaluation thinking in interviews.
