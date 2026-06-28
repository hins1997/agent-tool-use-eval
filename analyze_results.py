"""Merge automatic and human scores, then generate an evidence-based report draft."""

from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze agent behavior evaluation results")
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--merged-output", type=Path)
    parser.add_argument("--allow-dry-run", action="store_true")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_optional_int(value: Any) -> int | None:
    text = str(value or "").strip()
    if not text or text.upper() in {"PENDING", "N/A", "NONE"}:
        return None
    try:
        number = int(float(text))
    except ValueError:
        return None
    return number


def parse_optional_float(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def merge_reviews(
    rows: list[dict[str, str]],
    reviews: list[dict[str, str]],
) -> list[dict[str, str]]:
    review_index = {
        (row.get("case_id", ""), row.get("model", "")): row for row in reviews
    }
    merged: list[dict[str, str]] = []
    for row in rows:
        item = dict(row)
        review = review_index.get((row.get("case_id", ""), row.get("model", "")))
        if review:
            result_score = review.get("result_score_0_2", "").strip()
            reasoning_score = review.get("reasoning_score_0_2", "").strip()
            if result_score:
                item["result_score"] = result_score
            if reasoning_score:
                item["reasoning_score"] = reasoning_score
            manual_failure = review.get("manual_failure_type", "").strip()
            item["manual_failure_type"] = manual_failure
            item["review_notes"] = review.get("review_notes", "").strip()
            trajectory = parse_optional_int(item.get("trajectory_score"))
            result = parse_optional_int(item.get("result_score"))
            reasoning = parse_optional_int(item.get("reasoning_score"))
            if None not in (trajectory, result, reasoning):
                item["total_score"] = str(trajectory + result + reasoning)
        merged.append(item)
    return merged


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def pct(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "N/A"
    return f"{numerator / denominator:.1%}"


def format_number(value: float | None, digits: int = 2) -> str:
    if value is None or math.isnan(value):
        return "N/A"
    return f"{value:.{digits}f}"


def effective_failure(row: dict[str, str]) -> str:
    manual = row.get("manual_failure_type", "").strip()
    if manual:
        return manual
    return row.get("failure_type", "").strip() or "unclassified"


def build_metrics(rows: list[dict[str, str]]) -> dict[str, Any]:
    models = sorted({row.get("model", "") for row in rows if row.get("model")})
    cases = sorted({row.get("case_id", "") for row in rows if row.get("case_id")})
    categories = sorted({row.get("category", "") for row in rows if row.get("category")})
    modules = sorted({row.get("module", "tool_use_reliability") for row in rows})
    autonomy_layers = sorted(
        {row.get("autonomy_layer", "") for row in rows if row.get("autonomy_layer")}
    )
    expected_rows = len(models) * len(cases)

    by_model: dict[str, dict[str, Any]] = {}
    by_model_module: dict[tuple[str, str], dict[str, Any]] = {}
    by_model_autonomy_layer: dict[tuple[str, str], dict[str, Any]] = {}
    by_model_category: dict[tuple[str, str], dict[str, Any]] = {}
    failures: Counter[str] = Counter()
    reviewed_rows = 0
    reviewed_complete = 0
    total_cost = 0.0
    cost_rows = 0

    for row in rows:
        model = row.get("model", "")
        module = row.get("module", "tool_use_reliability") or "tool_use_reliability"
        layer = row.get("autonomy_layer", "")
        category = row.get("category", "")
        trajectory = parse_optional_int(row.get("trajectory_score"))
        result = parse_optional_int(row.get("result_score"))
        reasoning = parse_optional_int(row.get("reasoning_score"))
        total = parse_optional_int(row.get("total_score"))
        cost = parse_optional_float(row.get("estimated_cost_cny"))

        bucket = by_model.setdefault(
            model,
            {
                "rows": 0,
                "trajectory": [],
                "full_trajectory": 0,
                "reviewed": 0,
                "completed": 0,
                "total": [],
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0,
            },
        )
        bucket["rows"] += 1
        if trajectory is not None:
            bucket["trajectory"].append(float(trajectory))
            if trajectory == 3:
                bucket["full_trajectory"] += 1
        if result is not None and reasoning is not None:
            bucket["reviewed"] += 1
            reviewed_rows += 1
            if result == 2:
                bucket["completed"] += 1
                reviewed_complete += 1
        if total is not None:
            bucket["total"].append(float(total))
        bucket["input_tokens"] += parse_optional_int(row.get("input_tokens")) or 0
        bucket["output_tokens"] += parse_optional_int(row.get("output_tokens")) or 0
        if cost is not None:
            bucket["cost"] += cost
            total_cost += cost
            cost_rows += 1

        module_bucket = by_model_module.setdefault(
            (model, module),
            {"trajectory": [], "reviewed": 0, "completed": 0, "total": []},
        )
        if trajectory is not None:
            module_bucket["trajectory"].append(float(trajectory))
        if result is not None and reasoning is not None:
            module_bucket["reviewed"] += 1
            if result == 2:
                module_bucket["completed"] += 1
        if total is not None:
            module_bucket["total"].append(float(total))

        if layer:
            layer_bucket = by_model_autonomy_layer.setdefault(
                (model, layer),
                {"trajectory": [], "reviewed": 0, "completed": 0, "total": []},
            )
            if trajectory is not None:
                layer_bucket["trajectory"].append(float(trajectory))
            if result is not None and reasoning is not None:
                layer_bucket["reviewed"] += 1
                if result == 2:
                    layer_bucket["completed"] += 1
            if total is not None:
                layer_bucket["total"].append(float(total))

        category_bucket = by_model_category.setdefault(
            (model, category),
            {"trajectory": [], "reviewed": 0, "completed": 0, "total": []},
        )
        if trajectory is not None:
            category_bucket["trajectory"].append(float(trajectory))
        if result is not None and reasoning is not None:
            category_bucket["reviewed"] += 1
            if result == 2:
                category_bucket["completed"] += 1
        if total is not None:
            category_bucket["total"].append(float(total))

        failure = effective_failure(row)
        if failure not in {"none", "manual_behavior_review", ""}:
            failures[failure] += 1

    return {
        "rows": len(rows),
        "models": models,
        "cases": cases,
        "categories": categories,
        "modules": modules,
        "autonomy_layers": autonomy_layers,
        "expected_rows": expected_rows,
        "by_model": by_model,
        "by_model_module": by_model_module,
        "by_model_autonomy_layer": by_model_autonomy_layer,
        "by_model_category": by_model_category,
        "failures": failures,
        "reviewed_rows": reviewed_rows,
        "reviewed_complete": reviewed_complete,
        "total_cost": total_cost,
        "cost_rows": cost_rows,
    }


def derive_findings(metrics: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    model_means = []
    for model, bucket in metrics["by_model"].items():
        value = mean(bucket["trajectory"])
        if value is not None:
            model_means.append((value, model))
    if model_means:
        best_value, best_model = max(model_means)
        findings.append(
            f"{best_model} 的平均轨迹分最高，为 {best_value:.2f}/3。"
        )

    drops = []
    for model in metrics["models"]:
        normal = metrics["by_model_category"].get((model, "normal"), {})
        normal_mean = mean(normal.get("trajectory", []))
        if normal_mean is None:
            continue
        for category in metrics["categories"]:
            if category == "normal":
                continue
            bucket = metrics["by_model_category"].get((model, category), {})
            category_mean = mean(bucket.get("trajectory", []))
            if category_mean is not None:
                drops.append((normal_mean - category_mean, model, category, category_mean))
    if drops:
        drop, model, category, category_mean = max(drops)
        findings.append(
            f"{model} 在 {category} 场景相对正常场景下降最大，下降 {drop:.2f} 分，"
            f"该场景均分为 {category_mean:.2f}/3。"
        )

    if metrics["failures"]:
        failure, count = metrics["failures"].most_common(1)[0]
        total_failures = sum(metrics["failures"].values())
        findings.append(
            f"最常见失败类型是 {failure}，共 {count} 次，占已分类失败的 "
            f"{count / total_failures:.1%}。"
        )
    elif metrics["reviewed_rows"] == 0:
        findings.append("人工复核尚未填写，暂时只能报告轨迹层，不能声称任务完成率。")
    else:
        findings.append("当前已复核样本中未记录有效失败类型，需要检查人工分类字段。")
    return findings[:3]


def render_report(metrics: dict[str, Any], source: Path, review: Path | None) -> str:
    findings = derive_findings(metrics)
    lines = [
        "# Agent 行为评测：自动分析草稿",
        "",
        "> 本文由结果分析器生成。发布前必须回看代表性 trace，并补充方法解释。框架包含工具调用可靠性和自主性边界控制两个模块。",
        "",
        "## 数据完整性",
        "",
        f"- 自动结果：`{source}`",
        f"- 人工复核：`{review}`" if review else "- 人工复核：未提供",
        f"- 模型数：{len(metrics['models'])}",
        f"- Case 数：{len(metrics['cases'])}",
        f"- 评测模块：{', '.join(metrics['modules'])}",
        f"- 自主性层级：{', '.join(metrics['autonomy_layers'])}" if metrics["autonomy_layers"] else "- 自主性层级：N/A",
        f"- 结果行数：{metrics['rows']} / 预期 {metrics['expected_rows']}",
        f"- 人工复核：{metrics['reviewed_rows']} / {metrics['rows']} "
        f"({pct(metrics['reviewed_rows'], metrics['rows'])})",
        "",
        "## 三个数字发现",
        "",
    ]
    for index, finding in enumerate(findings, 1):
        lines.append(f"{index}. {finding}")

    lines.extend(
        [
            "",
            "## 分模型结果",
            "",
            "| 模型 | 行数 | 平均轨迹分 | 轨迹满分率 | 已复核 | 任务完成率* | 平均总分* | 输入/输出Token | 估算成本(CNY) |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for model in metrics["models"]:
        bucket = metrics["by_model"][model]
        lines.append(
            f"| {model} | {bucket['rows']} | {format_number(mean(bucket['trajectory']))}/3 | "
            f"{pct(bucket['full_trajectory'], len(bucket['trajectory']))} | "
            f"{bucket['reviewed']} | {pct(bucket['completed'], bucket['reviewed'])} | "
            f"{format_number(mean(bucket['total']))}/7 | "
            f"{bucket['input_tokens']}/{bucket['output_tokens']} | {bucket['cost']:.4f} |"
        )

    lines.extend(
        [
            "",
            "## 分模块轨迹分",
            "",
            "| 模型 | 工具调用可靠性 | 自主性边界控制 |",
            "|---|---:|---:|",
        ]
    )
    module_labels = [
        ("tool_use_reliability", "工具调用可靠性"),
        ("autonomy_boundary", "自主性边界控制"),
    ]
    for model in metrics["models"]:
        values = []
        for module, _label in module_labels:
            bucket = metrics["by_model_module"].get((model, module), {})
            values.append(f"{format_number(mean(bucket.get('trajectory', [])))}/3")
        lines.append(f"| {model} | {' | '.join(values)} |")

    if metrics["autonomy_layers"]:
        lines.extend(
            [
                "",
                "## 自主性分层轨迹分",
                "",
                "| 模型 | 单轮边界 | 多轮边界 |",
                "|---|---:|---:|",
            ]
        )
        for model in metrics["models"]:
            values = []
            for layer in ["single_turn", "multi_turn"]:
                bucket = metrics["by_model_autonomy_layer"].get((model, layer), {})
                values.append(f"{format_number(mean(bucket.get('trajectory', [])))}/3")
            lines.append(f"| {model} | {' | '.join(values)} |")

    lines.extend(
        [
            "",
            "\\* 任务完成率和平均总分只基于已人工复核样本。",
            "",
            "## 分场景轨迹分",
            "",
            "| 模型 | normal | boundary | adversarial | long_chain |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    category_order = ["normal", "boundary", "adversarial", "long_chain"]
    for model in metrics["models"]:
        values = []
        for category in category_order:
            bucket = metrics["by_model_category"].get((model, category), {})
            values.append(f"{format_number(mean(bucket.get('trajectory', [])))}/3")
        lines.append(f"| {model} | {' | '.join(values)} |")

    lines.extend(["", "## 失败类型", ""])
    if metrics["failures"]:
        total = sum(metrics["failures"].values())
        lines.extend(["| 类型 | 次数 | 比例 |", "|---|---:|---:|"])
        for failure, count in metrics["failures"].most_common():
            lines.append(f"| {failure} | {count} | {count / total:.1%} |")
    else:
        lines.append("尚无可报告的失败分类。")

    lines.extend(
        [
            "",
            "## 发布前必须补充",
            "",
            "- [ ] 回看至少 3 个代表性失败 trace，确认自动分类没有误导。",
            "- [ ] 解释最严重失败对真实产品的风险，而不只比较平均分。",
            "- [ ] 报告模型实际 model_id、运行日期、样本量和 mock 环境。",
            "- [ ] 明确人工复核分母；未复核数据不得计入任务完成率。",
            "- [ ] 补充样本量、单次运行、单人评分和预设轨迹的限制。",
            "",
        ]
    )
    return "\n".join(lines)


def write_merged(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    if "dryrun" in str(args.results).lower() and not args.allow_dry_run:
        print(
            "Refusing to analyze dry-run output as formal evidence. "
            "Use --allow-dry-run only for testing.",
            file=sys.stderr,
        )
        return 2
    if not args.results.exists():
        print(f"Results file not found: {args.results}", file=sys.stderr)
        return 2
    rows = read_csv(args.results)
    reviews: list[dict[str, str]] = []
    if args.review:
        if not args.review.exists():
            print(f"Review file not found: {args.review}", file=sys.stderr)
            return 2
        reviews = read_csv(args.review)
        rows = merge_reviews(rows, reviews)
    metrics = build_metrics(rows)
    if metrics["rows"] != metrics["expected_rows"]:
        print(
            f"Warning: incomplete matrix: {metrics['rows']} rows, "
            f"expected {metrics['expected_rows']}",
            file=sys.stderr,
        )

    output = args.output or args.results.with_name(
        args.results.stem.replace("eval_results", "analysis") + ".md"
    )
    merged_output = args.merged_output or args.results.with_name(
        args.results.stem.replace("eval_results", "merged_results") + ".csv"
    )
    output.write_text(render_report(metrics, args.results, args.review), encoding="utf-8")
    write_merged(merged_output, rows)
    print(f"Analysis: {output}")
    print(f"Merged results: {merged_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
