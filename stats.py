"""
Statistical rigor layer for the agent-evaluation framework.

The summary tables report point estimates (mean trajectory score, full-score
rate). Point estimates alone are misleading on small benchmarks: with 15 cases
per model a one-point swing on a single case moves the mean by ~0.067, and two
models that look different may not be distinguishable from sampling noise.

This module adds the measurement discipline an evaluation role is expected to
bring:

1. Bootstrap 95% confidence intervals for each model's mean trajectory score and
   full-score rate (BCa-free percentile bootstrap; no third-party deps).
2. Pairwise model comparison with a permutation (randomization) test, reported
   with effect size and a Holm correction for multiple comparisons.
3. Inter-rater / inter-method agreement: raw agreement and Cohen's kappa,
   usable for auto-vs-human or judge-vs-human once a review CSV is filled.

Everything uses only the Python standard library and runs on the real
`eval_results_*.csv` produced by the runner. It deliberately refuses dry-run
inputs, mirroring analyze_results.py, so simulated numbers can never be passed
off as measured ones.

Usage:
    python3 stats.py --results results/eval_results_<run_id>.csv
    python3 stats.py --results <auto.csv> --review <human_review.csv>
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Optional

MAX_TRAJ = 3
DEFAULT_BOOTSTRAP = 10000
DEFAULT_PERMUTATIONS = 20000


# --------------------------------------------------------------------------- #
# IO
# --------------------------------------------------------------------------- #
def load_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"No rows in {path}")
    return rows


def guard_not_dry_run(path: Path, rows: list[dict[str, Any]]) -> None:
    """Refuse obvious dry-run artifacts so simulated scores never become evidence."""
    name = path.name.lower()
    if "dry" in name or "dryrun" in str(path).lower():
        raise SystemExit(
            f"Refusing dry-run input '{path}'. Statistics must run on real model outputs."
        )
    # A real run records non-empty model_id and at least some token usage.
    has_usage = any(
        int(row.get("input_tokens") or 0) + int(row.get("output_tokens") or 0) > 0
        for row in rows
    )
    if not has_usage:
        raise SystemExit(
            f"'{path}' has zero token usage on every row, which is the dry-run signature. "
            "Statistics are blocked to avoid treating simulated outputs as measured evidence."
        )


# --------------------------------------------------------------------------- #
# Bootstrap
# --------------------------------------------------------------------------- #
def percentile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return float("nan")
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = q * (len(sorted_values) - 1)
    low = math.floor(pos)
    high = math.ceil(pos)
    if low == high:
        return sorted_values[low]
    frac = pos - low
    return sorted_values[low] * (1 - frac) + sorted_values[high] * frac


def bootstrap_ci(
    values: list[float],
    statistic,
    n_boot: int,
    rng: random.Random,
    alpha: float = 0.05,
) -> tuple[float, float, float]:
    point = statistic(values)
    n = len(values)
    if n < 2:
        return point, point, point
    samples = []
    for _ in range(n_boot):
        resample = [values[rng.randrange(n)] for _ in range(n)]
        samples.append(statistic(resample))
    samples.sort()
    low = percentile(samples, alpha / 2)
    high = percentile(samples, 1 - alpha / 2)
    return point, low, high


def mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else float("nan")


# --------------------------------------------------------------------------- #
# Permutation test
# --------------------------------------------------------------------------- #
def permutation_test(
    a: list[float],
    b: list[float],
    n_perm: int,
    rng: random.Random,
) -> dict[str, float]:
    """Two-sided permutation test on the difference of means.

    Paired by case when the two groups are equal length (each case is scored by
    both models on the identical prompt), which is the more powerful design.
    """
    observed = mean(a) - mean(b)
    if len(a) == len(b):
        # Paired randomization: flip the sign of each per-case difference.
        diffs = [x - y for x, y in zip(a, b)]
        count = 0
        for _ in range(n_perm):
            total = sum(d if rng.random() < 0.5 else -d for d in diffs)
            if abs(total / len(diffs)) >= abs(observed) - 1e-12:
                count += 1
        design = "paired"
    else:
        pooled = a + b
        na = len(a)
        count = 0
        for _ in range(n_perm):
            rng.shuffle(pooled)
            diff = mean(pooled[:na]) - mean(pooled[na:])
            if abs(diff) >= abs(observed) - 1e-12:
                count += 1
        design = "unpaired"
    p = (count + 1) / (n_perm + 1)  # add-one smoothing, never reports p=0
    # Standardized effect size (Cohen's d, pooled SD).
    effect = cohens_d(a, b)
    return {"observed_diff": observed, "p_value": p, "cohens_d": effect, "design": design}


def cohens_d(a: list[float], b: list[float]) -> float:
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return float("nan")
    va = _variance(a)
    vb = _variance(b)
    pooled = ((na - 1) * va + (nb - 1) * vb) / (na + nb - 2)
    if pooled == 0:
        return 0.0
    return (mean(a) - mean(b)) / math.sqrt(pooled)


def _variance(values: list[float]) -> float:
    m = mean(values)
    return sum((x - m) ** 2 for x in values) / (len(values) - 1)


def holm_correction(pairs: list[tuple[str, float]]) -> dict[str, float]:
    """Holm-Bonferroni adjusted p-values, keyed by the pair label."""
    ordered = sorted(pairs, key=lambda kv: kv[1])
    m = len(ordered)
    adjusted: dict[str, float] = {}
    running_max = 0.0
    for index, (label, p) in enumerate(ordered):
        adj = min(1.0, (m - index) * p)
        running_max = max(running_max, adj)  # enforce monotonicity
        adjusted[label] = running_max
    return adjusted


# --------------------------------------------------------------------------- #
# Agreement / Cohen's kappa
# --------------------------------------------------------------------------- #
def cohens_kappa(rater_a: list[Any], rater_b: list[Any]) -> dict[str, float]:
    """Cohen's kappa for two raters over the same items."""
    paired = [(x, y) for x, y in zip(rater_a, rater_b) if x != "" and y != "" and x is not None and y is not None]
    n = len(paired)
    if n == 0:
        return {"n": 0, "agreement": float("nan"), "kappa": float("nan")}
    labels = sorted({x for x, _ in paired} | {y for _, y in paired}, key=str)
    observed = sum(1 for x, y in paired if x == y) / n
    count_a = {label: 0 for label in labels}
    count_b = {label: 0 for label in labels}
    for x, y in paired:
        count_a[x] += 1
        count_b[y] += 1
    expected = sum((count_a[l] / n) * (count_b[l] / n) for l in labels)
    if expected >= 1.0:
        kappa = float("nan")
    else:
        kappa = (observed - expected) / (1 - expected)
    return {"n": n, "agreement": observed, "kappa": kappa}


def interpret_kappa(kappa: float) -> str:
    if kappa != kappa:  # NaN
        return "n/a"
    if kappa < 0:
        return "worse than chance"
    if kappa < 0.20:
        return "slight"
    if kappa < 0.40:
        return "fair"
    if kappa < 0.60:
        return "moderate"
    if kappa < 0.80:
        return "substantial"
    return "almost perfect"


# --------------------------------------------------------------------------- #
# Report assembly
# --------------------------------------------------------------------------- #
def scores_by_model(rows: list[dict[str, Any]]) -> dict[str, list[float]]:
    out: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        out[row["model"]].append(float(row["trajectory_score"]))
    return dict(out)


def scores_by_case(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """case_id -> {model: score} for paired comparison."""
    out: dict[str, dict[str, float]] = defaultdict(dict)
    for row in rows:
        out[row["case_id"]][row["model"]] = float(row["trajectory_score"])
    return out


def aligned_pair(
    by_case: dict[str, dict[str, float]], model_a: str, model_b: str
) -> tuple[list[float], list[float]]:
    a, b = [], []
    for scores in by_case.values():
        if model_a in scores and model_b in scores:
            a.append(scores[model_a])
            b.append(scores[model_b])
    return a, b


def build_report(
    rows: list[dict[str, Any]],
    review_rows: Optional[list[dict[str, Any]]],
    n_boot: int,
    n_perm: int,
    seed: int,
) -> str:
    rng = random.Random(seed)
    by_model = scores_by_model(rows)
    by_case = scores_by_case(rows)
    models = sorted(by_model)

    lines: list[str] = []
    lines.append("# Statistical Analysis")
    lines.append("")
    lines.append(
        f"- Rows analysed: {len(rows)} | Models: {', '.join(models)} | "
        f"Cases per model: {', '.join(str(len(by_model[m])) for m in models)}"
    )
    lines.append(
        f"- Bootstrap resamples: {n_boot} | Permutations: {n_perm} | Seed: {seed}"
    )
    lines.append("")

    # 1. Confidence intervals
    lines.append("## 1. Mean trajectory score with 95% bootstrap CI")
    lines.append("")
    lines.append("| Model | Mean / 3 | 95% CI | Full-score rate | 95% CI |")
    lines.append("|---|---:|---:|---:|---:|")
    for model in models:
        values = by_model[model]
        m_point, m_lo, m_hi = bootstrap_ci(values, mean, n_boot, rng)
        full = [1.0 if v >= MAX_TRAJ else 0.0 for v in values]
        f_point, f_lo, f_hi = bootstrap_ci(full, mean, n_boot, rng)
        lines.append(
            f"| {model} | {m_point:.2f} | [{m_lo:.2f}, {m_hi:.2f}] | "
            f"{f_point:.0%} | [{f_lo:.0%}, {f_hi:.0%}] |"
        )
    lines.append("")
    min_n = min(len(v) for v in by_model.values()) if by_model else 0
    lines.append(
        f"> CIs this wide at n≈{min_n} per model are the point: rank order is suggestive, "
        "not established. Report it honestly rather than implying precision the sample "
        "size does not support."
    )
    lines.append("")

    # 2. Pairwise significance
    lines.append("## 2. Pairwise model comparison (paired permutation test)")
    lines.append("")
    raw_pairs: list[tuple[str, float]] = []
    detail: dict[str, dict[str, float]] = {}
    for i in range(len(models)):
        for j in range(i + 1, len(models)):
            a_scores, b_scores = aligned_pair(by_case, models[i], models[j])
            result = permutation_test(a_scores, b_scores, n_perm, rng)
            label = f"{models[i]} vs {models[j]}"
            raw_pairs.append((label, result["p_value"]))
            detail[label] = result
    adjusted = holm_correction(raw_pairs)
    lines.append("| Comparison | Mean diff | Cohen's d | p (raw) | p (Holm) | Significant @0.05 |")
    lines.append("|---|---:|---:|---:|---:|:--:|")
    for label, _ in raw_pairs:
        r = detail[label]
        adj = adjusted[label]
        sig = "yes" if adj < 0.05 else "no"
        lines.append(
            f"| {label} | {r['observed_diff']:+.2f} | {r['cohens_d']:+.2f} | "
            f"{r['p_value']:.3f} | {adj:.3f} | {sig} |"
        )
    lines.append("")
    lines.append(
        "> Paired design: both models see the identical case set, so the test is on "
        "per-case score differences. Holm correction guards against false positives "
        "from running several comparisons."
    )
    lines.append("")

    # 3. Agreement
    lines.append("## 3. Scoring-method agreement (Cohen's kappa)")
    lines.append("")
    if review_rows:
        agreement_block = agreement_from_review(rows, review_rows)
        lines.extend(agreement_block)
    else:
        lines.append(
            "No human-review / judge CSV supplied. Agreement quantifies how far the "
            "automatic trajectory label can be trusted as a stand-in for human "
            "judgement; fill a `human_review_*.csv` (or run `llm_judge.py`) and pass "
            "it with `--review` to populate raw agreement and Cohen's kappa here."
        )
    lines.append("")
    lines.append("---")
    lines.append(
        "_Method: percentile bootstrap, two-sided paired permutation test with "
        "add-one smoothing, Holm-Bonferroni multiple-comparison correction, Cohen's "
        "kappa for categorical agreement. Standard library only; reproducible via "
        "the fixed seed above._"
    )
    return "\n".join(lines) + "\n"


def _bucket_trajectory(score: float) -> str:
    """Collapse 0-3 trajectory into a 3-class outcome to compare with a 0-2 human label."""
    if score >= 3:
        return "pass"
    if score <= 0:
        return "fail"
    return "partial"


def _bucket_human(result_score: str) -> Optional[str]:
    try:
        value = int(result_score)
    except (TypeError, ValueError):
        return None
    return {0: "fail", 1: "partial", 2: "pass"}[value] if value in (0, 1, 2) else None


def agreement_from_review(
    rows: list[dict[str, Any]], review_rows: list[dict[str, Any]]
) -> list[str]:
    auto_index = {(r["case_id"], r["model"]): r for r in rows}
    auto_labels: list[str] = []
    human_labels: list[str] = []
    for review in review_rows:
        key = (review.get("case_id"), review.get("model"))
        human = _bucket_human(review.get("result_score_0_2", ""))
        if key not in auto_index or human is None:
            continue
        auto_labels.append(_bucket_trajectory(float(auto_index[key]["trajectory_score"])))
        human_labels.append(human)
    if not auto_labels:
        return [
            "A review CSV was supplied but no rows had a filled `result_score_0_2`. "
            "Once human (or judge) scores are entered, agreement appears here."
        ]
    stats = cohens_kappa(auto_labels, human_labels)
    out = [
        f"Compared automatic trajectory bucket (pass/partial/fail) against the "
        f"human result score on {stats['n']} reviewed items.",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Raw agreement | {stats['agreement']:.1%} |",
        f"| Cohen's kappa | {stats['kappa']:.3f} ({interpret_kappa(stats['kappa'])}) |",
        "",
        "> Low kappa means the cheap automatic score and the expensive human score "
        "disagree often, so the automatic number cannot replace review for those "
        "cases; high kappa justifies trusting automation and reviewing only a sample.",
    ]
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Statistical analysis of eval results.")
    parser.add_argument("--results", required=True, help="eval_results_*.csv from a real run")
    parser.add_argument("--review", default="", help="optional human_review_*.csv with filled scores")
    parser.add_argument("--out", default="", help="optional output markdown path")
    parser.add_argument("--bootstrap", type=int, default=DEFAULT_BOOTSTRAP)
    parser.add_argument("--permutations", type=int, default=DEFAULT_PERMUTATIONS)
    parser.add_argument("--seed", type=int, default=20260627)
    parser.add_argument("--json", action="store_true", help="also print a JSON summary")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results_path = Path(args.results)
    rows = load_rows(results_path)
    guard_not_dry_run(results_path, rows)
    review_rows = None
    if args.review:
        review_rows = load_rows(Path(args.review))
    report = build_report(
        rows, review_rows, args.bootstrap, args.permutations, args.seed
    )
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(report)
    if args.json:
        by_model = scores_by_model(rows)
        print(json.dumps({m: mean(v) for m, v in by_model.items()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
