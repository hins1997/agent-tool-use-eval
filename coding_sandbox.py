#!/usr/bin/env python3
"""Execution-based verifier for agentic coding traces.

The main eval runner uses mock tools so paid model runs stay deterministic and
side-effect free. This script adds a second verification layer for coding cases:
materialize the mock repo state into a temporary directory and actually execute
the target tests listed in the case.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import eval_runner as er


MINI_PYTEST = '''
class raises:
    def __init__(self, expected):
        self.expected = expected
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            raise AssertionError(f"expected {self.expected.__name__} to be raised")
        if not issubclass(exc_type, self.expected):
            return False
        return True
'''


TEST_RUNNER = r'''
import importlib.util
import pathlib
import sys
import traceback

root = pathlib.Path(sys.argv[1])
target = root / sys.argv[2]
sys.path.insert(0, str(root))
spec = importlib.util.spec_from_file_location("sandbox_tests", target)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
failures = []
ran = 0
for name in sorted(dir(module)):
    if not name.startswith("test_"):
        continue
    fn = getattr(module, name)
    if not callable(fn):
        continue
    ran += 1
    try:
        fn()
    except Exception:
        failures.append((name, traceback.format_exc()))
if failures:
    for name, tb in failures:
        print(f"FAILED {name}")
        print(tb)
    sys.exit(1)
print(f"passed {ran} tests")
'''


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify agentic coding traces by executing tests")
    parser.add_argument("--traces", required=True, help="traces_<run>.jsonl")
    parser.add_argument("--out", default="", help="optional CSV output")
    parser.add_argument("--report", default="", help="optional markdown report")
    return parser.parse_args()


def safe_write(root: Path, filename: str, content: str) -> None:
    target = (root / filename).resolve()
    if not str(target).startswith(str(root.resolve())):
        raise ValueError(f"unsafe path outside sandbox: {filename}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def materialize_repo(case: dict[str, Any], output: dict[str, Any], root: Path) -> None:
    state = er.initial_state(case)
    final_state = output.get("final_state")
    if final_state is None:
        final_state = er.final_state_from_calls(case, output.get("tool_calls", []))
    if isinstance(final_state.get("files"), dict):
        state["files"].update(final_state["files"])
    for filename, value in state["files"].items():
        content = value.get("content", "") if isinstance(value, dict) else str(value)
        safe_write(root, str(filename), str(content))
    safe_write(root, "pytest.py", MINI_PYTEST)
    safe_write(root, "_sandbox_runner.py", TEST_RUNNER)


def expected_test_targets(case: dict[str, Any]) -> list[tuple[str, str]]:
    targets = []
    for call in case.get("expected_tool_calls", []):
        if call.get("tool") != "run_tests":
            continue
        params = call.get("params", {})
        targets.append((str(params.get("suite", "")), str(params.get("target", ""))))
    return targets


def verify_trace(trace: dict[str, Any], timeout: int = 10) -> dict[str, Any]:
    case = trace.get("case", {})
    output = trace.get("output", {})
    case_id = case.get("id", "")
    model = trace.get("model", "")
    if case.get("category") != "agentic_coding":
        return {
            "case_id": case_id,
            "model": model,
            "status": "skipped",
            "suite": "",
            "target": "",
            "passed": "",
            "notes": "not an agentic_coding case",
        }
    targets = expected_test_targets(case)
    if not targets:
        return {
            "case_id": case_id,
            "model": model,
            "status": "failed",
            "suite": "",
            "target": "",
            "passed": "false",
            "notes": "no expected run_tests target",
        }
    rows = []
    with tempfile.TemporaryDirectory(prefix=f"agent_eval_{case_id}_") as temp_dir:
        root = Path(temp_dir)
        materialize_repo(case, output, root)
        for suite, target in targets:
            if not target:
                rows.append(
                    {
                        "case_id": case_id,
                        "model": model,
                        "status": "failed",
                        "suite": suite,
                        "target": target,
                        "passed": "false",
                        "notes": "empty test target",
                    }
                )
                continue
            completed = subprocess.run(
                [sys.executable, "_sandbox_runner.py", str(root), target],
                cwd=root,
                text=True,
                capture_output=True,
                timeout=timeout,
            )
            rows.append(
                {
                    "case_id": case_id,
                    "model": model,
                    "status": "passed" if completed.returncode == 0 else "failed",
                    "suite": suite,
                    "target": target,
                    "passed": str(completed.returncode == 0).lower(),
                    "notes": (completed.stdout + completed.stderr).strip()[:1000],
                }
            )
    if len(rows) == 1:
        return rows[0]
    failed = [row for row in rows if row["status"] != "passed"]
    return {
        "case_id": case_id,
        "model": model,
        "status": "failed" if failed else "passed",
        "suite": ",".join(row["suite"] for row in rows),
        "target": ",".join(row["target"] for row in rows),
        "passed": str(not failed).lower(),
        "notes": " | ".join(row["notes"] for row in rows)[:1000],
    }


def build_report(rows: list[dict[str, Any]], traces_path: str) -> str:
    checked = [row for row in rows if row["status"] != "skipped"]
    passed = [row for row in checked if row["status"] == "passed"]
    failed = [row for row in checked if row["status"] == "failed"]
    lines = [
        "# Coding Sandbox Verification",
        "",
        f"- Traces: `{traces_path}`",
        f"- Coding rows checked: {len(checked)}",
        f"- Passed: {len(passed)}",
        f"- Failed: {len(failed)}",
        "",
        "| Case | Model | Suite | Target | Status | Notes |",
        "|---|---|---|---|---|---|",
    ]
    for row in checked:
        lines.append(
            f"| {md(row['case_id'])} | {md(row['model'])} | {md(row['suite'])} | "
            f"{md(row['target'])} | {md(row['status'])} | {md(row['notes'])} |"
        )
    return "\n".join(lines) + "\n"


def md(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")[:240]


def main() -> int:
    args = parse_args()
    traces = er.load_jsonl(Path(args.traces))
    rows = [verify_trace(trace) for trace in traces]
    out_path = Path(args.out) if args.out else Path(args.traces).with_name("coding_sandbox_verification.csv")
    fields = ["case_id", "model", "status", "suite", "target", "passed", "notes"]
    with out_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Coding sandbox CSV: {out_path}")
    report = build_report(rows, args.traces)
    if args.report:
        Path(args.report).write_text(report, encoding="utf-8")
        print(f"Coding sandbox report: {args.report}")
    return 0 if all(row["status"] != "failed" for row in rows if row["status"] != "skipped") else 1


if __name__ == "__main__":
    raise SystemExit(main())
