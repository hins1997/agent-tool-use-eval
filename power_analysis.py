"""
Power & sample-size design for the evaluation.

This is the tool that answers the only question that makes the statistics layer
worth anything: *given the effect I care about, how much data do I need, and
where should that data go — more cases, or more trials per case?*

It computes, on the real run:

1. MDE (minimum detectable effect) at the current number of cases — i.e. the
   smallest model difference this eval could detect at all. If the differences
   you observe are smaller than the MDE, "not significant" is guaranteed by the
   design, not a finding about the models.
2. Required number of CASES to detect a target difference, for both a paired
   mean-score test and a paired success-rate test (McNemar).
3. Required number of TRIALS PER CASE to estimate a single case's success
   probability to a target precision (binomial) — shows why 1 trial per case
   cannot measure per-case reliability.
4. pass^k reliability decay (tau-bench style): the probability an agent succeeds
   on all k independent attempts.
5. The fixed-budget variance decomposition: for a fixed total number of API
   calls, how splitting between cases (N) and trials (K) changes the variance of
   the headline mean — the formal version of "cases vs calls".

Standard library only. References are in METHODOLOGY_AGENT_EVAL.md.

Usage:
    python3 power_analysis.py --results results/real_run_20260627/eval_results_*.csv
    python3 power_analysis.py --results <csv> --target-diff 0.10 --metric success
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

FULL = 3


# ------------------------------ normal quantiles ----------------------------- #
def z(p: float) -> float:
    """Inverse standard-normal CDF (Acklam's rational approximation)."""
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def variance(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


# ------------------------------ data --------------------------------------- #
def load(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as h:
        return list(csv.DictReader(h))


def by_case(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    m: dict[str, dict[str, float]] = defaultdict(dict)
    for r in rows:
        m[r["case_id"]][r["model"]] = float(r["trajectory_score"])
    return m


def paired(matrix, a, b):
    av, bv = [], []
    for s in matrix.values():
        if a in s and b in s:
            av.append(s[a]); bv.append(s[b])
    return av, bv


# ------------------------------ power math --------------------------------- #
def mde_paired_mean(sd_diff: float, n: int, alpha=0.05, power=0.8) -> float:
    return (z(1 - alpha / 2) + z(power)) * sd_diff / math.sqrt(n)


def n_paired_mean(effect: float, sd_diff: float, alpha=0.05, power=0.8) -> float:
    if effect == 0:
        return float("inf")
    return ((z(1 - alpha / 2) + z(power)) * sd_diff / abs(effect)) ** 2


def n_unpaired_props(p1: float, p2: float, alpha=0.05, power=0.8) -> float:
    """Cases per model to detect success-rate difference p1 vs p2 (two-sample)."""
    if p1 == p2:
        return float("inf")
    pbar = (p1 + p2) / 2
    za, zb = z(1 - alpha / 2), z(power)
    num = (za * math.sqrt(2 * pbar * (1 - pbar)) + zb * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    return num / (p1 - p2) ** 2


def n_mcnemar(p1: float, p2: float, corr: float = 0.5, alpha=0.05, power=0.8) -> float:
    """Paired success test. Approximate discordant probs from marginals + a
    within-case correlation, then required number of pairs (cases)."""
    # joint p(both success) under correlation; clamp to valid range.
    p11 = max(min(p1, p2), corr * math.sqrt(p1 * (1 - p1) * p2 * (1 - p2)) + p1 * p2)
    p10 = max(p1 - p11, 1e-6)   # a success, b fail
    p01 = max(p2 - p11, 1e-6)   # b success, a fail
    pdisc = p10 + p01
    diff = p01 - p10
    if abs(diff) < 1e-9:
        return float("inf")
    za, zb = z(1 - alpha / 2), z(power)
    nd = (za * math.sqrt(pdisc) + zb * math.sqrt(pdisc - diff ** 2)) ** 2 / diff ** 2
    return nd / pdisc  # inflate discordant-pair count to total pairs


def trials_for_margin(p: float, margin: float, conf=0.95) -> float:
    return (z(1 - (1 - conf) / 2) ** 2) * p * (1 - p) / margin ** 2


# ------------------------------ report ------------------------------------- #
def build(rows, target_diff, seed_models, alpha, power) -> str:
    matrix = by_case(rows)
    models = sorted({r["model"] for r in rows})
    n_cases = len(matrix)
    L = ["# Power & Sample-Size Design", ""]
    L.append(f"- Cases in this run: {n_cases} | Models: {', '.join(models)} | alpha={alpha}, power={power}")
    L.append("- Outcome: trajectory score (0-3) for mean tests; full-score (==3) for success tests.")
    L.append("")

    # success rates
    succ = {m: mean([1.0 if s.get(m, -1) >= FULL else 0.0 for s in matrix.values() if m in s]) for m in models}
    L.append("## Observed success (full-score) rates")
    L.append("")
    L.append("| Model | success rate |")
    L.append("|---|---:|")
    for m in models:
        L.append(f"| {m} | {succ[m]:.0%} |")
    L.append("")

    # 1. MDE at current N
    L.append(f"## 1. Minimum detectable effect at the current N={n_cases}")
    L.append("")
    L.append("| Comparison | Observed mean diff | SD of paired diff | MDE (80% power) | Detectable now? |")
    L.append("|---|---:|---:|---:|:--:|")
    for i in range(len(models)):
        for j in range(i + 1, len(models)):
            a, b = models[i], models[j]
            av, bv = paired(matrix, a, b)
            diffs = [x - y for x, y in zip(av, bv)]
            obs = mean(diffs); sd = math.sqrt(variance(diffs))
            mde = mde_paired_mean(sd, len(diffs), alpha, power) if sd > 0 else 0.0
            ok = "yes" if abs(obs) >= mde and mde > 0 else "NO"
            L.append(f"| {a} vs {b} | {obs:+.2f} | {sd:.2f} | {mde:.2f} | {ok} |")
    L.append("")
    L.append("> If the observed difference is below the MDE, the design literally cannot call it "
             "significant. At this N you can only detect very large gaps — which is exactly why every "
             "comparison came back non-significant. That is a statement about sample size, not models.")
    L.append("")

    # 2. Required cases for target differences
    L.append("## 2. Cases needed to detect a target difference (80% power)")
    L.append("")
    # use a representative SD (pooled across comparisons) for the mean test
    all_diffs = []
    for i in range(len(models)):
        for j in range(i + 1, len(models)):
            av, bv = paired(matrix, models[i], models[j])
            all_diffs += [x - y for x, y in zip(av, bv)]
    sd_rep = math.sqrt(variance(all_diffs)) if len(all_diffs) > 1 else 1.0
    L.append(f"Representative SD of paired trajectory diff (from this run): {sd_rep:.2f}")
    L.append("")
    L.append("| Target diff | Paired mean test (cases) | Success-rate test 0.80 vs (0.80-Δ), McNemar (cases) |")
    L.append("|---|---:|---:|")
    for td in [0.50, 0.30, 0.20, 0.10, 0.05]:
        n_mean = n_paired_mean(td, sd_rep, alpha, power)
        p_hi = 0.80
        p_lo = max(0.01, p_hi - td)
        n_mc = n_mcnemar(p_hi, p_lo, 0.5, alpha, power)
        L.append(f"| {td:.2f} | {math.ceil(n_mean)} | {math.ceil(n_mc)} |")
    L.append("")
    L.append("> Reading: detecting a ~0.10 (trajectory) or ~10pp (success) gap needs on the order of "
             "100-200 cases, not 15. Detecting 5pp needs many hundreds. This sets the case budget.")
    L.append("")

    # 3. Trials per case
    L.append("## 3. Trials per case needed to measure per-case reliability")
    L.append("")
    L.append("To estimate ONE case's success probability p to +/- margin (95% CI):")
    L.append("")
    L.append("| p (case success) | margin +/-0.20 | margin +/-0.15 | margin +/-0.10 |")
    L.append("|---|---:|---:|---:|")
    for p in [0.5, 0.7, 0.8, 0.9]:
        L.append(f"| {p:.1f} | {math.ceil(trials_for_margin(p,0.20))} | "
                 f"{math.ceil(trials_for_margin(p,0.15))} | {math.ceil(trials_for_margin(p,0.10))} |")
    L.append("")
    L.append("> With **1 trial per case** a case's success is a single 0/1 — its per-case reliability is "
             "unmeasurable. Even a coarse +/-0.20 estimate needs ~25 trials. So trials-per-case is the "
             "lever for *reliability*, not for the headline mean.")
    L.append("")

    # 4. pass^k decay
    L.append("## 4. pass^k reliability decay (all k attempts succeed)")
    L.append("")
    L.append("| per-trial p | pass^1 | pass^2 | pass^3 | pass^5 | pass^8 |")
    L.append("|---|---:|---:|---:|---:|---:|")
    for p in [0.95, 0.90, 0.80, 0.70]:
        L.append(f"| {p:.2f} | {p:.2f} | {p**2:.2f} | {p**3:.2f} | {p**5:.2f} | {p**8:.2f} |")
    L.append("")
    L.append("> tau-bench's point: a 90%-per-trial agent is only 59% reliable over 5 attempts. You cannot "
             "even compute this column with 1 trial per case — it requires K>1.")
    L.append("")

    # 5. fixed-budget tradeoff
    L.append("## 5. Cases vs trials under a fixed call budget (the formal answer)")
    L.append("")
    L.append("Variance of the headline mean across N cases x K trials:")
    L.append("")
    L.append("```")
    L.append("Var(mean)  =  sigma_between^2 / N   +   sigma_within^2 / (N*K)")
    L.append("with fixed total calls C = N*K:")
    L.append("Var(mean)  =  sigma_between^2 / N   +   sigma_within^2 / C")
    L.append("```")
    L.append("")
    L.append("- The **within-case term is fixed by the total budget C** regardless of how you split it. "
             "Only **N** shrinks the **between-case term**, which dominates on a benchmark. ")
    L.append("- => For the **headline mean / model ranking**, spend the budget on **more CASES** (K small).")
    L.append("- => For **reliability (pass^k) and variance-reducing a paired comparison at temperature>0**, "
             "you separately need **K>1 trials per case** (K~5-8). K=1 makes reliability unmeasurable.")
    L.append("- Practical split: pick N from section 2 (power for the comparison you care about), then add "
             "K=5-8 only at temperature>0 to measure reliability and average out per-call noise.")
    L.append("")
    L.append("---")
    L.append("_Methods: paired/McNemar sample-size formulae, binomial precision, pass^k, and the "
             "two-level variance decomposition. See METHODOLOGY_AGENT_EVAL.md for sources. At very small "
             "N even these are optimistic — Bowyer et al. (2025) show CLT/bootstrap intervals under-cover "
             "below a few hundred points; prefer Bayesian intervals there._")
    return "\n".join(L) + "\n"


def parse_args():
    ap = argparse.ArgumentParser(description="Power & sample-size design for the eval.")
    ap.add_argument("--results", required=True)
    ap.add_argument("--target-diff", type=float, default=0.10)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--power", type=float, default=0.8)
    ap.add_argument("--out", default="")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    rows = load(Path(args.results))
    report = build(rows, args.target_diff, None, args.alpha, args.power)
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
