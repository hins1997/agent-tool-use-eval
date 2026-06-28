# Industry Eval Gap Analysis

This document positions the project against frontier-model and agent-evaluation practice, then turns the gaps into an implementation roadmap.

For the current implementation completion audit, see `docs/industry_alignment_completion_audit.md`.

The short version: this project is already strong as a trace-first, behavior-focused agent evaluation framework. It has a clear niche: tool-use reliability, autonomy boundary control, multi-turn scoring, human review, LLM-as-judge calibration, robustness, causality, reliability, and power analysis. Compared with frontier-lab evaluation systems, the biggest remaining gaps are environment realism, scenario scale, dynamic user simulation, broader safety coverage, coding/browser/OS task families, and production-style governance.

## Current Project Strengths

| Layer | Current capability | Why it matters |
|---|---|---|
| Trace-first evidence | Stores model output, tool calls, arguments, tool results, and scoring decisions | Catches failures that final-answer grading misses |
| Tool-use reliability | 44 structured cases across normal, boundary, adversarial, and long-chain behavior | Tests tool choice, parameter extraction, state transfer, injection resistance, and stop conditions |
| Autonomy boundary | 16 single-turn cases plus 9 multi-turn autonomy cases | Tests act / clarify / refuse / stop / defer, including persistence across turns |
| Multi-turn state | Conversation-level cases and turn-level expectations | Catches premature action, stale-context execution, and late-turn boundary collapse |
| Human review | Rule score can be merged with outcome and reasoning review | Prevents fully automatic scoring from becoming overconfident |
| LLM-as-judge | OpenAI primary judge, Claude / DeepSeek cross judges, judge-vs-human kappa, judge bias report | Treats the judge as an instrument that must be validated |
| Measurement quality | Bootstrap CIs, paired tests, Holm correction, kappa, causal effects, pass^k, power analysis | Converts benchmark runs from demos into defensible evidence |

## Industry Patterns To Match

### 1. Frontier model reports are multi-axis, not single-score

OpenAI and Anthropic publish model/system-card style evaluations that separate general capability, tool or agentic capability, safety, robustness, and deployment risk. OpenAI's Preparedness Framework also separates tracked risk categories such as cybersecurity, CBRN, persuasion, and model autonomy. Anthropic's Claude 4 materials similarly report agentic coding and tool-heavy benchmarks alongside safety evaluation.

Implication for this project: keep the tool/autonomy focus, but report it as a model-card style scorecard with clear suites, risk tiers, confidence intervals, and known limitations.

### 2. Agent benchmarks increasingly run in environments

Public agent benchmarks such as SWE-bench Verified, TAU-bench, WebArena, OSWorld, and GAIA evaluate agents through task execution, state transitions, browser or OS actions, tool feedback, and multi-step recovery. The important distinction is not only "did the model answer correctly"; it is "did it interact with an environment correctly over time".

Implication: local mock tools are excellent for deterministic unit-style evals, but the next step is a sandboxed stateful environment layer: browser state, file state, CRM/calendar/email state, shell state, and resettable fixtures.

### 3. Dynamic user simulation matters

TAU-bench popularized a key idea for tool agents: the user can be an active simulator rather than a static prompt. This matters for autonomy boundaries because the model may ask a clarification question, receive partial information, face pushback, or be tempted to violate a policy after repeated pressure.

Implication: autonomy evaluation should move beyond fixed multi-turn transcripts toward scenario simulators that respond based on the agent's actual previous action.

### 4. Safety evals are policy and risk taxonomies, not only refusal cases

The current autonomy suite already covers refusal, defer, and side-effect control. Frontier safety evaluation is broader: prompt injection, data exfiltration, cyber misuse, unauthorized financial action, privacy leakage, medical/legal overclaiming, persuasion/manipulation, hidden instruction hierarchy, and high-impact decision-making.

Implication: add a formal risk taxonomy and map every case to risk type, permission level, side-effect severity, and expected boundary behavior.

### 5. Judge quality must be governed

The project has already moved in the right direction: OpenAI as primary judge, Claude / DeepSeek as cross judges, no rule-score leakage, temperature 0, structured JSON, and judge-vs-human kappa. The remaining gap is operational governance: judge prompt versioning, gold calibration sets, drift monitoring, and release gates.

Implication: LLM-as-judge should become a stable measurement subsystem, not a one-off script.

## Gap Matrix

| Area | Current state | Frontier-style target | Priority |
|---|---|---|---|
| Suite scale | 44 tool-use, 16 single-turn autonomy, 9 autonomy multi-turn, plus robustness variants | Hundreds of versioned cases across task families and risk tiers | P0 |
| Reporting | Several generated markdown reports | Single model-card style scorecard with per-suite scores, CIs, deltas, judge agreement, and failure taxonomy | P0 |
| Case taxonomy | Categories exist, but metadata is partly implicit | Manifest-driven taxonomy: suite, capability, risk, side-effect severity, required permission, tool family, oracle type | P0 |
| Stateful tools | Local deterministic mocks | Resettable sandbox environments with persistent state and snapshots | P1 |
| Dynamic multi-turn | Fixed transcripts with turn expectations | User simulator reacts to the agent's clarification/refusal/action choices | P1 |
| Permission boundary | Act / clarify / refuse / stop / defer | Explicit policy matrix for side effects: read-only, draft-only, reversible, irreversible, external-send, purchase/delete | P1 |
| Tool-error recovery | Covered in long-chain cases | Dedicated flaky-tool, timeout, retry, stale-result, and partial-failure suites | P1 |
| Agentic coding | Implemented as `cases_agentic_coding.jsonl` | SWE-bench-style local repo tasks with tests, diffs, and tool traces | P2 |
| Web/browser tasks | Implemented as `cases_browser_web.jsonl` | WebArena/BrowserGym-inspired tasks with browser state and prompt-injection pages | P2 |
| Computer-use tasks | Not yet a suite | OSWorld-style UI/file/browser tasks, preferably sandboxed | P3 |
| Long context / memory | Limited | Long-context retrieval, stale memory, conflicting documents, memory poisoning | P2 |
| Safety breadth | Autonomy boundary cases | Cyber, privacy, data exfiltration, persuasion, medical/legal/financial, policy hierarchy, prompt injection | P1 |
| Judge governance | Multi-judge and kappa exist | Judge prompt registry, calibration gold set, drift report, self-judge bias dashboard | P0 |
| Operations | Manual commands plus full-run script | CI smoke gate, release benchmark gate, cost tracking, artifact index, reproducible seeds | P1 |

## Recommended Roadmap

### P0: Make The Framework Legible And Governed

1. Add a benchmark manifest.
   - Implemented as `benchmark_manifest.json` to keep the project dependency-free.
   - Fields: suite id, version, case count, capability tags, risk tags, side-effect severity, oracle type, scoring owner, judge policy, minimum report requirements.

2. Add a model-card style scorecard generator.
   - Suggested file: `scorecard.py`
   - Inputs: rule results, human review, judge CSV, bias report, stats report, causal report, robustness report.
   - Output: one consolidated markdown scorecard per run.

3. Add judge calibration artifacts.
   - Suggested files: `judge_calibration_gold.csv`, `docs/judge_calibration.md`
   - Require judge-vs-human kappa before using judge scores as formal evidence.

4. Expand the failure taxonomy.
   - Suggested categories: wrong tool, wrong parameter, unauthorized side effect, premature action, unnecessary clarification, unsafe compliance, false completion, hallucinated tool result, failed recovery, context carryover failure, prompt-injection compliance.

### P1: Deepen The Core Differentiator

1. Build a permission and side-effect suite.
   - Cases should cover read-only, draft-only, reversible, irreversible, external-send, purchase/payment, delete, privacy disclosure, and high-impact advice.

2. Build a stateful tool sandbox.
   - Calendar, email, files, CRM/order system, and payment-like mock tools should have resettable state snapshots.
   - The scorer should verify final environment state, not only the tool-call sequence.

3. Add dynamic user simulation.
   - Replace some fixed transcripts with a user simulator that can answer clarifying questions, resist refusals, provide corrections, or attempt prompt injection.
   - This is especially valuable for autonomy boundary evaluation, because the measured behavior is whether the agent updates boundaries correctly after interaction.

4. Add dedicated tool-error recovery.
   - Timeout, rate limit, missing dependency, unavailable contact, partial API success, inconsistent tool output, stale cache, and retry-limit cases.

### P2: Add Public-Benchmark-Adjacent Agent Suites

1. Agentic coding suite.
   - Small local repositories with failing tests.
   - Score by test pass, patch minimality, tool trace, and whether the agent asked unnecessary questions.
   - This mirrors the spirit of SWE-bench Verified without needing a large external harness at first.

2. Browser/web suite.
   - Local web apps with forms, tables, search, login-like state, and malicious page text.
   - Score final browser/application state and injection resistance.

3. Long-context and memory suite.
   - Multi-document tasks with conflicting, stale, or hidden information.
   - Evaluate whether the agent retrieves the right source, cites tool evidence, and avoids stale memory.

### P3: Broaden To Full Agent Operating Environments

1. OS/computer-use suite inspired by OSWorld.
2. Multimodal evidence tasks: screenshots, PDFs, spreadsheets, and forms.
3. Continuous regression monitoring: scheduled benchmark runs, judge drift checks, and report diffs.

## What To Prioritize For This Portfolio

The highest-signal next work is not simply "more cases". It is:

1. A manifest-driven benchmark taxonomy.
2. A model-card scorecard generator.
3. A richer autonomy/permission boundary suite.
4. A resettable stateful mock environment.
5. Dynamic user simulation for multi-turn autonomy.

That combination makes the project look less like a case collection and more like a real evaluation platform. It also keeps the positioning sharp: many public benchmarks measure whether an agent can complete tasks; this framework measures whether an agent completes tasks while respecting tool reliability, permission boundaries, and side-effect control.

## Suggested Near-Term Implementation Tasks

| Task | Artifact | Expected impact |
|---|---|---|
| Benchmark manifest | `benchmark_manifest.json` | Makes coverage, gaps, and reporting requirements explicit |
| Scorecard generator | `scorecard.py` | Produces a single executive report per run |
| Permission cases | `cases_permission_boundary.jsonl` | Implemented: strengthens the autonomy-boundary module with explicit permission and side-effect tiers |
| Stateful tools | Implemented inside `eval_runner.py` with `cases_stateful_tools.jsonl` | Enables environment-state scoring |
| Dynamic simulator | Implemented in `eval_runner.py` with `cases_dynamic_autonomy.jsonl` | Turns autonomy from transcript scoring into interaction scoring |
| Judge calibration | `judge_calibration_gold.csv` | Prevents judge drift and self-judge bias from silently entering results |

## Source Anchors

- OpenAI Preparedness Framework: https://openai.com/safety/preparedness/
- OpenAI GPT-4o System Card: https://openai.com/index/gpt-4o-system-card/
- Anthropic Claude 4 announcement and system-card materials: https://www.anthropic.com/news/claude-4
- SWE-bench Verified: https://openai.com/index/introducing-swe-bench-verified/
- TAU-bench: https://arxiv.org/abs/2406.12045
- WebArena: https://arxiv.org/abs/2307.13854
- OSWorld: https://arxiv.org/abs/2404.07972
- GAIA: https://arxiv.org/abs/2311.12983
- DeepSeek-V3 Technical Report: https://arxiv.org/abs/2412.19437
- Qwen3 Technical Report: https://arxiv.org/abs/2505.09388
- MiniMax-M1 Technical Report: https://arxiv.org/abs/2506.13585
