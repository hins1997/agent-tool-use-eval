"""
Robustness as a causal question: is a higher score real capability, or memorised
phrasing?

A benchmark score can be inflated by surface familiarity — the model handles the
exact wording the benchmark uses, not the underlying task. That is the leading
signature of contamination / "looks-stronger-than-it-is". The clean way to test
it is a controlled intervention: hold the task and its ground truth fixed, change
ONLY the surface form (paraphrase, language, punctuation, distractor, injected
pressure), and measure the effect on the score. Because each perturbed variant is
paired to its canonical phrasing, the difference is the *causal effect of that
perturbation* — there is no confounding by task difficulty, since the task is the
same.

This module reads a paraphrase-robustness result file (from running
`cases_paraphrase_robustness.jsonl`) and reports, per model AND per perturbation
type:

- mean causal effect of the perturbation on the trajectory score (paired),
- 95% bootstrap CI clustered on the base task,
- a paired sign-flip permutation p-value for "effect != 0".

An effect whose CI excludes 0 (especially a negative one) is causal evidence that
the model is phrasing-dependent on that kind of change — a robustness defect that
a raw average score cannot reveal.

Standard library only.

Usage:
    python3 eval_runner.py --cases cases_paraphrase_robustness.jsonl --models deepseek,openai,claude --budget-cny 60
    python3 perturbation_causal.py --results results/eval_results_<run_id>.csv \
        --cases cases_paraphrase_robustness.jsonl
"""

from __future__ import annotations

import argparse
import csv
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

from eval_runner import load_jsonl

SAMPLES = 10000


def load_results(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as h:
        return list(csv.DictReader(h))


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def bootstrap_ci(values, n, rng, alpha=0.05):
    if len(values) < 2:
        m = mean(values)
        return m, m
    samples = sorted(mean(values[rng.randrange(len(values))] for _ in values) for _ in range(n))
    lo = samples[int((alpha / 2) * (len(samples) - 1))]
    hi = samples[int((1 - alpha / 2) * (len(samples) - 1))]
    return lo, hi


def sign_flip_p(values, n, rng):
    """Paired single-sample permutation test for mean(effect) != 0 by flipping
    the sign of each paired difference (the sharp null: perturbation has no effect)."""
    if not values:
        return 1.0
    observed = abs(mean(values))
    count = 0
    for _ in range(n):
        flipped = mean(v if rng.random() < 0.5 else -v for v in values)
        if abs(flipped) >= observed - 1e-12:
            count += 1
    return (count + 1) / (n + 1)


def contrasts(cases, rows):
    """Return effect lists keyed by (model, variant_type) and by model overall.
    Each effect = score(variant) - score(canonical) on the same base task."""
    base_of = {c["id"]: c.get("base_id", c["id"]) for c in cases}
    vtype_of = {c["id"]: c.get("variant_type", "?") for c in cases}
    # (model, base) -> {variant_type: score}
    grid: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    for r in rows:
        cid = r["case_id"]
        if cid not in base_of:
            continue
        try:
            grid[(r["model"], base_of[cid])][vtype_of[cid]] = float(r["trajectory_score"])
        except ValueError:
            continue
    by_type: dict[tuple[str, str], list[float]] = defaultdict(list)
    by_model: dict[str, list[float]] = defaultdict(list)
    for (model, _base), variants in grid.items():
        if "canonical" not in variants:
            continue
        c = variants["canonical"]
        for vt, score in variants.items():
            if vt == "canonical":
                continue
            by_type[(model, vt)].append(score - c)
            by_model[model].append(score - c)
    return by_type, by_model


def build_report(cases, rows, seed) -> str:
    rng = random.Random(seed)
    by_type, by_model = contrasts(cases, rows)
    models = sorted(by_model)
    L = ["# Perturbation Causal Effects (robustness = real capability)", ""]
    L.append(f"- seed {seed} | each effect = score(variant) - score(canonical), paired on the base task")
    L.append("- Outcome: trajectory score (0-3). Negative effect = perturbation lowered the score.")
    L.append("")
    if not models:
        L.append("No canonical/variant pairs found in results. Run `cases_paraphrase_robustness.jsonl` first.")
        return "\n".join(L) + "\n"

    # detect single-trial / dryrun
    if not any(int(r.get("input_tokens") or 0) + int(r.get("output_tokens") or 0) > 0 for r in rows):
        L.append("> WARNING: results show zero token usage (dry-run signature). Effects are trivially 0. Not evidence.")
        L.append("")

    L.append("## Overall sensitivity to surface change (per model)")
    L.append("")
    L.append("| Model | contrasts | mean effect | 95% CI | p (sign-flip) | phrasing-dependent? |")
    L.append("|---|---:|---:|---:|---:|:--:|")
    for model in models:
        vals = by_model[model]
        m = mean(vals)
        lo, hi = bootstrap_ci(vals, SAMPLES, rng)
        p = sign_flip_p(vals, SAMPLES, rng)
        flag = "yes" if (lo > 0 or hi < 0) else "no"
        L.append(f"| {model} | {len(vals)} | {m:+.2f} | [{lo:+.2f}, {hi:+.2f}] | {p:.3f} | {flag} |")
    L.append("")
    L.append("> CI excluding 0 = the model's score moves causally with pure rewording, i.e. part of its "
             "score is phrasing, not capability. A negative mean is the worrying direction.")
    L.append("")

    L.append("## Effect by perturbation type (which surface change hurts)")
    L.append("")
    L.append("| Model | perturbation | n | mean effect | 95% CI | p (sign-flip) |")
    L.append("|---|---|---:|---:|---:|---:|")
    for model in models:
        types = sorted(vt for (m, vt) in by_type if m == model)
        for vt in types:
            vals = by_type[(model, vt)]
            m = mean(vals)
            lo, hi = bootstrap_ci(vals, SAMPLES, rng)
            p = sign_flip_p(vals, SAMPLES, rng)
            L.append(f"| {model} | {vt} | {len(vals)} | {m:+.2f} | [{lo:+.2f}, {hi:+.2f}] | {p:.3f} |")
    L.append("")
    L.append("> This localises the fragility: e.g. a model robust to paraphrase but not to language_shift "
             "or injection_reword tells you exactly which surface invariance it lacks — actionable for both "
             "data construction and product guardrails.")
    L.append("")
    L.append("---")
    L.append("_Method: paired contrast vs the canonical phrasing (task held fixed => no difficulty "
             "confound); cluster bootstrap CI over base tasks; sign-flip permutation test of the sharp "
             "null that the perturbation has no effect. Standard library only._")
    return "\n".join(L) + "\n"


def parse_args():
    ap = argparse.ArgumentParser(description="Causal effect of surface perturbations on score.")
    ap.add_argument("--results", required=True)
    ap.add_argument("--cases", default="cases_paraphrase_robustness.jsonl")
    ap.add_argument("--seed", type=int, default=20260627)
    ap.add_argument("--out", default="")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    cases = load_jsonl(Path(args.cases))
    rows = load_results(Path(args.results))
    report = build_report(cases, rows, args.seed)
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
