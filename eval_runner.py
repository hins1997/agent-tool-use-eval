"""
Agent tool-use reliability evaluator.

The runner uses only the Python standard library. It supports:
- JSONL cases
- OpenAI-compatible APIs (DeepSeek, Qwen, OpenAI)
- Anthropic Messages API
- deterministic local dry-run
- full tool traces, automatic trajectory scoring, human-review CSV
- token-based cost estimates when prices are configured
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import operator
import os
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_CASES = ROOT / "cases_first15.jsonl"
DEFAULT_PRICING = ROOT / "model_prices.json"
TODAY = date.today().isoformat()

MODEL_CONFIGS = {
    "deepseek": {
        "provider": "openai_compatible",
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com/chat/completions",
    },
    "qwen": {
        "provider": "openai_compatible",
        "model": os.getenv("QWEN_MODEL", "qwen3.5-plus"),
        "api_key_env": "DASHSCOPE_API_KEY",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "extra_body": {"enable_thinking": False},
    },
    "claude": {
        "provider": "anthropic",
        "model": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        "api_key_env": "ANTHROPIC_API_KEY",
        "base_url": "https://api.anthropic.com/v1/messages",
    },
    "openai": {
        "provider": "openai_compatible",
        "model": os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        "api_key_env": "OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1/chat/completions",
    },
}

TOOLS = [
    {
        "name": "get_weather",
        "description": "Get weather for a city and date. Use this for current or date-specific weather instead of guessing.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name"},
                "date": {"type": "string", "description": "YYYY-MM-DD; defaults to today"},
            },
            "required": ["location"],
            "additionalProperties": False,
        },
    },
    {
        "name": "calculate",
        "description": "Evaluate an arithmetic expression.",
        "parameters": {
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
            "additionalProperties": False,
        },
    },
    {
        "name": "web_search",
        "description": "Search the web for fresh external information.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "send_email",
        "description": "Send an email. All required fields must be known; never invent an address.",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["to", "subject", "body"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_calendar",
        "description": "Get calendar events for a date.",
        "parameters": {
            "type": "object",
            "properties": {"date": {"type": "string", "description": "YYYY-MM-DD"}},
            "required": ["date"],
            "additionalProperties": False,
        },
    },
    {
        "name": "create_event",
        "description": "Create a calendar event after checking availability when the user requests a free slot.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "date": {"type": "string"},
                "start_time": {"type": "string"},
                "duration_minutes": {"type": "integer"},
                "location": {"type": "string"},
            },
            "required": ["title", "date", "start_time", "duration_minutes"],
            "additionalProperties": False,
        },
    },
    {
        "name": "translate",
        "description": "Translate text into a target language.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "target_language": {"type": "string"},
            },
            "required": ["text", "target_language"],
            "additionalProperties": False,
        },
    },
    {
        "name": "read_file",
        "description": "Read a text file.",
        "parameters": {
            "type": "object",
            "properties": {"filename": {"type": "string"}},
            "required": ["filename"],
            "additionalProperties": False,
        },
    },
    {
        "name": "write_file",
        "description": "Write or append text to a file in the mock environment.",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string"},
                "content": {"type": "string"},
                "mode": {"type": "string", "enum": ["w", "a"]},
            },
            "required": ["filename", "content"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_contact",
        "description": "Look up contact details. An empty list means no contact was found.",
        "parameters": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
            "additionalProperties": False,
        },
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate LLM tool-use reliability")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--models", default="deepseek,qwen,claude")
    parser.add_argument("--case-ids", default="", help="Comma-separated case IDs")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results")
    parser.add_argument("--pricing", type=Path, default=DEFAULT_PRICING)
    parser.add_argument("--budget-cny", type=float, default=250.0)
    parser.add_argument("--usd-cny", type=float, default=7.25)
    parser.add_argument("--max-turns", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--sleep", type=float, default=0.5)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--validate", action="store_true")
    return parser.parse_args()


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


def validate_cases(cases: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    valid_categories = {"normal", "boundary", "adversarial", "long_chain"}
    for index, case in enumerate(cases, 1):
        prefix = f"case #{index}"
        for field in ("id", "category", "prompt", "expected_tool_calls"):
            if field not in case:
                errors.append(f"{prefix}: missing {field}")
        case_id = str(case.get("id", ""))
        if case_id in seen:
            errors.append(f"{prefix}: duplicate id {case_id}")
        seen.add(case_id)
        if case.get("category") not in valid_categories:
            errors.append(f"{prefix}: invalid category {case.get('category')}")
        if not isinstance(case.get("expected_tool_calls", []), list):
            errors.append(f"{prefix}: expected_tool_calls must be a list")
    return errors


def select_cases(cases: list[dict[str, Any]], case_ids: str, limit: int) -> list[dict[str, Any]]:
    if case_ids:
        wanted = [item.strip() for item in case_ids.split(",") if item.strip()]
        by_id = {case["id"]: case for case in cases}
        missing = [case_id for case_id in wanted if case_id not in by_id]
        if missing:
            raise ValueError(f"Unknown case IDs: {', '.join(missing)}")
        cases = [by_id[case_id] for case_id in wanted]
    if limit > 0:
        cases = cases[:limit]
    return cases


_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def safe_calculate(expression: str) -> float | int:
    def evaluate(node: ast.AST) -> float | int:
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
            return _BIN_OPS[type(node.op)](evaluate(node.left), evaluate(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
            return _UNARY_OPS[type(node.op)](evaluate(node.operand))
        raise ValueError("unsupported expression")

    return evaluate(ast.parse(expression, mode="eval"))


def execute_tool(name: str, params: dict[str, Any], today: str) -> str:
    if name == "get_weather":
        return json.dumps(
            {
                "location": params.get("location"),
                "date": params.get("date", today),
                "temperature_c": 22,
                "condition": "sunny",
                "humidity": 45,
            },
            ensure_ascii=False,
        )
    if name == "calculate":
        try:
            return json.dumps({"result": safe_calculate(str(params.get("expression", "")))})
        except Exception as exc:
            return json.dumps({"error": str(exc)}, ensure_ascii=False)
    if name == "web_search":
        query = str(params.get("query", ""))
        count = int(params.get("max_results", 3))
        results = [
            {
                "title": f"{query} - result {i}",
                "snippet": f"Mock search evidence {i} for {query}",
                "url": f"https://example.com/{i}",
            }
            for i in range(1, min(count, 10) + 1)
        ]
        return json.dumps(results, ensure_ascii=False)
    if name == "send_email":
        return json.dumps(
            {
                "status": "success",
                "to": params.get("to"),
                "subject": params.get("subject"),
            },
            ensure_ascii=False,
        )
    if name == "get_calendar":
        return json.dumps(
            [
                {"title": "Team sync", "start": "14:00", "end": "15:00"},
                {"title": "Review", "start": "16:30", "end": "17:30"},
            ],
            ensure_ascii=False,
        )
    if name == "create_event":
        return json.dumps({"status": "success", "event": params}, ensure_ascii=False)
    if name == "translate":
        return json.dumps(
            {
                "target_language": params.get("target_language"),
                "translated_text": f"[translated] {params.get('text', '')}",
            },
            ensure_ascii=False,
        )
    if name == "read_file":
        filename = str(params.get("filename", ""))
        if filename == "quarterly_report.txt":
            return json.dumps({"error": "file_not_found", "filename": filename})
        return json.dumps(
            {"filename": filename, "content": f"Mock content from {filename}"},
            ensure_ascii=False,
        )
    if name == "write_file":
        return json.dumps(
            {
                "status": "success",
                "filename": params.get("filename"),
                "mode": params.get("mode", "w"),
                "bytes_written": len(str(params.get("content", "")).encode("utf-8")),
            },
            ensure_ascii=False,
        )
    if name == "get_contact":
        name_value = str(params.get("name", ""))
        if name_value in {"赵六", "项目负责人"}:
            return "[]"
        return json.dumps(
            [{"name": name_value, "email": contact_email(name_value)}],
            ensure_ascii=False,
        )
    return json.dumps({"error": "unknown_tool", "tool": name}, ensure_ascii=False)


def post_json(
    url: str,
    body: dict[str, Any],
    headers: dict[str, str],
    timeout: int,
    retries: int,
) -> dict[str, Any]:
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            if exc.code < 500 and exc.code != 429:
                raise RuntimeError(f"HTTP {exc.code}: {details[:800]}") from exc
            last_error = f"HTTP {exc.code}: {details[:800]}"
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = str(exc)
        if attempt < retries:
            time.sleep(2**attempt)
    raise RuntimeError(last_error)


def openai_tools() -> list[dict[str, Any]]:
    return [{"type": "function", "function": tool} for tool in TOOLS]


def run_openai_compatible(
    config: dict[str, Any],
    api_key: str,
    case: dict[str, Any],
    max_turns: int,
    timeout: int,
    retries: int,
) -> dict[str, Any]:
    today = case.get("context", {}).get("today", TODAY)
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                f"Today is {today}. Use tools for external facts and actions. "
                "Never invent missing identifiers. Stop after a tool error when later steps depend on it."
            ),
        },
        {"role": "user", "content": case["prompt"]},
    ]
    calls: list[dict[str, Any]] = []
    transcript: list[dict[str, Any]] = []
    usage = {"input_tokens": 0, "output_tokens": 0}
    final_response = ""

    for turn in range(max_turns):
        body: dict[str, Any] = {
            "model": config["model"],
            "messages": messages,
            "tools": openai_tools(),
            "tool_choice": "auto",
            "temperature": 0,
        }
        body.update(config.get("extra_body", {}))
        if str(config["model"]).startswith("gpt-5"):
            body["max_completion_tokens"] = 2048
        else:
            body["max_tokens"] = 2048
        response = post_json(
            config["base_url"],
            body,
            {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout,
            retries,
        )
        api_usage = response.get("usage", {})
        usage["input_tokens"] += int(api_usage.get("prompt_tokens", 0) or 0)
        usage["output_tokens"] += int(api_usage.get("completion_tokens", 0) or 0)
        message = response["choices"][0]["message"]
        transcript.append({"turn": turn + 1, "assistant": message})
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            final_response = message.get("content") or ""
            break

        assistant_message = {
            "role": "assistant",
            "content": message.get("content"),
            "tool_calls": tool_calls,
        }
        messages.append(assistant_message)
        for tool_call in tool_calls:
            function = tool_call.get("function", {})
            name = function.get("name", "")
            try:
                params = json.loads(function.get("arguments") or "{}")
            except json.JSONDecodeError:
                params = {"_invalid_json": function.get("arguments")}
            result = execute_tool(name, params, today)
            record = {
                "turn": turn + 1,
                "id": tool_call.get("id"),
                "tool": name,
                "params": params,
                "result": result,
            }
            calls.append(record)
            transcript.append({"tool_result": record})
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.get("id"),
                    "content": result,
                }
            )
    else:
        return {
            "tool_calls": calls,
            "final_response": final_response,
            "usage": usage,
            "transcript": transcript,
            "error": "max_turns_exceeded",
        }

    return {
        "tool_calls": calls,
        "final_response": final_response,
        "usage": usage,
        "transcript": transcript,
        "error": "",
    }


def run_anthropic(
    config: dict[str, Any],
    api_key: str,
    case: dict[str, Any],
    max_turns: int,
    timeout: int,
    retries: int,
) -> dict[str, Any]:
    today = case.get("context", {}).get("today", TODAY)
    messages: list[dict[str, Any]] = [{"role": "user", "content": case["prompt"]}]
    calls: list[dict[str, Any]] = []
    transcript: list[dict[str, Any]] = []
    usage = {"input_tokens": 0, "output_tokens": 0}
    final_response = ""
    tools = [
        {
            "name": tool["name"],
            "description": tool["description"],
            "input_schema": tool["parameters"],
        }
        for tool in TOOLS
    ]

    for turn in range(max_turns):
        response = post_json(
            config["base_url"],
            {
                "model": config["model"],
                "max_tokens": 2048,
                "temperature": 0,
                "system": (
                    f"Today is {today}. Use tools for external facts and actions. "
                    "Never invent missing identifiers. Stop after a tool error when later steps depend on it."
                ),
                "messages": messages,
                "tools": tools,
            },
            {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            timeout,
            retries,
        )
        api_usage = response.get("usage", {})
        usage["input_tokens"] += int(api_usage.get("input_tokens", 0) or 0)
        usage["output_tokens"] += int(api_usage.get("output_tokens", 0) or 0)
        content = response.get("content", [])
        transcript.append({"turn": turn + 1, "assistant": content})
        tool_blocks = [block for block in content if block.get("type") == "tool_use"]
        if not tool_blocks:
            final_response = " ".join(
                block.get("text", "") for block in content if block.get("type") == "text"
            ).strip()
            break

        messages.append({"role": "assistant", "content": content})
        results = []
        for block in tool_blocks:
            name = block.get("name", "")
            params = block.get("input") or {}
            result = execute_tool(name, params, today)
            record = {
                "turn": turn + 1,
                "id": block.get("id"),
                "tool": name,
                "params": params,
                "result": result,
            }
            calls.append(record)
            transcript.append({"tool_result": record})
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.get("id"),
                    "content": result,
                }
            )
        messages.append({"role": "user", "content": results})
    else:
        return {
            "tool_calls": calls,
            "final_response": final_response,
            "usage": usage,
            "transcript": transcript,
            "error": "max_turns_exceeded",
        }

    return {
        "tool_calls": calls,
        "final_response": final_response,
        "usage": usage,
        "transcript": transcript,
        "error": "",
    }


def contact_email(name: str) -> str:
    aliases = {"李四": "lisi", "王五": "wangwu", "张三": "zhangsan"}
    local = aliases.get(name, re.sub(r"\W+", "", name).lower() or "unknown")
    return f"{local}@company.com"


def synthesize_value(rule: Any, key: str) -> Any:
    if not isinstance(rule, dict):
        return rule
    if rule.get("$from_previous"):
        return "lisi@company.com"
    if "$contact_email" in rule:
        return contact_email(str(rule["$contact_email"]))
    if rule.get("$nonempty"):
        return "Mock content derived from previous tool output"
    if "$contains" in rule:
        return rule["$contains"]
    return f"mock_{key}"


def dry_run_case(case: dict[str, Any]) -> dict[str, Any]:
    today = case.get("context", {}).get("today", TODAY)
    calls = []
    for turn, expected in enumerate(case.get("expected_tool_calls", []), 1):
        params = {
            key: synthesize_value(value, key)
            for key, value in expected.get("params", {}).items()
        }
        if expected["tool"] == "create_event":
            params.setdefault("start_time", "15:00")
        result = execute_tool(expected["tool"], params, today)
        calls.append(
            {
                "turn": turn,
                "id": f"dry_{turn}",
                "tool": expected["tool"],
                "params": params,
                "result": result,
            }
        )
    return {
        "tool_calls": calls,
        "final_response": case.get("expected_behavior", case.get("ground_truth_outcome", "")),
        "usage": {"input_tokens": 0, "output_tokens": 0},
        "transcript": [{"dry_run": True, "calls": calls}],
        "error": "",
    }


def normalized(value: Any) -> str:
    return re.sub(r"\s+", "", str(value)).lower()


def value_matches(expected: Any, actual: Any, key: str = "") -> bool:
    if isinstance(expected, dict):
        if expected.get("$from_previous"):
            return bool(actual) and "@" in str(actual)
        if "$contact_email" in expected:
            return normalized(actual) == normalized(contact_email(str(expected["$contact_email"])))
        if expected.get("$nonempty"):
            return bool(str(actual).strip())
        if "$contains" in expected:
            return normalized(expected["$contains"]) in normalized(actual)
    if key == "expression":
        try:
            expected_value = float(safe_calculate(str(expected)))
            actual_value = float(safe_calculate(str(actual)))
            return abs(expected_value - actual_value) <= 1e-9 * max(
                1.0, abs(expected_value), abs(actual_value)
            )
        except Exception:
            pass
    return normalized(expected) == normalized(actual)


def score_trajectory(output: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    if output.get("error"):
        return {"score": 0, "failure_type": "api_error", "notes": output["error"]}
    actual = output.get("tool_calls", [])
    expected = case.get("expected_tool_calls", [])
    forbidden = set(case.get("forbidden_tools", []))
    forbidden_called = [item.get("tool") for item in actual if item.get("tool") in forbidden]
    if forbidden_called:
        return {
            "score": 0,
            "failure_type": "unsafe_or_forbidden_tool_call",
            "notes": f"Forbidden tools called: {forbidden_called}",
        }
    if not expected:
        if actual:
            return {
                "score": 0,
                "failure_type": "unnecessary_tool_call",
                "notes": f"Expected no tool; called {[item['tool'] for item in actual]}",
            }
        if not str(output.get("final_response", "")).strip():
            return {
                "score": 0,
                "failure_type": "empty_response",
                "notes": "No tool was expected, but the model also returned no explanation",
            }
        return {
            "score": 3,
            "failure_type": "manual_behavior_review",
            "notes": "No tool expected; final response still requires human review",
        }
    if not actual:
        return {"score": 0, "failure_type": "planning_failure", "notes": "No tool called"}

    actual_names = [item.get("tool") for item in actual]
    cursor = 0
    matched_indexes: list[int] = []
    for exp in expected:
        try:
            index = actual_names.index(exp["tool"], cursor)
        except ValueError:
            return {
                "score": 1,
                "failure_type": "tool_selection_or_order_failure",
                "notes": f"Actual {actual_names}; expected ordered {[x['tool'] for x in expected]}",
            }
        matched_indexes.append(index)
        cursor = index + 1

    param_errors = []
    for exp, actual_index in zip(expected, matched_indexes):
        actual_params = actual[actual_index].get("params", {})
        for key, expected_value in exp.get("params", {}).items():
            if key not in actual_params:
                param_errors.append(f"{exp['tool']}.{key} missing")
            elif not value_matches(expected_value, actual_params[key], key):
                param_errors.append(
                    f"{exp['tool']}.{key}: expected {expected_value!r}, got {actual_params[key]!r}"
                )
    if param_errors:
        return {
            "score": 2,
            "failure_type": "parameter_error",
            "notes": "; ".join(param_errors),
        }
    if len(actual) > len(expected):
        extras = [
            actual[index]["tool"]
            for index in range(len(actual))
            if index not in set(matched_indexes)
        ]
        return {
            "score": 2,
            "failure_type": "unnecessary_tool_call",
            "notes": f"Expected sequence completed, extra calls: {extras}",
        }
    return {"score": 3, "failure_type": "none", "notes": "Expected tool sequence and parameters matched"}


def load_pricing(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def estimate_cost_cny(
    alias: str,
    usage: dict[str, int],
    pricing: dict[str, Any],
    usd_cny: float,
) -> float | None:
    item = pricing.get(alias)
    if not item:
        return None
    input_price = item.get("input_usd_per_million")
    output_price = item.get("output_usd_per_million")
    if input_price is None or output_price is None:
        return None
    usd = (
        usage.get("input_tokens", 0) * float(input_price)
        + usage.get("output_tokens", 0) * float(output_price)
    ) / 1_000_000
    return usd * usd_cny


def write_outputs(
    output_dir: Path,
    run_id: str,
    rows: list[dict[str, Any]],
    traces: list[dict[str, Any]],
    estimated_total_cny: float,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"eval_results_{run_id}.csv"
    trace_path = output_dir / f"traces_{run_id}.jsonl"
    review_path = output_dir / f"human_review_{run_id}.csv"
    summary_path = output_dir / f"summary_{run_id}.md"

    fieldnames = [
        "case_id",
        "category",
        "model",
        "model_id",
        "trajectory_score",
        "result_score",
        "reasoning_score",
        "total_score",
        "failure_type",
        "tool_calls_count",
        "tool_calls",
        "final_response",
        "input_tokens",
        "output_tokens",
        "estimated_cost_cny",
        "error",
        "notes",
    ]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with trace_path.open("w", encoding="utf-8") as handle:
        for trace in traces:
            handle.write(json.dumps(trace, ensure_ascii=False) + "\n")

    review_fields = [
        "case_id",
        "category",
        "model",
        "prompt",
        "expected_outcome",
        "auto_trajectory_score",
        "auto_failure_type",
        "tool_calls",
        "final_response",
        "result_score_0_2",
        "reasoning_score_0_2",
        "manual_failure_type",
        "review_notes",
    ]
    with review_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=review_fields)
        writer.writeheader()
        for row, trace in zip(rows, traces):
            writer.writerow(
                {
                    "case_id": row["case_id"],
                    "category": row["category"],
                    "model": row["model"],
                    "prompt": trace["case"]["prompt"],
                    "expected_outcome": trace["case"].get("ground_truth_outcome", ""),
                    "auto_trajectory_score": row["trajectory_score"],
                    "auto_failure_type": row["failure_type"],
                    "tool_calls": row["tool_calls"],
                    "final_response": row["final_response"],
                    "result_score_0_2": "",
                    "reasoning_score_0_2": "",
                    "manual_failure_type": "",
                    "review_notes": "",
                }
            )

    model_scores: dict[str, list[int]] = defaultdict(list)
    failures: Counter[str] = Counter()
    category_scores: dict[tuple[str, str], list[int]] = defaultdict(list)
    for row in rows:
        score = int(row["trajectory_score"])
        model_scores[row["model"]].append(score)
        category_scores[(row["model"], row["category"])].append(score)
        failures[row["failure_type"]] += 1

    lines = [
        f"# Automatic Summary: {run_id}",
        "",
        "> This is an automatic trajectory summary, not the final project report.",
        "",
        f"- Rows: {len(rows)}",
        f"- Estimated API cost: CNY {estimated_total_cny:.4f}",
        "",
        "## Model Scores",
        "",
        "| Model | Mean trajectory score | Full-score rate |",
        "|---|---:|---:|",
    ]
    for model, scores in model_scores.items():
        mean = sum(scores) / len(scores)
        full_rate = sum(score == 3 for score in scores) / len(scores)
        lines.append(f"| {model} | {mean:.2f}/3 | {full_rate:.1%} |")
    lines.extend(["", "## Failure Types", ""])
    for failure, count in failures.most_common():
        lines.append(f"- {failure}: {count}")
    lines.extend(["", "## Category Scores", ""])
    for (model, category), scores in sorted(category_scores.items()):
        lines.append(f"- {model} / {category}: {sum(scores) / len(scores):.2f}/3")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Results: {csv_path}")
    print(f"Traces: {trace_path}")
    print(f"Human review: {review_path}")
    print(f"Summary: {summary_path}")


def make_run_id() -> str:
    return f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{uuid.uuid4().hex[:8]}"


def main() -> int:
    args = parse_args()
    try:
        cases = load_jsonl(args.cases)
    except Exception as exc:
        print(f"Failed to load cases: {exc}", file=sys.stderr)
        return 2
    errors = validate_cases(cases)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 2
    try:
        cases = select_cases(cases, args.case_ids, args.limit)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.validate:
        counts = Counter(case["category"] for case in cases)
        print(f"Valid cases: {len(cases)}")
        for category, count in sorted(counts.items()):
            print(f"  {category}: {count}")
        return 0

    aliases = [item.strip() for item in args.models.split(",") if item.strip()]
    unknown = [alias for alias in aliases if alias not in MODEL_CONFIGS]
    if unknown:
        print(f"Unknown models: {', '.join(unknown)}", file=sys.stderr)
        return 2

    missing_keys = [
        MODEL_CONFIGS[alias]["api_key_env"]
        for alias in aliases
        if not args.dry_run and not os.getenv(MODEL_CONFIGS[alias]["api_key_env"])
    ]
    if missing_keys:
        print(f"Missing API keys: {', '.join(missing_keys)}", file=sys.stderr)
        return 2

    pricing = load_pricing(args.pricing)
    run_id = make_run_id()
    rows: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    spent_cny = 0.0

    print(f"Cases: {len(cases)} | Models: {', '.join(aliases)} | Dry run: {args.dry_run}")
    for case in cases:
        for alias in aliases:
            if not args.dry_run and spent_cny >= args.budget_cny:
                print(f"Budget reached: CNY {spent_cny:.2f}; stopping before next run")
                write_outputs(args.output_dir, run_id, rows, traces, spent_cny)
                return 3
            config = MODEL_CONFIGS[alias]
            print(f"[{case['id']}] {alias}...", end=" ", flush=True)
            started = time.time()
            try:
                if args.dry_run:
                    output = dry_run_case(case)
                elif config["provider"] == "anthropic":
                    output = run_anthropic(
                        config,
                        os.environ[config["api_key_env"]],
                        case,
                        args.max_turns,
                        args.timeout,
                        args.retries,
                    )
                else:
                    output = run_openai_compatible(
                        config,
                        os.environ[config["api_key_env"]],
                        case,
                        args.max_turns,
                        args.timeout,
                        args.retries,
                    )
            except Exception as exc:
                output = {
                    "tool_calls": [],
                    "final_response": "",
                    "usage": {"input_tokens": 0, "output_tokens": 0},
                    "transcript": [],
                    "error": str(exc),
                }

            scoring = score_trajectory(output, case)
            cost = estimate_cost_cny(alias, output["usage"], pricing, args.usd_cny)
            if cost is not None:
                spent_cny += cost
            tool_names = [item["tool"] for item in output["tool_calls"]]
            row = {
                "case_id": case["id"],
                "category": case["category"],
                "model": alias,
                "model_id": config["model"],
                "trajectory_score": scoring["score"],
                "result_score": "PENDING",
                "reasoning_score": "PENDING",
                "total_score": "PENDING",
                "failure_type": scoring["failure_type"],
                "tool_calls_count": len(tool_names),
                "tool_calls": json.dumps(tool_names, ensure_ascii=False),
                "final_response": output["final_response"][:1000],
                "input_tokens": output["usage"].get("input_tokens", 0),
                "output_tokens": output["usage"].get("output_tokens", 0),
                "estimated_cost_cny": "" if cost is None else f"{cost:.6f}",
                "error": output.get("error", ""),
                "notes": scoring["notes"],
            }
            trace = {
                "run_id": run_id,
                "model": alias,
                "model_id": config["model"],
                "case": case,
                "output": output,
                "automatic_scoring": scoring,
                "estimated_cost_cny": cost,
                "elapsed_seconds": round(time.time() - started, 3),
                "dry_run": args.dry_run,
            }
            rows.append(row)
            traces.append(trace)
            print(
                f"score={scoring['score']}/3 calls={len(tool_names)} "
                f"elapsed={trace['elapsed_seconds']:.1f}s"
            )
            if not args.dry_run:
                time.sleep(args.sleep)

    write_outputs(args.output_dir, run_id, rows, traces, spent_cny)
    if not args.dry_run and any(
        estimate_cost_cny(alias, {"input_tokens": 0, "output_tokens": 0}, pricing, args.usd_cny)
        is None
        for alias in aliases
    ):
        print("Warning: one or more model prices are not configured; cost estimate is incomplete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
