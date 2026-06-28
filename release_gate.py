#!/usr/bin/env python3
"""Evaluate launch/release gates for an agent eval run."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate manifest release gates for eval results")
    parser.add_argument("--manifest", default="benchmark_manifest.json")
    parser.add_argument("--results", required=True, nargs="+", help="one or more eval_results CSVs")
    parser.add_argument("--out", default="", help="optional markdown output")
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


def case_prefix_for_suite(suite_id: str) -> str:
    prefixes = {
        "agent_planning": "PL",
        "autonomy_boundary_single_turn": "AB",
        "autonomy_boundary_multiturn": "ABM",
    }
    return prefixes.get(suite_id, "")


def row_matches_suite(row: dict[str, str], suite: dict[str, Any]) -> bool:
    suite_id = suite.get("suite_id", "")
    case_id = row.get("case_id", "")
    category = row.get("category", "")
    module = row.get("module") or "tool_use_reliability"
    if suite_id == "tool_use_reliability":
        return module == "tool_use_reliability" and category in {"normal", "boundary", "adversarial", "long_chain"}
    if suite_id == "agent_planning":
        return module == "agent_planning" or case_id.startswith("PL")
    if suite_id == "autonomy_boundary_single_turn":
        return module == "autonomy_boundary" and case_id.startswith("AB") and not case_id.startswith("ABM")
    if suite_id == "autonomy_boundary_multiturn":
        return module == "autonomy_boundary" and (row.get("autonomy_layer") == "multi_turn" or case_id.startswith("ABM"))
    prefix = case_prefix_for_suite(suite_id)
    return bool(prefix and case_id.startswith(prefix))


def build_release_gate_report(manifest: dict[str, Any], rows: list[dict[str, str]], result_paths: list[str] | None = None) -> str:
    gates = manifest.get("release_gates", {})
    min_mean = float(gates.get("minimum_mean_trajectory_score", 0))
    block_failures = set(gates.get("blocking_failure_types", []))
    warn_failures = set(gates.get("warning_failure_types", []))
    block_dry_run = bool(gates.get("block_on_dry_run", True))

    scores = [value for value in (as_float(row.get("trajectory_score")) for row in rows) if value is not None]
    mean_score = sum(scores) / len(scores) if scores else None
    dry_rows = [
        row
        for row in rows
        if str(row.get("dry_run", "")).lower() == "true"
        or (row.get("input_tokens") == "0" and row.get("output_tokens") == "0")
    ]
    failure_counts = Counter(row.get("failure_type", "") or "none" for row in rows)
    blocking_rows = [row for row in rows if (row.get("failure_type", "") or "none") in block_failures]
    warning_rows = [row for row in rows if (row.get("failure_type", "") or "none") in warn_failures]

    p0_suites = [suite for suite in manifest.get("suites", []) if suite.get("priority") == "P0"]
    covered_p0 = []
    missing_p0 = []
    for suite in p0_suites:
        observed = sum(1 for row in rows if row_matches_suite(row, suite))
        if observed:
            covered_p0.append((suite.get("suite_id", ""), observed))
        else:
            missing_p0.append(suite.get("suite_id", ""))
    coverage_ratio = len(covered_p0) / len(p0_suites) if p0_suites else 1.0
    min_coverage = float(gates.get("minimum_p0_suite_coverage_ratio", 1.0))

    failures = []
    warnings = []
    if mean_score is None:
        failures.append("no numeric trajectory scores")
    elif mean_score < min_mean:
        failures.append(f"mean trajectory score {mean_score:.2f} < gate {min_mean:.2f}")
    if coverage_ratio < min_coverage:
        failures.append(f"P0 coverage {coverage_ratio:.0%} < gate {min_coverage:.0%}; missing {', '.join(missing_p0)}")
    if blocking_rows:
        failures.append(f"{len(blocking_rows)} blocking failure row(s)")
    if block_dry_run and dry_rows:
        failures.append(f"{len(dry_rows)} dry-run-like row(s)")
    if warning_rows:
        warnings.append(f"{len(warning_rows)} warning failure row(s)")

    decision = "FAIL" if failures else ("WARN" if warnings else "PASS")
    lines = [
        "# Release Gate Report",
        "",
        f"- Decision: **{decision}**",
        f"- Results: `{', '.join(result_paths or [])}`",
        f"- Rows: {len(rows)}",
        f"- Mean trajectory score: {mean_score:.2f}" if mean_score is not None else "- Mean trajectory score: n/a",
        f"- P0 suite coverage: {len(covered_p0)}/{len(p0_suites)} ({coverage_ratio:.0%})",
        f"- Blocking failures: {len(blocking_rows)}",
        f"- Warning failures: {len(warning_rows)}",
        f"- Dry-run-like rows: {len(dry_rows)}",
        "",
        "## Gate Failures",
        "",
    ]
    if failures:
        lines.extend(f"- {item}" for item in failures)
    else:
        lines.append("- none")
    lines.extend(["", "## Warnings", ""])
    if warnings:
        lines.extend(f"- {item}" for item in warnings)
    else:
        lines.append("- none")

    lines.extend(["", "## P0 Coverage", "", "| Suite | Observed rows |", "|---|---:|"])
    observed_map = dict(covered_p0)
    for suite in p0_suites:
        suite_id = suite.get("suite_id", "")
        lines.append(f"| {suite_id} | {observed_map.get(suite_id, 0)} |")

    lines.extend(["", "## Failure Distribution", "", "| Failure type | Rows |", "|---|---:|"])
    for failure, count in failure_counts.most_common():
        lines.append(f"| {failure} | {count} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    rows = []
    for path in args.results:
        rows.extend(read_csv(path))
    report = build_release_gate_report(manifest, rows, args.results)
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"Release gate report: {args.out}")
    else:
        print(report)
    return 0 if "- Decision: **FAIL**" not in report else 1


if __name__ == "__main__":
    raise SystemExit(main())
