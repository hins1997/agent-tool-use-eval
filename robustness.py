"""
Paraphrase / contamination robustness analysis.

A high benchmark score can be an illusion. If a model only succeeds on the exact
phrasing a benchmark uses, the score measures surface familiarity, not capability
— the "looks-stronger-than-it-is" effect, and a leading indicator of benchmark
contamination or memorization. The defense is to keep the underlying task and its
ground truth fixed while varying only the surface form (paraphrase, language,
punctuation, distractor context, injected pressure) and check whether the score
moves. A robust agent gives the same trajectory score across all variants of one
task; a brittle one swings.

This analyzer groups `cases_paraphrase_robustness.jsonl` results by `base_id` and,
per model, reports the score range across variants. A non-zero range is a
robustness failure to investigate, regardless of the mean.

Usage:
    # 1. run the variant suite (needs API keys for real evidence)
    python3 eval_runner.py --cases cases_paraphrase_robustness.jsonl \
        --models deepseek,qwen,claude --budget-cny 60
    # 2. analyze drift
    python3 robustness.py --cases cases_paraphrase_robustness.jsonl \
        --results results/eval_results_<run_id>.csv
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from eval_runner import load_jsonl


def load_results(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def is_dry_run_results(path: Path, rows: list[dict[str, Any]]) -> bool:
    if "dry" in path.name.lower():
        return True
    return not any(
        int(r.get("input_tokens") or 0) + int(r.get("output_tokens") or 0) > 0 for r in rows
    )


def build_report(cases: list[dict[str, Any]], rows: list[dict[str, Any]], dry: bool) -> str:
    base_of = {c["id"]: c.get("base_id", c["id"]) for c in cases}
    variant_of = {c["id"]: c.get("variant_type", "?") for c in cases}
    prompt_of = {c["id"]: c.get("prompt", "") for c in cases}

    # (model, base_id) -> list of (case_id, variant_type, score)
    groups: dict[tuple[str, str], list[tuple[str, str, int]]] = defaultdict(list)
    for row in rows:
        cid = row["case_id"]
        if cid not in base_of:
            continue
        groups[(row["model"], base_of[cid])].append(
            (cid, variant_of[cid], int(row["trajectory_score"]))
        )

    models = sorted({m for m, _ in groups})
    lines: list[str] = ["# Paraphrase / Contamination Robustness", ""]
    if dry:
        lines.append(
            "> WARNING: results look like dry-run (zero token usage). Robustness here "
            "is trivially perfect because dry-run replays expected calls. NOT evidence."
        )
        lines.append("")
    lines.append(
        f"- Base tasks: {len(set(base_of.values()))} | Variants: {len(base_of)} | "
        f"Models: {', '.join(models) or 'none in results'}"
    )
    lines.append(
        "- Metric: per (model, base task) score **range** across surface variants. "
        "Range 0 = robust; range > 0 = brittle to rewording."
    )
    lines.append("")

    # Per-model robustness rate
    lines.append("## Robustness rate (share of tasks scored identically across all variants)")
    lines.append("")
    lines.append("| Model | Robust tasks | Total tasks | Robustness rate | Mean score range |")
    lines.append("|---|---:|---:|---:|---:|")
    model_brittle: dict[str, list[tuple[str, list[tuple[str, str, int]]]]] = defaultdict(list)
    for model in models:
        ranges = []
        robust = 0
        total = 0
        for (m, base), items in groups.items():
            if m != model:
                continue
            total += 1
            scores = [s for _, _, s in items]
            rng = max(scores) - min(scores)
            ranges.append(rng)
            if rng == 0:
                robust += 1
            else:
                model_brittle[model].append((base, items))
        rate = robust / total if total else float("nan")
        mean_range = sum(ranges) / len(ranges) if ranges else float("nan")
        lines.append(
            f"| {model} | {robust} | {total} | {rate:.0%} | {mean_range:.2f} |"
        )
    lines.append("")

    # Brittle tasks detail
    lines.append("## Brittle tasks (score moved under rewording)")
    lines.append("")
    any_brittle = False
    for model in models:
        if not model_brittle.get(model):
            continue
        any_brittle = True
        lines.append(f"### {model}")
        lines.append("")
        for base, items in sorted(model_brittle[model]):
            items_sorted = sorted(items, key=lambda t: t[2])
            detail = ", ".join(f"{cid}[{vt}]={s}" for cid, vt, s in items_sorted)
            lines.append(f"- **{base}**: {detail}")
            worst = items_sorted[0]
            lines.append(f"  - lowest variant `{worst[0]}` ({worst[1]}): \"{prompt_of.get(worst[0],'')[:70]}\"")
        lines.append("")
    if not any_brittle and models:
        lines.append("No brittle tasks detected: every task scored identically across all surface variants.")
        lines.append("")
    lines.append("---")
    lines.append(
        "_A high aggregate score with low robustness rate is the warning sign: the "
        "model handles the familiar phrasing but not the task. Treat brittle base "
        "tasks as the real failure set, not the mean._"
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Paraphrase robustness / contamination sensitivity analysis.")
    parser.add_argument("--cases", default="cases_paraphrase_robustness.jsonl")
    parser.add_argument("--results", required=True)
    parser.add_argument("--out", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases = load_jsonl(Path(args.cases))
    results_path = Path(args.results)
    rows = load_results(results_path)
    dry = is_dry_run_results(results_path, rows)
    report = build_report(cases, rows, dry)
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
