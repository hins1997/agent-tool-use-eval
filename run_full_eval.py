"""
One-command orchestrator for a full real evaluation pass.

Run this on the machine where your API keys are set (e.g. your PowerShell
session). It executes every case suite through the selected models, runs the
LLM judge on each trace, then runs the statistical, causal, and robustness
analyses, and writes a consolidated index so you have all real outputs in one
place.

It shells out to the existing scripts (no logic duplication) and stops cleanly
on missing keys or budget. Nothing here calls a model directly; eval_runner and
llm_judge do, using your environment keys.

Example (PowerShell, keys already set):
    python run_full_eval.py --models deepseek,qwen,claude --judge openai --budget-cny 200 --concurrency 6

Smoke test first (cheap, a few cases):
    python run_full_eval.py --models deepseek,qwen,claude --judge openai --smoke --concurrency 6
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable or "python3"

# (label, cases file, is_robustness_suite)
SUITES = [
    ("tool_use_reliability", "cases_all40.jsonl", False),
    ("agent_planning", "cases_agent_planning.jsonl", False),
    ("search_deep_research", "cases_search_research.jsonl", False),
    ("autonomy_boundary", "cases_autonomy_boundary.jsonl", False),
    ("autonomy_multiturn", "cases_autonomy_multiturn.jsonl", False),
    ("dynamic_user_simulation", "cases_dynamic_autonomy.jsonl", False),
    ("permission_boundary", "cases_permission_boundary.jsonl", False),
    ("stateful_tool_sandbox", "cases_stateful_tools.jsonl", False),
    ("agentic_coding", "cases_agentic_coding.jsonl", False),
    ("browser_web", "cases_browser_web.jsonl", False),
    ("multiturn", "cases_multiturn.jsonl", False),
    ("paraphrase_robustness", "cases_paraphrase_robustness.jsonl", True),
]
SMOKE_IDS = {
    "cases_all40.jsonl": "N01,B03,A03,L01",
    "cases_agent_planning.jsonl": "PL01,PL03,PL05",
    "cases_search_research.jsonl": "SR01,SR03,SR05",
    "cases_autonomy_boundary.jsonl": "AB01,AB04,AB11",
    "cases_autonomy_multiturn.jsonl": "ABM01,ABM03,ABM05",
    "cases_dynamic_autonomy.jsonl": "DS01,DS02,DS04",
    "cases_permission_boundary.jsonl": "PB01,PB05,PB11",
    "cases_stateful_tools.jsonl": "ST01,ST03,ST06",
    "cases_agentic_coding.jsonl": "AC01,AC02",
    "cases_browser_web.jsonl": "BW01,BW03",
    "cases_multiturn.jsonl": "MT01,MT02",
    "cases_paraphrase_robustness.jsonl": "R01a,R01b,R01c,R06a,R06c",
}


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    print("\n$ " + " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def find_path(stdout: str, label: str) -> str:
    m = re.search(rf"{label}:\s*(\S+)", stdout)
    return m.group(1) if m else ""


def judge_aliases(primary: str, cross: str) -> str:
    aliases = []
    for item in [primary, *cross.split(",")]:
        alias = item.strip()
        if alias and alias not in aliases:
            aliases.append(alias)
    return ",".join(aliases)


def filter_judge_csv(judge_csv: Path, alias: str, out_csv: Path) -> int:
    import csv

    with judge_csv.open("r", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    filtered = [row for row in rows if row.get("judge_alias") == alias]
    if not filtered:
        return 0
    with out_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(filtered[0].keys()))
        writer.writeheader()
        writer.writerows(filtered)
    return len(filtered)


def eval_suite(
    cases: str,
    models: str,
    budget: str,
    smoke: bool,
    trials: str,
    temperature: str,
    concurrency: str,
) -> dict:
    cmd = [PY, "eval_runner.py", "--cases", cases, "--models", models, "--budget-cny", budget,
           "--trials", trials, "--temperature", temperature, "--concurrency", concurrency]
    if smoke and cases in SMOKE_IDS:
        cmd += ["--case-ids", SMOKE_IDS[cases]]
    proc = run(cmd)
    print(proc.stdout[-800:] if proc.stdout else "", flush=True)
    if proc.returncode not in (0, 3):  # 3 = budget reached, still wrote outputs
        print(proc.stderr, file=sys.stderr)
        return {"ok": False, "stderr": proc.stderr}
    return {
        "ok": True,
        "results": find_path(proc.stdout, "Results"),
        "traces": find_path(proc.stdout, "Traces"),
        "review": find_path(proc.stdout, "Human review"),
        "budget_stop": proc.returncode == 3,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Full real evaluation pass orchestrator.")
    ap.add_argument("--models", default="deepseek,qwen,claude")
    ap.add_argument("--judge", default="openai", help="formal primary judge model alias for llm_judge")
    ap.add_argument("--cross-judges", default="claude,deepseek", help="comma-separated cross/audit judge aliases")
    ap.add_argument("--budget-cny", default="200")
    ap.add_argument("--smoke", action="store_true", help="run a few case IDs per suite only")
    ap.add_argument("--skip-judge", action="store_true")
    ap.add_argument("--trials", default="1", help="trials per (case, model); >1 with --temperature enables reliability/pass^k")
    ap.add_argument("--temperature", default="0.0", help="sampling temperature; use >0 with --trials>1")
    ap.add_argument(
        "--concurrency",
        default="3",
        help="parallel workers passed to eval_runner.py. Use 3 for conservative runs, 6-9 for faster smoke runs if provider rate limits allow.",
    )
    args = ap.parse_args()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "results" / f"full_run_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    all_judges = judge_aliases(args.judge, args.cross_judges)
    index = [f"# Full evaluation run {stamp}", "",
             f"- Models: {args.models} | Primary judge: {args.judge} | Cross judges: {args.cross_judges} | Smoke: {args.smoke} | "
             f"Trials: {args.trials} | Temperature: {args.temperature} | Concurrency: {args.concurrency}", ""]

    main_results = ""
    para_results = ""
    for label, cases, is_robust in SUITES:
        print(f"\n=== SUITE: {label} ({cases}) ===", flush=True)
        res = eval_suite(
            cases,
            args.models,
            args.budget_cny,
            args.smoke,
            args.trials,
            args.temperature,
            args.concurrency,
        )
        if not res["ok"]:
            index.append(f"## {label}: FAILED\n\n```\n{res.get('stderr','')[-500:]}\n```\n")
            continue
        index.append(f"## {label}")
        index.append(f"- results: `{res['results']}`")
        index.append(f"- traces: `{res['traces']}`")
        index.append(f"- human review worksheet (fill for result/reasoning scores): `{res['review']}`")
        if res.get("budget_stop"):
            index.append("- NOTE: budget reached; suite partially run.")
        if label == "tool_use_reliability":
            main_results = res["results"]
        if is_robust:
            para_results = res["results"]

        # LLM judge on this suite's traces (real judge model).
        if not args.skip_judge and res["traces"]:
            judge_out = out_dir / f"judge_{label}_multi.csv"
            jp = run([PY, "llm_judge.py", "score", "--traces", res["traces"],
                      "--judge", all_judges, "--out", str(judge_out)])
            print(jp.stdout[-300:] if jp.stdout else jp.stderr[-300:], flush=True)
            if jp.returncode == 0:
                primary_out = out_dir / f"judge_{label}_primary_{args.judge}.csv"
                primary_count = filter_judge_csv(judge_out, args.judge, primary_out)
                index.append(f"- LLM-judge multi scores: `{judge_out}`")
                if primary_count:
                    index.append(f"- Formal primary judge scores ({args.judge}, {primary_count} rows): `{primary_out}`")
                compare_out = out_dir / f"judge_vs_rule_{label}.md"
                jc = run([PY, "llm_judge.py", "compare", "--results", res["results"],
                          "--judge-csv", str(primary_out if primary_count else judge_out), "--review", res["review"],
                          "--out", str(compare_out)])
                if jc.returncode == 0:
                    index.append(f"- Primary judge-vs-rule calibration: `{compare_out}`")
                bias_out = out_dir / f"judge_bias_{label}.md"
                jb = run([PY, "llm_judge.py", "bias", "--judge-csv", str(judge_out),
                          "--out", str(bias_out)])
                if jb.returncode == 0:
                    index.append(f"- Judge-family bias audit: `{bias_out}`")
                # Judge vs human agreement (only meaningful once review is filled).
                ja = run([PY, "llm_judge.py", "agreement", "--judge-csv", str(primary_out if primary_count else judge_out),
                          "--review", res["review"]])
                (out_dir / f"judge_agreement_{label}.md").write_text(
                    (ja.stdout or "") + (ja.stderr or ""), encoding="utf-8")
        index.append("")

    # Statistical + causal analyses on the main suite.
    if main_results:
        for script, name in [("stats.py", "statistics"), ("causal_eval.py", "causal")]:
            out_md = out_dir / f"{name}.md"
            cmd = [PY, script, "--results", main_results, "--out", str(out_md)]
            if name == "causal" and para_results:
                cmd += ["--robustness-results", para_results]
            sp = run(cmd)
            print(sp.stdout[-200:] if sp.stdout else sp.stderr[-300:], flush=True)
            if sp.returncode == 0:
                index.append(f"## {name}\n- `{out_md}`\n")

    # Reliability / pass^k (only meaningful with trials > 1).
    if main_results and int(args.trials) > 1:
        rel_md = out_dir / "reliability.md"
        rp = run([PY, "reliability.py", "--results", main_results, "--out", str(rel_md)])
        print(rp.stdout[-200:] if rp.stdout else rp.stderr[-300:], flush=True)
        if rp.returncode == 0:
            index.append(f"## reliability (pass^k)\n- `{rel_md}`\n")
    elif main_results:
        index.append("## reliability (pass^k)\n- skipped: needs --trials > 1 with --temperature > 0\n")

    # Robustness drift + perturbation causal effects.
    if para_results:
        rob_md = out_dir / "robustness.md"
        rp = run([PY, "robustness.py", "--cases", "cases_paraphrase_robustness.jsonl",
                  "--results", para_results, "--out", str(rob_md)])
        if rp.returncode == 0:
            index.append(f"## robustness drift\n- `{rob_md}`\n")
        pc_md = out_dir / "perturbation_causal.md"
        pc = run([PY, "perturbation_causal.py", "--cases", "cases_paraphrase_robustness.jsonl",
                  "--results", para_results, "--out", str(pc_md)])
        print(pc.stdout[-200:] if pc.stdout else pc.stderr[-300:], flush=True)
        if pc.returncode == 0:
            index.append(f"## perturbation causal effects\n- `{pc_md}`\n")

    index_path = out_dir / "INDEX.md"
    index_path.write_text("\n".join(index) + "\n", encoding="utf-8")
    print(f"\nDONE. Consolidated index: {index_path}")
    print("Next: fill the human_review_*.csv worksheets, then re-run stats.py with --review "
          "and llm_judge.py agreement to get human-validated numbers.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
