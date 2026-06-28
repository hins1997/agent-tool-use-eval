#!/usr/bin/env python3
"""Compare two eval result CSVs and report run-to-run deltas."""

from __future__ import annotations

import argparse
import csv
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare baseline/current eval_results CSV files")
    parser.add_argument("--baseline", required=True, help="baseline eval_results CSV")
    parser.add_argument("--current", required=True, help="current eval_results CSV")
    parser.add_argument("--out", default="", help="optional markdown output path")
    parser.add_argument("--regression-threshold", type=float, default=-0.5)
    return parser.parse_args()


def read_csv(path: str) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def as_float(value: Any) -> float | None:
    try:
        text = str(value or "").strip()
        if not text or text.upper() in {"PENDING", "N/A", "NONE"}:
            return None
        return float(text)
    except ValueError:
        return None


def score(row: dict[str, str]) -> float | None:
    total = as_float(row.get("total_score"))
    if total is not None:
        return total
    return as_float(row.get("trajectory_score"))


def mean(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}"


def row_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (row.get("case_id", ""), row.get("model", ""), row.get("trial", "1") or "1")


def group_key(row: dict[str, str], field: str) -> str:
    if field == "module":
        return row.get("module") or "tool_use_reliability"
    return row.get(field, "") or "unknown"


def build_delta_report(
    baseline_rows: list[dict[str, str]],
    current_rows: list[dict[str, str]],
    baseline_path: str = "",
    current_path: str = "",
    regression_threshold: float = -0.5,
) -> str:
    baseline = {row_key(row): row for row in baseline_rows}
    current = {row_key(row): row for row in current_rows}
    common_keys = sorted(set(baseline) & set(current))
    added = sorted(set(current) - set(baseline))
    removed = sorted(set(baseline) - set(current))
    paired = []
    for key in common_keys:
        old = baseline[key]
        new = current[key]
        old_score = score(old)
        new_score = score(new)
        if old_score is None or new_score is None:
            continue
        paired.append(
            {
                "key": key,
                "case_id": key[0],
                "model": key[1],
                "trial": key[2],
                "module": group_key(new, "module"),
                "category": group_key(new, "category"),
                "old_score": old_score,
                "new_score": new_score,
                "delta": new_score - old_score,
                "old_failure": old.get("failure_type", ""),
                "new_failure": new.get("failure_type", ""),
            }
        )

    lines = [
        "# Eval Run Delta Report",
        "",
        "## Scope",
        "",
        f"- Baseline: `{baseline_path}`" if baseline_path else "- Baseline: n/a",
        f"- Current: `{current_path}`" if current_path else "- Current: n/a",
        f"- Baseline rows: {len(baseline_rows)}",
        f"- Current rows: {len(current_rows)}",
        f"- Matched case/model/trial rows with numeric scores: {len(paired)}",
        f"- Added rows: {len(added)}",
        f"- Removed rows: {len(removed)}",
        "",
    ]
    if not paired:
        lines.append("No comparable scored rows found.")
        return "\n".join(lines) + "\n"

    deltas = [row["delta"] for row in paired]
    regressions = [row for row in paired if row["delta"] <= regression_threshold]
    improvements = [row for row in paired if row["delta"] >= abs(regression_threshold)]
    lines.extend(
        [
            "## Executive Summary",
            "",
            f"- Mean score delta: {fmt(mean(deltas))}",
            f"- Regressions <= {regression_threshold:+.2f}: {len(regressions)}",
            f"- Improvements >= {abs(regression_threshold):+.2f}: {len(improvements)}",
            "",
        ]
    )

    for field, title in [("model", "By Model"), ("module", "By Module"), ("category", "By Category")]:
        lines.extend([f"## {title}", "", "| Group | Rows | Baseline mean | Current mean | Delta |", "|---|---:|---:|---:|---:|"])
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in paired:
            grouped[row[field]].append(row)
        for name, rows in sorted(grouped.items()):
            old_mean = mean([row["old_score"] for row in rows])
            new_mean = mean([row["new_score"] for row in rows])
            delta = None if old_mean is None or new_mean is None else new_mean - old_mean
            lines.append(f"| {md(name)} | {len(rows)} | {fmt(old_mean)} | {fmt(new_mean)} | {fmt(delta)} |")
        lines.append("")

    failure_changes = Counter(
        (row["old_failure"] or "none", row["new_failure"] or "none")
        for row in paired
        if (row["old_failure"] or "none") != (row["new_failure"] or "none")
    )
    lines.extend(["## Failure-Type Changes", "", "| Baseline failure | Current failure | Rows |", "|---|---|---:|"])
    if failure_changes:
        for (old_failure, new_failure), count in failure_changes.most_common(15):
            lines.append(f"| {md(old_failure)} | {md(new_failure)} | {count} |")
    else:
        lines.append("| none | none | 0 |")
    lines.append("")

    lines.extend(["## Largest Regressions", "", "| Case | Model | Module | Category | Baseline | Current | Delta | Failure change |", "|---|---|---|---|---:|---:|---:|---|"])
    for row in sorted(paired, key=lambda item: item["delta"])[:15]:
        if row["delta"] >= 0:
            break
        lines.append(delta_row(row))
    lines.append("")

    lines.extend(["## Largest Improvements", "", "| Case | Model | Module | Category | Baseline | Current | Delta | Failure change |", "|---|---|---|---|---:|---:|---:|---|"])
    for row in sorted(paired, key=lambda item: item["delta"], reverse=True)[:15]:
        if row["delta"] <= 0:
            break
        lines.append(delta_row(row))
    lines.append("")

    lines.extend(
        [
            "## Operating Note",
            "",
            "- Treat this as a regression triage report, not a significance test.",
            "- Use paired statistical tests for formal model comparisons; use this report to find what changed and where to inspect traces.",
        ]
    )
    return "\n".join(lines) + "\n"


def delta_row(row: dict[str, Any]) -> str:
    failure = f"{row['old_failure'] or 'none'} -> {row['new_failure'] or 'none'}"
    return (
        f"| {md(row['case_id'])} | {md(row['model'])} | {md(row['module'])} | {md(row['category'])} | "
        f"{row['old_score']:.2f} | {row['new_score']:.2f} | {row['delta']:+.2f} | {md(failure)} |"
    )


def md(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")[:200]


def main() -> int:
    args = parse_args()
    baseline = read_csv(args.baseline)
    current = read_csv(args.current)
    report = build_delta_report(
        baseline,
        current,
        args.baseline,
        args.current,
        args.regression_threshold,
    )
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"Run delta report: {args.out}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
