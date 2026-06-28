# JD-Based Job-Fit Gap Audit

This audit is based on the 31 target-role JD screenshots and the local JD summary at `../目标岗位JD汇总.md`, with spot checks against original screenshots such as DeepSeek Agent Data Strategy Engineer, Moonshot Agent Eval Product, and Tencent Cloud AI Agent Test Engineer.

It replaces the earlier generic LLM / Agent Evaluation Engineer audit. The relevant target roles are not one single job family; they split into evaluation product, evaluation engineering, Agent data strategy, model strategy, safety evaluation, and testing platform roles.

## Overall Judgment

The project is a strong match for the evaluation/product/data-strategy side of the target jobs, especially:

1. DeepSeek Agent 数据策略 / 数据评测 / 模型策略搜索评估.
2. Moonshot 大模型数据 Eval PM / Agent Eval Product.
3. StepFun 大模型评测产品经理.
4. Alibaba 数据科学专家-大模型安全评测.
5. AliCloud AI 产品评测专家/工程师.
6. MiniMax 大模型评测研究员, if positioned through statistical rigor and model behavior analysis.
7. Tencent / 2345 Agent testing roles, as reach roles if the engineering sandbox and CI gaps are strengthened.

The project is weaker for pure algorithm-research, post-training, multimodal data-production, medical-domain, and distributed evaluation-platform engineering roles.

## JD Demand Clusters

Across the screenshots, repeated demands cluster into these themes:

| JD demand cluster | Examples from target JDs | Current project coverage |
|---|---|---|
| Agent evaluation data and scenarios | DeepSeek Agent 数据策略: planning, tool use, multi-turn, instruction following, boundary cases | Strong; planning is now a standalone suite |
| Evaluation framework / benchmark design | Moonshot, StepFun, Ant, Tencent, AliCloud ask for multi-dimensional eval frameworks and internal benchmarks | Strong |
| Trace-based failure diagnosis | Moonshot Agent Eval Product asks to inspect Agent Trace and separate context, planning, tool-use, reasoning failures | Strong |
| Tool-use / Agent task execution | Tencent asks for tool-call accuracy, reasoning-chain stability, long memory, Agent+Workflow; DeepSeek asks for tool calling and multi-turn | Strong |
| LLM-as-Judge / multi-judge bias control | Tencent and Meituan explicitly mention LLM-as-Judge and judge bias | Strong; includes a fixed 20-example judge calibration gold set |
| Statistical and experimental rigor | Alibaba safety eval and MiniMax value math/statistics rigor; JD summary emphasizes scientific experiments | Strong |
| Productized reporting and cross-team loop | Moonshot, StepFun, AliCloud ask for eval conclusions to become data/product/model iteration | Medium-High |
| Real sandbox / execution-based eval | Tencent, 2345, Moonshot Eval Product mention verifiable tasks, sandbox, benchmark automation | Medium-High for coding and local browser; `coding_sandbox.py` executes target tests, `browser_sandbox.py` verifies local browser traces, OS still mock |
| CI/CD and production platform | 2345 asks CI/CD; Moonshot Eval Engineer and StepFun system roles ask platform/system engineering | Medium; CI smoke gate and run-to-run delta report exist, production orchestration still shallow |
| Public benchmark literacy | Tencent, StepFun, Moonshot ask SWE-bench, Tau-bench, OSWorld, Arena, Terminal-Bench awareness | Medium-High |
| Training/data strategy linkage | DeepSeek and Moonshot ask translating failures into training/eval data strategy | Medium |
| Safety taxonomy breadth | Alibaba safety eval needs hallucination/compliance/ethics; Ant asks finance/medical/app ecosystem risks | Medium |
| Multimodal/domain-specific eval | StepFun multimodal, Alibaba multimodal label expert, Baichuan medical | Low by design |
| Algorithm/post-training research | Zhipu, Ant, Zero-One ask PyTorch, RLHF/DPO, Critic model, NLP/data synthesis | Low-Medium |

## First-Tier Role Fit

| Role | Fit | Why the project helps | Main missing proof |
|---|---:|---|---|
| Alibaba 数据科学专家-大模型安全评测 | High | Strong match to scientific eval experiments, risk cases, judge calibration, statistics, Python | Broader safety taxonomy: hallucination/compliance/ethics/cyber/privacy beyond Agent side effects |
| MiniMax 大模型评测研究员 | Medium-High | Strong statistical rigor, model behavior explanation, score uncertainty, failure taxonomy | More algorithm/model-internal understanding; stronger multi-modal/text reasoning eval examples |
| DeepSeek Agent 数据策略工程师 | High | Standalone planning suite, tool-use/multi-turn/boundary cases, Agent trace analysis, data-gap mindset | Real coding-agent usage logs; stronger Python engineering and sandbox evidence |
| AliCloud AI 产品评测专家/工程师 | High | Evaluation framework, toolchain, scorecard, trace store, automated scripts, product-quality framing | Platformization evidence: CI, version registry, release gates |
| Moonshot 大模型数据 Eval PM | High | Multi-dimensional framework, actionable failure taxonomy, model-card report, eval-to-data loop narrative | More explicit data-demand prioritization and example of eval result becoming data recipe |
| DeepSeek 模型策略 PM - 搜索评估方向 | High | Dedicated Search / Deep Research mini-suite, evidence-use failures, badcase analysis, A/B/data science background | Product comparison logs across Kimi/DeepSeek/Perplexity-style search products |
| DeepSeek Agent 数据评测专家 | High | Case quality, boundary tests, scoring standards, human/judge agreement, failure modes | More examples of high-quality Agent data annotation/rubric design |
| StepFun 大模型评测产品经理 | High | Benchmark manifest, scorecard, multi-suite eval, badcase taxonomy, automation | Multi-modal/long-context coverage and product workflow diagrams |

## Second-Tier / Reach Role Fit

| Role | Fit | Project relevance | Gap to close |
|---|---:|---|---|
| Tencent Cloud AI Agent 测试高级工程师 | Medium-High reach | Very close conceptually: trace-based eval, execution-based eval, LLM-as-Judge, Agent benchmarks | CI/CD, Docker/Linux sandbox, multi-Agent/workflow, external blog/open-source signal |
| 2345 智能体 Agent 测评工程师 | Medium reach | Three-layer eval idea maps well to result/trace/end-to-end scoring | Docker/Linux, sandbox automation, LangSmith/DeepEval/W&B style LLMOps, CI integration |
| Meituan 大模型评测专家 | High but lower salary | Judge bias, anti-contamination, eval loop, Vibe coding-style automation | Claude Code/OpenClaw usage depth and larger real benchmark run |
| Ant 大模型评测体系 / Benchmark | Medium | Adversarial analysis, boundary mining, benchmark framework | PyTorch, training/fine-tuning/alignment chain, finance/medical/app domain eval |
| Moonshot Agent 模型评估产品经理 | Medium-High | Real-scenario Agent behavior, reliability, multimodal/safety language | More product experience framing and real user-value metrics |
| Moonshot Eval Engineer | Medium reach | Framework and toolchain are relevant | Distributed systems, data pipelines, operations, Agent Loop/MCP/Memory/Multi-Agent depth |
| StepFun 模型与 Agent 评测系统工程师 | Medium reach | Eval runner and mock environments demonstrate prototype ability | Full-stack/platform engineering, middleware, real execution environments |
| DeepSeek / StepFun 模型策略 PM | Medium-High | Data analysis, badcase, evaluation-to-strategy loop | Product strategy artifacts, competitive product logs, prompt/demo experiments |

## Roles This Project Should Not Overfit To

| Role type | Why not a priority |
|---|---|
| Medical eval strategy PM | Requires medical/public-health domain background |
| Multimodal label/domain expert | Requires art, video, music, or multimodal production taste |
| Pure algorithm/post-training researcher | Requires stronger PyTorch, RLHF/DPO, Critic model, paper/research track |
| Big-data multimodal data engineering | Requires Spark/Hive/Hadoop/PB-scale ETL |
| Generic business growth / traffic strategy PM | Skill overlap is high, but it does not advance the AI-native evaluation positioning |

## Project Coverage Against JD Responsibilities

| Responsibility in JD screenshots | Current artifact | Coverage |
|---|---|---:|
| Build high-quality Agent eval datasets | `cases_all40.jsonl`, `cases_autonomy_*`, `cases_permission_boundary.jsonl` | High |
| Cover planning, tool use, multi-turn, instruction following | `cases_agent_planning.jsonl`, tool-use, autonomy, multi-turn, dynamic-user suites | High |
| Analyze model shortcomings and failure modes | `ANALYSIS_REPORT.md`, failure taxonomy, human review | High |
| Build scalable/verifiable task construction | `benchmark_manifest.json`, `eval_runner.py`, `run_full_eval.py` | Medium-High |
| Evaluate Agent trace and distinguish planning/context/tool/reasoning failures | Trace logging plus scoring/failure types | High |
| Build LLM-as-Judge / Execution-based / Trace-based eval | `llm_judge.py`, final-state scoring, trace scorer | High |
| Control judge bias and multi-judge disagreement | OpenAI primary, Claude/DeepSeek cross judges, kappa/bias reports | High |
| Scientific experiment design and statistical rigor | `stats.py`, `causal_eval.py`, `power_analysis.py`, `reliability.py` | High |
| Productized model-card reporting | `scorecard.py`, `SCORECARD.md` | High |
| Eval-to-data or eval-to-training loop | Failure taxonomy and roadmap docs | Medium |
| Search / Deep Research eval | `cases_search_research.jsonl` covers query formulation, freshness, citation support, uncertainty, and search-result injection | Medium-High |
| Safety eval beyond autonomy | Permission/side-effect/prompt-injection cases exist | Medium |
| Real browser/OS/coding execution environments | Mock stateful suites plus `coding_sandbox.py` and Playwright-compatible `browser_sandbox.py` exist | Medium |
| Platform engineering, CI/CD, distributed operation | Scripts and tests exist | Medium-Low |
| Public benchmark / open-source influence | Industry analysis and public-benchmark-aligned suites exist | Medium |

## Concrete Missing Items

### Must Close Before Heavy Applications

1. **Run expanded suites with real models.** Current formal evidence is strongest for tool-use reliability. The autonomy, permission, dynamic, stateful, coding, and browser suites need at least a smoke real run with DeepSeek/OpenAI/Claude plus human review.
2. **Document daily coding-agent usage.** DeepSeek explicitly asks Claude Code/Cursor/OpenClaw heavy usage. Keep logs: task, tool, failure, what you learned, how it changed benchmark cases.
3. **Add search product comparison logs.** `cases_search_research.jsonl` exists; the next step is comparing Kimi/DeepSeek/Perplexity-style products on the same rubric.

### Strongly Recommended For Reach Roles

1. **Promote browser verification beyond the local fixture.** `browser_sandbox.py` is a Playwright-compatible local-page verifier; the next step is a richer Playwright site with screenshots, reset hooks, and browser-event artifacts.
2. **Expand CI beyond smoke.** `.github/workflows/eval-smoke.yml`, `run_delta.py`, `coding_sandbox.py`, and `release_gate.py` exist; next is dry-run scorecard artifact upload and scheduled trend comparison.

### Can Be Stated As Honest Gaps

1. No large distributed eval platform yet.
2. No PyTorch/RLHF/DPO/Critic-model implementation yet.
3. Browser/coding/OS environments are local or partial, not full OSWorld/Terminal-Bench/WebArena-scale.
4. Safety coverage is strongest on autonomy and side effects, weaker on cyber, persuasion, compliance, and domain-specific medical/finance policy.
5. Human review is single-reviewer plus rubric, not a full inter-annotator adjudication workflow.
6. The project is portfolio-grade and reproducible, not yet a public leaderboard or production benchmark service.

## Best Interview Positioning By Role Family

### Evaluation Product / Eval PM

Use this line:

> I built a trace-first Agent behavior eval framework that turns vague model-quality issues into measurable cases, rubric, traces, judge scores, human review, confidence intervals, and scorecards. My strength is making evaluation conclusions explainable and actionable, not just producing a leaderboard.

Best evidence:

- `benchmark_manifest.json`
- `scorecard.py`
- `docs/industry_alignment_completion_audit.md`
- `results/real_run_20260627/ANALYSIS_REPORT.md`

### Agent Data Strategy / Agent Evaluation

Use this line:

> I focus on converting Agent failures into data and boundary-test design. The project covers planning, tool use, multi-turn clarification, permission boundaries, dynamic user pressure, final-state verification, and prompt-injection resistance.

Best evidence:

- `cases_all40.jsonl`
- `cases_autonomy_multiturn.jsonl`
- `cases_permission_boundary.jsonl`
- `cases_dynamic_autonomy.jsonl`
- traces under `results/real_run_20260627/`

### Safety Evaluation

Use this line:

> I do not claim a complete safety benchmark yet, but I have implemented the evaluation mechanics needed for safety work: risk taxonomy, refusal/defer/stop cases, unauthorized side-effect checks, human review, judge calibration, and severity-aware reporting.

Best evidence:

- `cases_permission_boundary.jsonl`
- `cases_autonomy_boundary.jsonl`
- `llm_judge.py`
- `stats.py`

### Evaluation Engineering / Testing Platform

Use this line:

> The current system is a minimum viable eval platform: case registry, provider runner, trace store, rule grader, final-state scorer, LLM judge, statistical reports, scorecard, and tests. I would not overclaim distributed platform experience, but the architecture maps cleanly to production modules.

Best evidence:

- `eval_runner.py`
- `run_full_eval.py`
- `test_eval_runner.py`
- `scorecard.py`

## Priority补强 Plan

| Priority | Action | Target roles helped |
|---|---|---|
| P0 | Real smoke run for expanded suites + human review | All evaluation roles |
| Done | `judge_calibration_gold.csv` + calibration doc + `llm_judge.py calibrate` | Moonshot, Tencent, Meituan, Alibaba |
| Done | Chinese one-page interview brief | Product/eval PM roles |
| Done | Search/Deep Research eval mini-suite | DeepSeek model strategy, Moonshot Agent Eval |
| Done | GitHub Actions CI smoke | Tencent, 2345, AliCloud, Eval Engineer |
| Done | Playwright-compatible local browser verifier | Tencent, Moonshot Agent Eval, 2345 |
| Done | Tiny real coding sandbox | DeepSeek Agent data, Tencent, SWE-bench-style roles |
| Done | Release-gate thresholds | AliCloud, Tencent, 2345, Eval Engineer |
| P2 | Broader safety taxonomy suite | Alibaba safety, Ant Benchmark |
| Done | Run-to-run delta report | Productized eval platform roles |
| P2 | Public technical blog | Tencent, MiniMax, StepFun reach roles |

## Final Recommendation

Use the project as the central proof for evaluation/product/data-strategy roles. It already covers the essence of the first-tier JD requirements: designing high-quality eval cases, analyzing Agent traces, building multi-dimensional eval frameworks, validating judges, and reporting statistical uncertainty.

Do not present it as evidence for full production platform engineering, post-training research, or multimodal/domain-specialist roles. For those, present it as a strong adjacent foundation and name the exact gaps you are actively closing.
