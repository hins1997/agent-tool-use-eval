#!/usr/bin/env python3
"""Generate a model-card style scorecard for an eval run."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


def read_csv(path: str | None) -> list[dict[str, str]]:
    if not path:
        return []
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def read_csv_many(paths: list[str] | None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths or []:
        rows.extend(read_csv(path))
    return rows


def read_text(path: str | None) -> str:
    if not path:
        return ""
    return Path(path).read_text(encoding="utf-8")


def load_manifest(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def as_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def mean(values: Iterable[float]) -> float | None:
    vals = list(values)
    if not vals:
        return None
    return statistics.fmean(vals)


def fmt(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}"


def fmt_path(path: str | None) -> str:
    if not path:
        return ""
    return path


def fmt_paths(paths: list[str] | None) -> str:
    return ", ".join(paths or [])


def group_rows(rows: list[dict[str, str]], key: str) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row.get(key, "")].append(row)
    return dict(grouped)


def score_by_model(rows: list[dict[str, str]]) -> list[tuple[str, int, float | None, float | None]]:
    out = []
    for model, model_rows in sorted(group_rows(rows, "model").items()):
        total_scores = [v for v in (as_float(r.get("total_score")) for r in model_rows) if v is not None]
        traj_scores = [v for v in (as_float(r.get("trajectory_score")) for r in model_rows) if v is not None]
        out.append((model, len(model_rows), mean(total_scores), mean(traj_scores)))
    return out


def judge_by_model(rows: list[dict[str, str]]) -> list[tuple[str, str, int, float | None, float | None, int]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row.get("judge_alias", ""), row.get("model", ""))].append(row)

    out = []
    for (judge_alias, model), model_rows in sorted(grouped.items()):
        result_scores = [v for v in (as_float(r.get("judge_result_score_0_2")) for r in model_rows) if v is not None]
        reasoning_scores = [v for v in (as_float(r.get("judge_reasoning_score_0_2")) for r in model_rows) if v is not None]
        self_judge_count = sum(1 for r in model_rows if str(r.get("self_judge", "")).lower() == "true")
        out.append((judge_alias, model, len(model_rows), mean(result_scores), mean(reasoning_scores), self_judge_count))
    return out


def review_by_model(rows: list[dict[str, str]]) -> list[tuple[str, int, float | None, float | None, float | None]]:
    out = []
    for model, model_rows in sorted(group_rows(rows, "model").items()):
        result_scores = [v for v in (as_float(r.get("result_score_0_2")) for r in model_rows) if v is not None]
        reasoning_scores = [v for v in (as_float(r.get("reasoning_score_0_2")) for r in model_rows) if v is not None]
        reviewed_totals = []
        for row in model_rows:
            trajectory = as_float(row.get("auto_trajectory_score"))
            result = as_float(row.get("result_score_0_2"))
            reasoning = as_float(row.get("reasoning_score_0_2"))
            if trajectory is not None and result is not None and reasoning is not None:
                reviewed_totals.append(trajectory + result + reasoning)
        out.append((model, len(model_rows), mean(reviewed_totals), mean(result_scores), mean(reasoning_scores)))
    return out


def review_completion(rows: list[dict[str, str]]) -> tuple[int, int]:
    reviewed = sum(1 for r in rows if r.get("result_score_0_2") and r.get("reasoning_score_0_2"))
    return reviewed, len(rows)


def primary_judge_by_model(rows: list[dict[str, str]], primary: str) -> list[tuple[str, int, float | None]]:
    primary_rows = [r for r in rows if r.get("judge_alias", "") == primary]
    out = []
    for model, model_rows in sorted(group_rows(primary_rows, "model").items()):
        totals = []
        for row in model_rows:
            result = as_float(row.get("judge_result_score_0_2"))
            reasoning = as_float(row.get("judge_reasoning_score_0_2"))
            if result is not None and reasoning is not None:
                totals.append(result + reasoning)
        out.append((model, len(model_rows), mean(totals)))
    return out


def best_by_score(rows: list[tuple[str, int, float | None, Any]]) -> tuple[str, float] | None:
    scored = [(name, score) for name, _count, score, *_rest in rows if score is not None]
    if not scored:
        return None
    return max(scored, key=lambda item: item[1])


def suite_rows(manifest: dict[str, Any], rows: list[dict[str, str]]) -> list[tuple[str, str, str, Any, str, int | None]]:
    category_counts = Counter(r.get("category", "") for r in rows)
    out = []
    for suite in manifest.get("suites", []):
        suite_id = suite.get("suite_id", "")
        module = suite.get("module", "")
        case_file = suite.get("case_file", "")
        case_count = suite.get("case_count")
        priority = suite.get("priority", "")
        if suite_id == "tool_use_reliability":
            observed = sum(
                1
                for row in rows
                if row.get("module", "tool_use_reliability") == "tool_use_reliability"
                and row.get("category") in {"normal", "boundary", "adversarial", "long_chain"}
            )
        elif suite_id == "autonomy_boundary_single_turn":
            observed = sum(
                1
                for row in rows
                if row.get("module") == "autonomy_boundary"
                and row.get("case_id", "").startswith("AB")
                and not row.get("case_id", "").startswith("ABM")
            )
        elif suite_id == "autonomy_boundary_multiturn":
            observed = sum(
                1
                for row in rows
                if row.get("module") == "autonomy_boundary"
                and (row.get("autonomy_layer") == "multi_turn" or row.get("case_id", "").startswith("ABM"))
            )
        elif suite_id == "agent_planning":
            observed = sum(
                1
                for row in rows
                if row.get("module") == "agent_planning" or row.get("case_id", "").startswith("PL")
            )
        elif suite_id == "search_deep_research":
            observed = sum(
                1
                for row in rows
                if row.get("category") == "search_research" or row.get("case_id", "").startswith("SR")
            )
        elif suite_id == "permission_boundary":
            observed = sum(
                1
                for row in rows
                if row.get("module") == "autonomy_boundary"
                and (
                    row.get("case_id", "").startswith("PB")
                    or row.get("category", "").startswith("permission_")
                )
            )
        elif suite_id == "stateful_tool_sandbox":
            observed = sum(
                1
                for row in rows
                if row.get("category") == "stateful" or row.get("case_id", "").startswith("ST")
            )
        elif suite_id == "dynamic_user_simulation":
            observed = sum(
                1
                for row in rows
                if row.get("module") == "autonomy_boundary"
                and (row.get("autonomy_layer") == "dynamic" or row.get("case_id", "").startswith("DS"))
            )
        elif suite_id == "agentic_coding":
            observed = sum(
                1
                for row in rows
                if row.get("category") == "agentic_coding" or row.get("case_id", "").startswith("AC")
            )
        elif suite_id == "browser_web":
            observed = sum(
                1
                for row in rows
                if row.get("category") == "browser_web" or row.get("case_id", "").startswith("BW")
            )
        elif suite_id == "tool_use_multiturn":
            observed = sum(
                1
                for row in rows
                if row.get("module", "tool_use_reliability") == "tool_use_reliability"
                and (row.get("category") == "multi_turn" or row.get("case_id", "").startswith("MT"))
            )
        elif suite_id == "paraphrase_robustness":
            observed = sum(
                1
                for row in rows
                if "robust" in row.get("category", "")
                or "paraphrase" in row.get("category", "")
                or row.get("case_id", "").startswith("R")
            )
        else:
            observed = None
        out.append((suite_id, case_file, module, case_count, priority, observed))
    return out


def coverage_gaps(manifest: dict[str, Any], rows: list[dict[str, str]]) -> list[str]:
    gaps = []
    for suite_id, _case_file, _module, case_count, priority, observed in suite_rows(manifest, rows):
        if priority == "P0" and observed == 0:
            cases = case_count if case_count is not None else "n/a"
            gaps.append(f"{suite_id} ({cases} manifest cases) has no observed rows in this run.")
    return gaps


def failure_table(rows: list[dict[str, str]], limit: int = 10) -> list[tuple[str, int]]:
    failures = Counter()
    for row in rows:
        failure = row.get("failure_type") or row.get("manual_failure_type") or ""
        if failure and failure.lower() not in {"none", "pass", "ok"}:
            failures[failure] += 1
    return failures.most_common(limit)


def report_facts(text: str, keywords: list[str], limit: int = 5) -> list[str]:
    facts = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            stripped = stripped[2:].strip()
        if stripped.startswith("> "):
            stripped = stripped[2:].strip()
        if any(keyword in stripped for keyword in keywords):
            facts.append(stripped)
        if len(facts) >= limit:
            break
    return facts


def stats_supports_strong_ranking(stats_text: str) -> bool | None:
    if not stats_text:
        return None
    significant_lines = [line for line in stats_text.splitlines() if "|" in line and "Significant" not in line]
    if any("| yes" in line.lower() for line in significant_lines):
        return True
    if "Significant @0.05" in stats_text and "| no" in stats_text.lower():
        return False
    return None


def render_scorecard(
    manifest: dict[str, Any],
    results: list[dict[str, str]],
    judge_rows: list[dict[str, str]],
    review_rows: list[dict[str, str]],
    report_paths: dict[str, str | None] | None = None,
    report_texts: dict[str, str] | None = None,
) -> str:
    report_paths = report_paths or {}
    report_texts = report_texts or {}
    policy = manifest.get("judge_policy", {})
    primary = policy.get("primary", "")
    review_scores = review_by_model(review_rows) if review_rows else []
    primary_scores = primary_judge_by_model(judge_rows, primary) if judge_rows and primary else []
    best_review = best_by_score(review_scores)
    best_primary = best_by_score(primary_scores)
    strong_ranking = stats_supports_strong_ranking(report_texts.get("stats", ""))
    gaps = coverage_gaps(manifest, results)
    reviewed_rows, review_total_rows = review_completion(review_rows)

    lines = []
    lines.append("# Agent Eval Scorecard")
    lines.append("")
    lines.append(f"- Framework: {manifest.get('framework', 'n/a')}")
    lines.append(f"- Manifest version: {manifest.get('version', 'n/a')}")
    lines.append(f"- Positioning: {manifest.get('positioning', 'n/a')}")
    lines.append("")

    lines.append("## Executive Decision")
    lines.append("")
    if best_review:
        lines.append(f"- Best human-reviewed model in this run: {best_review[0]} ({fmt(best_review[1])} / 7 mean reviewed total).")
    if best_primary:
        lines.append(f"- Best primary-judge model in this run: {best_primary[0]} ({fmt(best_primary[1])} / 4 mean OpenAI-judge total).")
    if strong_ranking is False:
        lines.append("- Ranking strength: directional only; the statistical report did not find pairwise significance at alpha=0.05.")
    elif strong_ranking is True:
        lines.append("- Ranking strength: at least one pairwise comparison is statistically significant at alpha=0.05.")
    else:
        lines.append("- Ranking strength: unknown; no statistical report was provided.")
    if gaps:
        lines.append(f"- Coverage warning: {len(gaps)} P0 suite(s) have no observed rows in this run.")
    else:
        lines.append("- Coverage warning: no missing P0 suites detected for this result file.")
    if review_total_rows and reviewed_rows < review_total_rows:
        lines.append(
            f"- Review warning: only {reviewed_rows}/{review_total_rows} review rows have human result/reasoning scores; unreviewed rows support coverage checks but not formal model-quality claims."
        )
    lines.append("")

    lines.append("## Suite Coverage")
    lines.append("")
    lines.append("| Suite | Case file | Module | Manifest cases | Priority | Observed rows |")
    lines.append("|---|---|---|---:|---|---:|")
    for suite_id, case_file, module, case_count, priority, observed in suite_rows(manifest, results):
        observed_text = str(observed) if observed is not None else "n/a"
        lines.append(f"| {suite_id} | {case_file} | {module} | {case_count if case_count is not None else 'n/a'} | {priority} | {observed_text} |")
    lines.append("")
    if gaps:
        lines.append("Missing P0 coverage:")
        lines.append("")
        for gap in gaps:
            lines.append(f"- {gap}")
        lines.append("")

    lines.append("## Rule Score By Model")
    lines.append("")
    lines.append("| Model | Rows | Mean total score | Mean trajectory score |")
    lines.append("|---|---:|---:|---:|")
    for model, count, total, traj in score_by_model(results):
        lines.append(f"| {model} | {count} | {fmt(total)} | {fmt(traj)} |")
    lines.append("")

    if review_rows:
        lines.append("## Human Review Coverage")
        lines.append("")
        lines.append(f"- Review rows: {len(review_rows)}")
        lines.append(f"- Rows with human scores: {reviewed_rows}")
        lines.append("")
        lines.append("| Model | Rows | Mean reviewed total | Mean result | Mean reasoning |")
        lines.append("|---|---:|---:|---:|---:|")
        for model, count, total, result, reasoning in review_by_model(review_rows):
            lines.append(f"| {model} | {count} | {fmt(total)} | {fmt(result)} | {fmt(reasoning)} |")
        lines.append("")

    if judge_rows:
        lines.append("## Judge Score By Model")
        lines.append("")
        lines.append(f"- Primary judge: {policy.get('primary', 'n/a')}")
        lines.append(f"- Cross judges: {', '.join(policy.get('cross_judges', [])) or 'n/a'}")
        lines.append("")
        lines.append("| Judge | Evaluated model | Rows | Mean result | Mean reasoning | Self-judge rows |")
        lines.append("|---|---|---:|---:|---:|---:|")
        for judge_alias, model, count, result, reasoning, self_count in judge_by_model(judge_rows):
            lines.append(f"| {judge_alias} | {model} | {count} | {fmt(result)} | {fmt(reasoning)} | {self_count} |")
        lines.append("")
        if primary_scores:
            lines.append("Primary-judge totals:")
            lines.append("")
            lines.append("| Evaluated model | Rows | Mean primary-judge total / 4 |")
            lines.append("|---|---:|---:|")
            for model, count, total in primary_scores:
                lines.append(f"| {model} | {count} | {fmt(total)} |")
            lines.append("")

    failures = failure_table(results)
    if failures:
        lines.append("## Top Failure Types")
        lines.append("")
        lines.append("| Failure type | Count |")
        lines.append("|---|---:|")
        for failure, count in failures:
            lines.append(f"| {failure} | {count} |")
        lines.append("")

    planned = manifest.get("planned_suites", [])
    if planned:
        lines.append("## Roadmap Coverage")
        lines.append("")
        lines.append("| Planned suite | Priority | Purpose |")
        lines.append("|---|---|---|")
        for suite in planned:
            lines.append(f"| {suite.get('suite_id', '')} | {suite.get('priority', '')} | {suite.get('purpose', '')} |")
        lines.append("")

    evidence_items = [
        ("Results CSV", report_paths.get("results")),
        ("Human review CSV", report_paths.get("review")),
        ("Judge CSV", report_paths.get("judge")),
        ("Statistics report", report_paths.get("stats")),
        ("Causal report", report_paths.get("causal")),
        ("Power report", report_paths.get("power")),
        ("Judge-vs-rule report", report_paths.get("judge_compare")),
        ("Judge bias report", report_paths.get("judge_bias")),
        ("Full analysis report", report_paths.get("analysis")),
    ]
    lines.append("## Evidence Index")
    lines.append("")
    lines.append("| Artifact | Path |")
    lines.append("|---|---|")
    for label, path in evidence_items:
        if path:
            lines.append(f"| {label} | `{fmt_path(path)}` |")
    lines.append("")

    lines.append("## Supporting Signals")
    lines.append("")
    snippets = {
        "stats": report_facts(report_texts.get("stats", ""), ["Rows analysed", "CIs this wide", "Significant", "Cohen's kappa"], 5),
        "causal": report_facts(report_texts.get("causal", ""), ["SRM", "balanced", "McNemar", "No paraphrase"], 5),
        "power": report_facts(report_texts.get("power", ""), ["Cases in this run", "MDE", "Detecting", "Practical split"], 5),
        "judge_compare": report_facts(report_texts.get("judge_compare", ""), ["Pearson", "Cohen's kappa", "Items compared"], 5),
        "judge_bias": report_facts(report_texts.get("judge_bias", ""), ["Self-judge rows", "Self-Judge Delta", "Operating Rule"], 5),
    }
    for name, facts in snippets.items():
        if facts:
            lines.append(f"### {name.replace('_', ' ').title()}")
            lines.append("")
            for fact in facts:
                lines.append(f"- {fact}")
            lines.append("")

    lines.append("## Limitations And Required Next Runs")
    lines.append("")
    lines.append("- Current tools are local mocks; this is appropriate for deterministic behavior evaluation but not yet a substitute for browser, OS, or production API environment tests.")
    if gaps:
        lines.append("- This scorecard should not be treated as a full framework-level release result until the missing P0 suites above are run.")
    if review_total_rows and reviewed_rows < review_total_rows:
        lines.append("- Unreviewed rows should be treated as coverage/smoke evidence only until human review or calibrated judge review is complete.")
    lines.append("- Current ranking should be framed with the statistical and power reports; small-N directional ordering is not the same as a significant model-quality claim.")
    lines.append("- Self-family judge rows are reported for bias diagnostics and should not be the sole evidence for a model's official score.")
    lines.append("- The next frontier-style additions are larger realistic environments, OS/computer-use tasks, and real API/browser harnesses.")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="benchmark_manifest.json")
    parser.add_argument("--results", required=True, nargs="+")
    parser.add_argument("--judge-csv", nargs="+")
    parser.add_argument("--review", nargs="+")
    parser.add_argument("--stats-report")
    parser.add_argument("--causal-report")
    parser.add_argument("--power-report")
    parser.add_argument("--judge-compare-report")
    parser.add_argument("--judge-bias-report")
    parser.add_argument("--analysis-report")
    parser.add_argument("--out")
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    results = read_csv_many(args.results)
    judge_rows = read_csv_many(args.judge_csv)
    review_rows = read_csv_many(args.review)
    report_paths = {
        "results": fmt_paths(args.results),
        "judge": fmt_paths(args.judge_csv),
        "review": fmt_paths(args.review),
        "stats": args.stats_report,
        "causal": args.causal_report,
        "power": args.power_report,
        "judge_compare": args.judge_compare_report,
        "judge_bias": args.judge_bias_report,
        "analysis": args.analysis_report,
    }
    report_texts = {
        "stats": read_text(args.stats_report),
        "causal": read_text(args.causal_report),
        "power": read_text(args.power_report),
        "judge_compare": read_text(args.judge_compare_report),
        "judge_bias": read_text(args.judge_bias_report),
        "analysis": read_text(args.analysis_report),
    }
    report = render_scorecard(manifest, results, judge_rows, review_rows, report_paths, report_texts)

    if args.out:
        Path(args.out).write_text(report + "\n", encoding="utf-8")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
