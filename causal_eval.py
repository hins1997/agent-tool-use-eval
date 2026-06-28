"""
Causal / experimental-design layer for model evaluation.

A benchmark comparison is an experiment, and the same rigor that makes an A/B
test trustworthy applies here. The naive "model A scored higher than model B"
ignores that both models were tested on the *same cases* — a paired/blocked
design — and that case difficulty is a huge nuisance variable. Treating the
comparison causally does three things a raw mean cannot:

1. **Blocking on case** removes case-difficulty variance, so the model effect is
   estimated from within-case differences (the paired design). This is the
   eval analogue of a blocked/paired A/B test.
2. **CUPED variance reduction** uses a pre-defined covariate (here: how hard the
   case was for the *other* models, computed leave-one-out) to shrink the
   variance of the model-mean estimate without bias — the same technique used to
   make online experiments more sensitive.
3. **Correct paired hypothesis tests** for the actual outcome type: McNemar's
   exact test for the binary success outcome (not a t-test on means), reported
   with discordant-pair counts.

It also runs an **SRM (sample-ratio mismatch) guard** — if the models did not
all see the same number of cases, the comparison is confounded before it starts.

Pure standard library. Designed to run on the real `eval_results_*.csv`. Refuses
dry-run inputs. When a paraphrase-robustness result file is passed, it also
estimates the *causal effect of rewording* on the score (a paired perturbation
contrast).

Usage:
    python3 causal_eval.py --results results/<eval_results>.csv
    python3 causal_eval.py --results <auto.csv> --robustness-results <para.csv> \
        --robustness-cases cases_paraphrase_robustness.jsonl
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

from eval_runner import load_jsonl

FULL = 3  # trajectory full score
DEFAULT_BOOT = 10000
DEFAULT_MC = 50000


# --------------------------------------------------------------------------- #
# IO + guards
# --------------------------------------------------------------------------- #
def load_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"No rows in {path}")
    return rows


def guard_not_dry_run(path: Path, rows: list[dict[str, Any]]) -> None:
    if "dry" in str(path).lower():
        raise SystemExit(f"Refusing dry-run input '{path}'.")
    if not any(int(r.get("input_tokens") or 0) + int(r.get("output_tokens") or 0) > 0 for r in rows):
        raise SystemExit(
            f"'{path}' has zero token usage on every row (dry-run signature); causal "
            "analysis blocked to avoid treating simulated outputs as evidence."
        )


def score_matrix(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """case_id -> {model: trajectory_score}."""
    matrix: dict[str, dict[str, float]] = defaultdict(dict)
    for row in rows:
        matrix[row["case_id"]][row["model"]] = float(row["trajectory_score"])
    return matrix


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def variance(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


# --------------------------------------------------------------------------- #
# 1. SRM guard
# --------------------------------------------------------------------------- #
def srm_check(rows: list[dict[str, Any]], n_mc: int, rng: random.Random) -> dict[str, Any]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[row["model"]] += 1
    models = sorted(counts)
    observed = [counts[m] for m in models]
    total = sum(observed)
    k = len(models)
    expected = total / k
    chi_sq = sum((o - expected) ** 2 / expected for o in observed)
    # Monte Carlo p-value under equal-allocation multinomial.
    extreme = 0
    for _ in range(n_mc):
        sim = [0] * k
        for _ in range(total):
            sim[rng.randrange(k)] += 1
        stat = sum((s - expected) ** 2 / expected for s in sim)
        if stat >= chi_sq - 1e-12:
            extreme += 1
    p = (extreme + 1) / (n_mc + 1)
    return {"counts": dict(counts), "chi_sq": chi_sq, "p_value": p, "balanced": p > 0.01}


# --------------------------------------------------------------------------- #
# 2. McNemar exact paired test (binary success)
# --------------------------------------------------------------------------- #
def mcnemar_exact(matrix: dict[str, dict[str, float]], a: str, b: str) -> dict[str, Any]:
    b_only = c_only = both = neither = 0
    for scores in matrix.values():
        if a not in scores or b not in scores:
            continue
        sa = scores[a] >= FULL
        sb = scores[b] >= FULL
        if sa and not sb:
            b_only += 1
        elif sb and not sa:
            c_only += 1
        elif sa and sb:
            both += 1
        else:
            neither += 1
    n = b_only + c_only
    if n == 0:
        p = 1.0
    else:
        tail = sum(math.comb(n, k) for k in range(0, min(b_only, c_only) + 1)) * (0.5 ** n)
        p = min(1.0, 2 * tail)
    return {
        "a_success_b_fail": b_only,
        "b_success_a_fail": c_only,
        "both_success": both,
        "both_fail": neither,
        "discordant": n,
        "p_value": p,
    }


# --------------------------------------------------------------------------- #
# 3. Case-blocked (paired) model effect + variance reduction from blocking
# --------------------------------------------------------------------------- #
def blocked_effect(
    matrix: dict[str, dict[str, float]], a: str, b: str, n_boot: int, rng: random.Random
) -> dict[str, Any]:
    """Within-case difference a-b (paired design) with cluster bootstrap CI.

    Also reports how much the paired (blocked) design reduces the variance of the
    mean-difference estimate versus treating the two arms as independent samples.
    """
    diffs = []
    a_vals = []
    b_vals = []
    for scores in matrix.values():
        if a in scores and b in scores:
            diffs.append(scores[a] - scores[b])
            a_vals.append(scores[a])
            b_vals.append(scores[b])
    n = len(diffs)
    if n < 2:
        return {"n": n, "effect": mean(diffs), "ci": (float("nan"), float("nan"))}
    effect = mean(diffs)
    # Cluster (case) bootstrap.
    samples = []
    for _ in range(n_boot):
        resample = [diffs[rng.randrange(n)] for _ in range(n)]
        samples.append(mean(resample))
    samples.sort()
    lo = samples[int(0.025 * (len(samples) - 1))]
    hi = samples[int(0.975 * (len(samples) - 1))]
    # Variance of mean difference: paired vs unpaired.
    var_paired = variance(diffs) / n
    var_unpaired = variance(a_vals) / n + variance(b_vals) / n
    reduction = 1 - (var_paired / var_unpaired) if var_unpaired > 0 else 0.0
    return {
        "n": n,
        "effect": effect,
        "ci": (lo, hi),
        "var_paired": var_paired,
        "var_unpaired": var_unpaired,
        "variance_reduction_from_blocking": reduction,
    }


# --------------------------------------------------------------------------- #
# 4. CUPED variance reduction on a model's mean score
# --------------------------------------------------------------------------- #
def cuped(matrix: dict[str, dict[str, float]], model: str) -> dict[str, Any]:
    """Reduce variance of model's mean trajectory score using a leave-one-out
    case-difficulty covariate (mean score of the OTHER models on the same case).
    """
    xs = []
    covs = []
    for scores in matrix.values():
        if model not in scores:
            continue
        others = [v for m, v in scores.items() if m != model]
        if not others:
            continue
        xs.append(scores[model])
        covs.append(mean(others))
    n = len(xs)
    if n < 2 or variance(covs) == 0:
        return {"n": n, "applicable": False}
    cov_mean = mean(covs)
    cov_xy = sum((x - mean(xs)) * (c - cov_mean) for x, c in zip(xs, covs)) / (n - 1)
    theta = cov_xy / variance(covs)
    adjusted = [x - theta * (c - cov_mean) for x, c in zip(xs, covs)]
    var_before = variance(xs) / n
    var_after = variance(adjusted) / n
    reduction = 1 - (var_after / var_before) if var_before > 0 else 0.0
    return {
        "n": n,
        "applicable": True,
        "theta": theta,
        "mean": mean(xs),
        "se_before": math.sqrt(var_before),
        "se_after": math.sqrt(var_after),
        "variance_reduction": reduction,
    }


# --------------------------------------------------------------------------- #
# 5. Paraphrase perturbation causal effect (paired canonical vs variant)
# --------------------------------------------------------------------------- #
def perturbation_effect(
    cases: list[dict[str, Any]], rows: list[dict[str, Any]], n_boot: int, rng: random.Random
) -> dict[str, Any]:
    base_of = {c["id"]: c.get("base_id", c["id"]) for c in cases}
    variant_of = {c["id"]: c.get("variant_type", "?") for c in cases}
    # (model, base) -> {variant_type: score}
    by_group: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    for row in rows:
        cid = row["case_id"]
        if cid not in base_of:
            continue
        by_group[(row["model"], base_of[cid])][variant_of[cid]] = float(row["trajectory_score"])
    per_model: dict[str, list[float]] = defaultdict(list)
    for (model, _base), variants in by_group.items():
        if "canonical" not in variants:
            continue
        canon = variants["canonical"]
        for vtype, score in variants.items():
            if vtype == "canonical":
                continue
            per_model[model].append(score - canon)  # effect of rewording on score
    out: dict[str, Any] = {}
    for model, diffs in per_model.items():
        if not diffs:
            continue
        effect = mean(diffs)
        samples = sorted(mean([diffs[rng.randrange(len(diffs))] for _ in diffs]) for _ in range(n_boot))
        lo = samples[int(0.025 * (len(samples) - 1))]
        hi = samples[int(0.975 * (len(samples) - 1))]
        out[model] = {"n_contrasts": len(diffs), "mean_effect": effect, "ci": (lo, hi)}
    return out


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
def build_report(
    rows: list[dict[str, Any]],
    robustness_cases: Optional[list[dict[str, Any]]],
    robustness_rows: Optional[list[dict[str, Any]]],
    n_boot: int,
    n_mc: int,
    seed: int,
) -> str:
    rng = random.Random(seed)
    matrix = score_matrix(rows)
    models = sorted({r["model"] for r in rows})
    L: list[str] = ["# Causal / Experimental-Design Analysis", ""]
    L.append(f"- Seed {seed} | bootstrap {n_boot} | MC {n_mc} | models: {', '.join(models)}")
    L.append("- Outcome for binary tests: trajectory full score (==3).")
    L.append("")

    # SRM
    srm = srm_check(rows, n_mc, rng)
    L.append("## 0. SRM (sample-ratio mismatch) guard")
    L.append("")
    L.append(f"- Per-model case counts: {srm['counts']}")
    L.append(f"- Chi-square {srm['chi_sq']:.3f}, MC p={srm['p_value']:.3f} -> "
             f"{'balanced, comparison not confounded by allocation' if srm['balanced'] else 'IMBALANCED: investigate before comparing'}")
    L.append("")

    # Blocked effect + McNemar
    L.append("## 1. Paired model comparison: blocked effect + McNemar exact")
    L.append("")
    L.append("| Comparison | Blocked effect (a-b) | 95% CI | Var. reduction from blocking | McNemar discordant (a>b / b>a) | McNemar p |")
    L.append("|---|---:|---:|---:|:--:|---:|")
    for i in range(len(models)):
        for j in range(i + 1, len(models)):
            a, b = models[i], models[j]
            be = blocked_effect(matrix, a, b, n_boot, rng)
            mc = mcnemar_exact(matrix, a, b)
            L.append(
                f"| {a} vs {b} | {be['effect']:+.2f} | [{be['ci'][0]:+.2f}, {be['ci'][1]:+.2f}] | "
                f"{be.get('variance_reduction_from_blocking', 0):.0%} | "
                f"{mc['a_success_b_fail']} / {mc['b_success_a_fail']} | {mc['p_value']:.3f} |"
            )
    L.append("")
    L.append("> Blocking on case (the paired design) is what makes a small benchmark usable: "
             "it strips out case-difficulty variance so the model effect is read from within-case "
             "differences. McNemar tests the binary success outcome correctly via discordant pairs.")
    L.append("")

    # CUPED
    L.append("## 2. CUPED variance reduction on each model's mean score")
    L.append("")
    L.append("| Model | Mean/3 | SE before | SE after | Variance reduction | theta |")
    L.append("|---|---:|---:|---:|---:|---:|")
    for model in models:
        c = cuped(matrix, model)
        if not c.get("applicable"):
            L.append(f"| {model} | - | - | - | n/a | - |")
            continue
        L.append(
            f"| {model} | {c['mean']:.2f} | {c['se_before']:.3f} | {c['se_after']:.3f} | "
            f"{c['variance_reduction']:.0%} | {c['theta']:+.2f} |"
        )
    L.append("")
    L.append("> CUPED uses a pre-defined covariate (here case difficulty, computed leave-one-out so "
             "it carries no information about the focal model) to shrink the variance of the mean "
             "estimate without bias — the same lever used to make online experiments more sensitive.")
    L.append("")

    # Perturbation effect
    L.append("## 3. Causal effect of rewording (paraphrase robustness)")
    L.append("")
    if robustness_cases and robustness_rows:
        pe = perturbation_effect(robustness_cases, robustness_rows, n_boot, rng)
        if pe:
            L.append("| Model | Contrasts | Mean effect of rewording on score | 95% CI |")
            L.append("|---|---:|---:|---:|")
            for model, d in sorted(pe.items()):
                L.append(f"| {model} | {d['n_contrasts']} | {d['mean_effect']:+.2f} | "
                         f"[{d['ci'][0]:+.2f}, {d['ci'][1]:+.2f}] |")
            L.append("")
            L.append("> Each variant is paired to its canonical phrasing, so the contrast estimates the "
                     "causal effect of surface rewording while holding the task fixed. A CI that excludes "
                     "0 means the model is measurably phrasing-dependent — a contamination/robustness red flag.")
        else:
            L.append("Robustness results supplied but no canonical/variant pairs matched.")
    else:
        L.append("No paraphrase-robustness results supplied. Run `cases_paraphrase_robustness.jsonl` "
                 "and pass `--robustness-results` + `--robustness-cases` to estimate the rewording effect.")
    L.append("")
    L.append("---")
    L.append("_Methods: SRM Monte-Carlo multinomial guard; case-blocked paired effect with cluster "
             "bootstrap; McNemar exact binomial on discordant pairs; CUPED with leave-one-out "
             "difficulty covariate; paired perturbation contrast. Standard library only; reproducible "
             "via the fixed seed._")
    return "\n".join(L) + "\n"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Causal / experimental-design analysis of eval results.")
    p.add_argument("--results", required=True)
    p.add_argument("--robustness-results", default="")
    p.add_argument("--robustness-cases", default="cases_paraphrase_robustness.jsonl")
    p.add_argument("--out", default="")
    p.add_argument("--bootstrap", type=int, default=DEFAULT_BOOT)
    p.add_argument("--mc", type=int, default=DEFAULT_MC)
    p.add_argument("--seed", type=int, default=20260627)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    path = Path(args.results)
    rows = load_rows(path)
    guard_not_dry_run(path, rows)
    rcases = rrows = None
    if args.robustness_results:
        rrows = load_rows(Path(args.robustness_results))
        rcases = load_jsonl(Path(args.robustness_cases))
    report = build_report(rows, rcases, rrows, args.bootstrap, args.mc, args.seed)
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
