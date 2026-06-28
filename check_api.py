"""
Model API connectivity & tool-calling verifier.

Run this FIRST, on the machine where your API keys are set, before any real eval
batch. For each selected model it checks three things and prints a clear
pass/fail line:

1. key present  - is the API key environment variable set?
2. chat ping    - does a minimal completion come back? (proves auth + endpoint + model id)
3. tool call    - does the model accept the function schema and emit one tool call?
                  (the whole framework depends on tool calls, so chat alone is not enough)

It spends only a few tokens per model. Exit code 0 means every selected model
passed both live checks; non-zero means at least one failed (with a diagnosis).

Usage (PowerShell session with keys set):
    python check_api.py
    python check_api.py --models deepseek,qwen,claude
"""

from __future__ import annotations

import argparse
import os
import time
from datetime import date

import eval_runner as er

PING_CASE = {
    "id": "_ping",
    "category": "normal",
    "prompt": "请只回复两个字：可用",
    "context": {"today": date.today().isoformat()},
    "expected_tool_calls": [],
}
TOOL_CASE = {
    "id": "_tool",
    "category": "normal",
    "prompt": "今天北京的天气怎么样？请用工具查询。",
    "context": {"today": date.today().isoformat()},
    "expected_tool_calls": [{"tool": "get_weather", "params": {"location": "北京"}}],
}


def run_case(alias: str, config: dict, api_key: str, case: dict, timeout: int, retries: int):
    """Run one case, converting any raised network/HTTP exception into an error dict
    (mirrors how eval_runner's main loop guards provider calls)."""
    try:
        if config["provider"] == "anthropic":
            return er.run_anthropic(config, api_key, case, 3, timeout, retries)
        return er.run_openai_compatible(config, api_key, case, 3, timeout, retries)
    except Exception as exc:  # noqa: BLE001 - we want any failure surfaced as a diagnosis
        return {"tool_calls": [], "final_response": "", "usage": {"input_tokens": 0, "output_tokens": 0},
                "transcript": [], "error": f"{type(exc).__name__}: {exc}"}


def diagnose(error: str) -> str:
    e = error.lower()
    if "tunnel connection failed" in e or "forbidden" in e and "403" in e:
        return "egress proxy blocked this host -> run on a machine with open network"
    if "401" in e or "invalid api key" in e or ("auth" in e and "author" not in e):
        return "auth failed -> check the API key value"
    if "404" in e or ("model" in e and "not" in e):
        return "model id not found -> set the *_MODEL env var to a valid model name"
    if "name resolution" in e or "gaierror" in e or "name or service" in e or "getaddrinfo" in e:
        return "DNS/network unreachable -> check internet/proxy"
    if "timeout" in e or "timed out" in e:
        return "timeout -> retry, or raise --timeout"
    if "429" in e or "rate" in e:
        return "rate limited / quota -> check billing"
    return "see error text"


def check_model(alias: str, timeout: int, retries: int) -> dict:
    config = er.MODEL_CONFIGS[alias]
    key_env = config["api_key_env"]
    api_key = os.getenv(key_env)
    result = {"alias": alias, "model_id": config["model"], "key_env": key_env}
    if not api_key:
        result.update(key=False, ping=None, tool=None, note=f"{key_env} not set")
        return result
    result["key"] = True

    # Chat ping
    t0 = time.time()
    ping = run_case(alias, config, api_key, PING_CASE, timeout, retries)
    result["ping_latency"] = round(time.time() - t0, 2)
    if ping.get("error"):
        result.update(ping=False, tool=None, note=f"ping: {ping['error'][:120]} | {diagnose(ping['error'])}")
        return result
    result["ping"] = True
    result["ping_reply"] = (ping.get("final_response") or "").strip().replace("\n", " ")[:40]
    result["ping_tokens"] = ping["usage"]

    # Tool call
    t0 = time.time()
    tool = run_case(alias, config, api_key, TOOL_CASE, timeout, retries)
    result["tool_latency"] = round(time.time() - t0, 2)
    if tool.get("error"):
        result.update(tool=False, note=f"tool: {tool['error'][:120]} | {diagnose(tool['error'])}")
        return result
    called = [c["tool"] for c in tool.get("tool_calls", [])]
    result["tool"] = "get_weather" in called
    result["tool_calls"] = called
    result["note"] = "ok" if result["tool"] else f"no get_weather call (got {called or 'none'})"
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify model APIs work for the eval framework.")
    ap.add_argument("--models", default="deepseek,qwen,claude")
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--retries", type=int, default=1)
    args = ap.parse_args()

    aliases = [a.strip() for a in args.models.split(",") if a.strip()]
    unknown = [a for a in aliases if a not in er.MODEL_CONFIGS]
    if unknown:
        print(f"Unknown model aliases: {', '.join(unknown)}")
        print(f"Available: {', '.join(er.MODEL_CONFIGS)}")
        return 2

    print(f"Verifying {len(aliases)} model(s): {', '.join(aliases)}\n")
    print(f"{'model':9} {'model_id':22} {'key':4} {'ping':5} {'tool':5} {'lat(s)':7} note")
    print("-" * 92)
    all_ok = True
    for alias in aliases:
        r = check_model(alias, args.timeout, args.retries)
        key = "yes" if r.get("key") else "NO"
        ping = "ok" if r.get("ping") is True else ("-" if r.get("ping") is None else "FAIL")
        tool = "ok" if r.get("tool") is True else ("-" if r.get("tool") is None else "FAIL")
        lat = r.get("tool_latency") or r.get("ping_latency") or "-"
        ok = r.get("key") and r.get("ping") and r.get("tool")
        all_ok = all_ok and bool(ok)
        print(f"{alias:9} {str(r['model_id'])[:22]:22} {key:4} {ping:5} {tool:5} {str(lat):7} {r.get('note','')}")
        if r.get("ping_reply"):
            print(f"          reply: \"{r['ping_reply']}\"  tokens={r.get('ping_tokens')}")

    print("-" * 92)
    if all_ok:
        print("ALL MODELS OK - safe to run the full eval (run_full_eval.py).")
        return 0
    print("Some checks failed - fix the notes above before spending on a full run.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
