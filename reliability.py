"""
Reliability evaluation: what a single-shot pass-rate cannot see.

Traditional eval reports one number per task: did it pass? But an agent that
passes a task once is not the same as one that passes it every time. tau-bench
(Yao et al., 2024) showed a 90%-per-attempt agent is only ~59% reliable over 5
attempts. Reliability is a capability dimension that a single trial per case
literally cannot measure.

This module runs on a *multi-trial* result file (eval_runner.py --trials K
--temperature >0) and reports:

1. pass^k  : probability the agent succeeds on ALL k independent attempts
             (worst-case reliability; decays as the per-case success prob ^k).
2. pass@k  : probability of AT LEAST one success in k attempts.
3. per-case success probability with a **hierarchical Beta-Binomial** posterior.
   The hierarchy is the point: with small K, a raw 3/5 is a noisy estimate, so
   we partially pool each case toward the model's global behaviour via an
   empirical-Bayes Beta prior. This is exactly the statistical move that lets us
   say something trustworthy per case when traditional eval only had a 0/1.
4. reliability profile: how many cases are stably-passing, stably-failing, or
   FLAKY (the dangerous middle), and the worst-case (low-percentile) reliability.

Standard library only (uses random.betavariate for posterior sampling).

Usage:
    python3 eval_runner.py --cases cases_all40.jsonl --models deepseek,openai,claude \
        --trials 8 --temperature 0.7 --budget-cny 200
    python3 reliability.py --results results/eval_results_<run_id>.csv
"""

from __future__ import annotations

import argparse
import csv
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

FULL = 3
FLAKY_LOW, FLAKY_HIGH = 0.2, 0.8
SAMPLES = 4000


def load(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as h:
        return list(csv.DictReader(h))


def aggregate(rows: list[dict[str, Any]], threshold: int):
    """(model, case_id) -> (trials, successes)."""
    agg: dict[tuple[str, str], list[int]] = defaultdict(list)
    for r in rows:
        try:
            score = int(r["trajectory_score"])
        except (KeyError, ValueError):
            continue
        agg[(r["model"], r["case_id"])].append(1 if score >= threshold else 0)
    return agg


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


# --------------------------------------------------------------------------- #
# Empirical-Bayes Beta prior (partial pooling)
# --------------------------------------------------------------------------- #
def empirical_bayes_prior(successes: list[int], trials: list[int]) -> tuple[float, float]:
    """Estimate a Beta(a0,b0) prior from the across-case success rates by moment
    matching, subtracting binomial sampling noise to recover the BETWEEN-case
    variance. Falls back to strong pooling when cases are indistinguishable."""
    rates = [s / k for s, k in zip(successes, trials) if k > 0]
    if len(rates) < 2:
        return 1.0, 1.0
    m = mean(rates)
    if m <= 0 or m >= 1:
        # all-pass or all-fail: weak prior, let data dominate
        return (0.5, 0.5)
    total_var = mean([(r - m) ** 2 for r in rates])
    within = mean([r * (1 - r) / k for r, k in zip(rates, trials) if k > 0])
    between = total_var - within
    if between <= 1e-6:
        # No real case-to-case differences beyond sampling noise -> strong pooling.
        kappa = 200.0
    else:
        kappa = max(1.0, m * (1 - m) / between - 1.0)
        kappa = min(kappa, 500.0)  # cap to avoid degenerate over-pooling
    return m * kappa, (1 - m) * kappa


def posterior_mean(s: int, k: int, a0: float, b0: float) -> float:
    return (a0 + s) / (a0 + b0 + k)


def posterior_samples(s: int, k: int, a0: float, b0: float, n: int, rng: random.Random):
    a, b = a0 + s, b0 + (k - s)
    return [rng.betavariate(a, b) for _ in range(n)]


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
def build_report(rows: list[dict[str, Any]], threshold: int, kmax_cap: int, seed: int) -> str:
    rng = random.Random(seed)
    agg = aggregate(rows, threshold)
    models = sorted({m for m, _ in agg})
    L = ["# Reliability (pass^k) Analysis", ""]
    L.append(f"- Success = trajectory score >= {threshold} | seed {seed}")
    L.append("")

    # Detect single-trial data.
    trials_per_cell = [len(v) for v in agg.values()]
    min_k = min(trials_per_cell) if trials_per_cell else 0
    max_k = max(trials_per_cell) if trials_per_cell else 0
    if max_k <= 1:
        L.append("> WARNING: this result file has 1 trial per (case, model). Reliability is "
                 "**unmeasurable** from single-shot data — pass^k collapses to 0/1. Re-run with "
                 "`eval_runner.py --trials 8 --temperature 0.7` and analyse that file.")
        L.append("")
        return "\n".join(L) + "\n"

    L.append(f"- Trials per (case, model): min {min_k}, max {max_k}")
    L.append("")

    # Per-model reliability table.
    L.append("## Per-trial success vs multi-attempt reliability")
    L.append("")
    L.append("| Model | cases | trials/case | mean per-case p | pass^1 | pass^2 | pass^3 | pass^5 | worst-case p (10th pct) |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    profile: dict[str, dict[str, float]] = {}
    flaky_lists: dict[str, list[tuple[str, float, int, int]]] = {}
    for model in models:
        cells = [(c, sum(v), len(v)) for (m, c), v in agg.items() if m == model]
        a0, b0 = empirical_bayes_prior([s for _, s, _ in cells], [k for _, _, k in cells])
        p_hats = []
        flaky = []
        for case, s, k in cells:
            p = posterior_mean(s, k, a0, b0)
            p_hats.append(p)
            flaky.append((case, p, s, k))
        flaky_lists[model] = flaky
        kcase = min(k for _, _, k in cells)

        def passk(kk):
            return mean([p ** kk for p in p_hats])

        # worst-case: 10th percentile of per-case posterior means
        sp = sorted(p_hats)
        worst = sp[max(0, int(0.10 * (len(sp) - 1)))]
        profile[model] = {
            "mean_p": mean(p_hats),
            "stable_pass": mean([1.0 if p >= FLAKY_HIGH else 0.0 for p in p_hats]),
            "flaky": mean([1.0 if FLAKY_LOW < p < FLAKY_HIGH else 0.0 for p in p_hats]),
            "stable_fail": mean([1.0 if p <= FLAKY_LOW else 0.0 for p in p_hats]),
            "a0": a0, "b0": b0,
        }
        p5 = passk(5) if kcase >= 5 else float("nan")
        p5s = f"{p5:.2f}" if p5 == p5 else "n/a(K<5)"
        L.append(
            f"| {model} | {len(cells)} | {kcase} | {mean(p_hats):.2f} | {passk(1):.2f} | "
            f"{passk(2):.2f} | {passk(3):.2f} | {p5s} | {worst:.2f} |"
        )
    L.append("")
    L.append("> pass^1 is the ordinary success rate. The drop from pass^1 to pass^3/pass^5 is the "
             "reliability tax that single-shot eval hides. worst-case p surfaces the least reliable "
             "cases, not the average.")
    L.append("")

    # Reliability profile.
    L.append("## Reliability profile (share of cases)")
    L.append("")
    L.append("| Model | stably-pass (p>=0.8) | FLAKY (0.2<p<0.8) | stably-fail (p<=0.2) |")
    L.append("|---|---:|---:|---:|")
    for model in models:
        pr = profile[model]
        L.append(f"| {model} | {pr['stable_pass']:.0%} | {pr['flaky']:.0%} | {pr['stable_fail']:.0%} |")
    L.append("")
    L.append("> Flaky cases are the operational risk a mean score erases: the agent sometimes does the "
             "task and sometimes doesn't. These are the cases to harden, and they only appear with K>1.")
    L.append("")

    # Most flaky cases per model.
    L.append("## Most flaky cases (per-case success closest to 50%)")
    L.append("")
    for model in models:
        ranked = sorted(flaky_lists[model], key=lambda t: abs(t[1] - 0.5))
        top = [t for t in ranked if FLAKY_LOW < t[1] < FLAKY_HIGH][:5]
        if not top:
            L.append(f"- **{model}**: no flaky cases (all stably pass or fail).")
            continue
        detail = ", ".join(f"{c}(p≈{p:.2f}, {s}/{k})" for c, p, s, k in top)
        L.append(f"- **{model}**: {detail}")
    L.append("")
    L.append("---")
    L.append("_Method: per-case success modelled as Beta-Binomial with an empirical-Bayes Beta prior "
             "(partial pooling), so small-K per-case estimates borrow strength from the model's global "
             "behaviour. pass^k uses posterior-mean per-case probabilities. Standard library only._")
    return "\n".join(L) + "\n"


def parse_args():
    ap = argparse.ArgumentParser(description="Reliability / pass^k analysis from multi-trial results.")
    ap.add_argument("--results", required=True)
    ap.add_argument("--threshold", type=int, default=FULL, help="trajectory score counted as success")
    ap.add_argument("--kmax", type=int, default=8)
    ap.add_argument("--seed", type=int, default=20260627)
    ap.add_argument("--out", default="")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    rows = load(Path(args.results))
    report = build_report(rows, args.threshold, args.kmax, args.seed)
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
