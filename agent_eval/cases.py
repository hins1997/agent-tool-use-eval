"""Case loading, validation, and selection for Agent behavior benchmarks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_MODULE = "tool_use_reliability"
VALID_MODULES = {"tool_use_reliability", "autonomy_boundary", "agent_planning"}
DEFAULT_AUTONOMY_LAYER = "single_turn"
VALID_AUTONOMY_LAYERS = {"single_turn", "multi_turn", "dynamic"}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    cases = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_no, raw in enumerate(handle, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                cases.append(json.loads(raw))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
    return cases


def case_module(case: dict[str, Any]) -> str:
    return str(case.get("module") or DEFAULT_MODULE)


def autonomy_layer(case: dict[str, Any]) -> str:
    if case_module(case) != "autonomy_boundary":
        return ""
    if case.get("autonomy_layer"):
        return str(case["autonomy_layer"])
    return "multi_turn" if isinstance(case.get("conversation"), list) else DEFAULT_AUTONOMY_LAYER


def validate_cases(cases: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    valid_categories = {
        "normal",
        "boundary",
        "adversarial",
        "long_chain",
        "stateful",
        "agentic_coding",
        "browser_web",
        "search_research",
        "planning",
    }
    valid_boundary_actions = {"act", "clarify", "refuse", "stop", "defer"}
    for index, case in enumerate(cases, 1):
        prefix = f"case #{index}"
        for field in ("id", "category", "prompt", "expected_tool_calls"):
            if field not in case:
                errors.append(f"{prefix}: missing {field}")
        case_id = str(case.get("id", ""))
        if case_id in seen:
            errors.append(f"{prefix}: duplicate id {case_id}")
        seen.add(case_id)
        module = case_module(case)
        if module not in VALID_MODULES:
            errors.append(f"{prefix}: invalid module {module}")
        if module == DEFAULT_MODULE and case.get("category") not in valid_categories:
            errors.append(f"{prefix}: invalid category {case.get('category')}")
        if module == "autonomy_boundary":
            layer = autonomy_layer(case)
            if layer not in VALID_AUTONOMY_LAYERS:
                errors.append(f"{prefix}: invalid autonomy_layer {layer}")
            if layer == "multi_turn":
                conversation = case.get("conversation")
                if not isinstance(conversation, list) or len(conversation) < 2:
                    errors.append(f"{prefix}: multi_turn autonomy case needs 2+ conversation turns")
            if layer == "dynamic":
                simulator = case.get("simulator")
                if not isinstance(simulator, dict):
                    errors.append(f"{prefix}: dynamic autonomy case needs simulator object")
                elif not str(simulator.get("initial_user", "")).strip():
                    errors.append(f"{prefix}: dynamic simulator needs initial_user")
            if not str(case.get("boundary_action", "")).strip():
                errors.append(f"{prefix}: autonomy_boundary case missing boundary_action")
            elif case.get("boundary_action") not in valid_boundary_actions:
                errors.append(
                    f"{prefix}: invalid boundary_action {case.get('boundary_action')}"
                )
            turn_expectations = case.get("turn_expectations", [])
            if turn_expectations and not isinstance(turn_expectations, list):
                errors.append(f"{prefix}: turn_expectations must be a list")
        if module == "agent_planning":
            if case.get("category") != "planning":
                errors.append(f"{prefix}: agent_planning case category must be planning")
            plan_expectations = case.get("plan_expectations")
            if not isinstance(plan_expectations, dict):
                errors.append(f"{prefix}: agent_planning case needs plan_expectations object")
            else:
                ordered_steps = plan_expectations.get("ordered_steps", [])
                if not isinstance(ordered_steps, list) or not ordered_steps:
                    errors.append(f"{prefix}: plan_expectations.ordered_steps must be a non-empty list")
        if not isinstance(case.get("expected_tool_calls", []), list):
            errors.append(f"{prefix}: expected_tool_calls must be a list")
        for field in ("expected_final_state", "forbidden_final_state", "initial_state"):
            if field in case and not isinstance(case.get(field), dict):
                errors.append(f"{prefix}: {field} must be an object")
    return errors


def select_cases(
    cases: list[dict[str, Any]],
    case_ids: str,
    limit: int,
    modules: str = "",
) -> list[dict[str, Any]]:
    if case_ids:
        wanted = [item.strip() for item in case_ids.split(",") if item.strip()]
        by_id = {case["id"]: case for case in cases}
        missing = [case_id for case_id in wanted if case_id not in by_id]
        if missing:
            raise ValueError(f"Unknown case IDs: {', '.join(missing)}")
        cases = [by_id[case_id] for case_id in wanted]
    if modules:
        wanted_modules = {item.strip() for item in modules.split(",") if item.strip()}
        unknown_modules = wanted_modules - VALID_MODULES
        if unknown_modules:
            raise ValueError(f"Unknown modules: {', '.join(sorted(unknown_modules))}")
        cases = [case for case in cases if case_module(case) in wanted_modules]
    if limit:
        cases = cases[:limit]
    return cases

