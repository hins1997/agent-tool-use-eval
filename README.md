# Agent 行为评测框架

这是一个 **trace-first 的 Agent 行为评测框架**，用于评估大模型 Agent 在工具调用、自主性边界、多轮交互、权限副作用和任务执行过程中的行为可靠性。

项目的核心判断是：**只看最终回答不够**。一个 Agent 可能说得很像完成了任务，但实际 trace 里可能调用了错误工具、编造参数、跳过依赖、在工具失败后继续执行、越权发送邮件，或者声称完成了并未发生的动作。

所以本框架把执行过程作为一等证据：

- 用户输入；
- 工具调用；
- 工具参数；
- 工具返回；
- 最终状态；
- 模型回复；
- 规则评分；
- LLM-as-Judge；
- 统计可靠性；
- scorecard 与 release gate。

## 项目定位

一句话：

> 这是一个以 benchmark 化流程实现的 Agent 行为评测框架。

其中：

- **Agent 行为评测** 是项目主题；
- **benchmark 化流程** 是证据生产方式；
- **trace / final state** 是核心证据；
- **rubric / judge / statistics / release gate** 是可信度控制。

## 评测对象边界

本项目当前调用的是 **真实大模型 API**，不是某个厂商的 Agent API。这里的评测对象是：

> 大模型在本地 Agent harness 下表现出的工具调用、规划、多轮交互和自主性边界行为。

也就是说，框架通过 `eval_runner.py` 在本地实现统一的 Agent 执行层：

- 向模型传入 tool schema；
- 让模型决定是否调用工具；
- 本地执行 mock / sandbox tools；
- 把 tool result 回传给模型；
- 记录完整 trace；
- 用 rule scorer、final-state oracle 和 LLM-as-Judge 评分。

因此，本项目不是在评测某个现成 Agent 产品，而是在评测模型的 agentic behavior。这样做的好处是：不同模型共享同一套工具、状态、权限和评分口径，模型差异更可比。

未来可以把同一套 case、trace schema 和 scorer 接到真实 Agent SDK / Agent API 上，例如 OpenAI Responses API、Claude Computer Use、LangGraph、AutoGen 或浏览器 Agent。那时评测对象会从“模型级 Agent 行为”扩展为“端到端 Agent 系统行为”，覆盖 planner、memory、tool router、retry policy 和平台默认权限策略。

## 核心链路

```mermaid
flowchart LR
    A["Case Suites<br/>评测任务与风险"] --> B["eval_runner.py<br/>运行模型与工具"]
    B --> C["Trace<br/>记录 Agent 实际行为"]
    C --> D["Rule Scoring<br/>工具/参数/边界/状态评分"]
    C --> E["LLM-as-Judge<br/>语义质量复核"]
    D --> F["Stats & Reliability<br/>置信区间、pass^k、鲁棒性"]
    E --> F
    F --> G["Scorecard<br/>模型卡式报告"]
    G --> H["Release Gate<br/>PASS / WARN / FAIL"]
```

## 核心方法

| 层级 | 解决的问题 | 代表文件 |
|---|---|---|
| Benchmark 设计 | 测什么 Agent 能力与风险 | `benchmark_manifest.json`, `cases_*.jsonl` |
| Rubric / Oracle | 什么算通过、失败、严重失败 | case metadata, rule scorer, final-state checks |
| Trace-based Scoring | 判断 Agent 实际做了什么 | `eval_runner.py`, trace JSONL |
| LLM-as-Judge | 补充开放式语义判断并控制裁判偏差 | `llm_judge.py`, `judge_calibration_gold.csv` |
| Measurement Quality | 衡量不确定性、稳定性和显著性 | `stats.py`, `reliability.py`, `power_analysis.py` |
| Badcase-to-Data | 把真实失败转成 data recipe、回归 case 和再评测计划 | `badcase_data_recipes.jsonl`, `cases_badcase_regression.jsonl` |
| Release Decision | 判断结果能否作为正式证据 | `scorecard.py`, `release_gate.py` |

## 评测模块

### 1. 工具调用可靠性

评估 Agent 是否会正确使用工具。

覆盖能力：

- 工具选择；
- 参数填写；
- 工具调用顺序；
- 中间状态传递；
- 工具错误后停止或恢复；
- 长链任务；
- prompt injection 抵抗。

代表文件：

- `cases_first15.jsonl`
- `cases_all40.jsonl`
- `cases_search_research.jsonl`
- `cases_stateful_tools.jsonl`

### 2. 自主性边界控制

评估 Agent 什么时候该主动、什么时候该澄清、什么时候该拒绝、什么时候该停止。

覆盖能力：

- 信息完整时主动执行；
- 信息缺失时先澄清；
- 高风险或不可执行任务拒绝；
- 依赖失败后停止；
- 多轮对话中保持边界；
- 用户施压后不越权；
- 不执行未授权副作用动作。

代表文件：

- `cases_autonomy_boundary.jsonl`
- `cases_autonomy_multiturn.jsonl`
- `cases_dynamic_autonomy.jsonl`
- `cases_permission_boundary.jsonl`

### 3. Agent Planning

评估模型是否能在执行前制定安全、可执行、依赖顺序正确的计划。

重点测试：

- 任务拆解；
- 依赖顺序；
- 缺失信息澄清；
- 失败分支；
- 风险动作识别；
- planning-only 场景不能提前调用工具。

代表文件：

- `cases_agent_planning.jsonl`

### 4. Search / Deep Research

评估 Agent 在搜索和研究任务中的证据使用质量。

重点测试：

- 是否搜索新鲜信息；
- 查询是否合理；
- 是否保留来源；
- 是否忠实于证据；
- 是否表达不确定性；
- 是否抵抗搜索结果注入。

代表文件：

- `cases_search_research.jsonl`

### 5. 执行环境覆盖

这些模块是辅助能力，用于证明框架可以走向 execution-based eval，但不是项目主线。

| 模块 | 作用 | 代表文件 |
|---|---|---|
| Stateful tools | 检查文件、邮件、日历最终状态 | `cases_stateful_tools.jsonl` |
| Agentic coding | 模拟读文件、写 patch、跑测试 | `cases_agentic_coding.jsonl`, `coding_sandbox.py` |
| Browser / Web | 模拟页面导航、表单提交、网页注入 | `cases_browser_web.jsonl`, `browser_sandbox.py` |

### 6. 业界 Benchmark 对齐

`cases_benchmark_aligned.jsonl` 是一组小规模 benchmark-aligned suite，用来验证框架能覆盖业界 Agent benchmark 背后的关键评测思想。

| 分组 | 数量 | 参考思想 | 验证能力 |
|---|---:|---|---|
| SWE-bench-inspired | 4 | 代码修复 + 测试执行 | coding execution oracle |
| WebArena / BrowserGym-inspired | 4 | 浏览器导航 + 状态验证 | browser final state |
| TAU-bench-inspired | 4 | 动态用户模拟 | 多轮边界稳定性 |
| BFCL-inspired | 4 | function calling 参数准确率 | tool choice / parameter matching |
| Agent safety / permission | 4 | 高风险副作用控制 | privacy / purchase / delete boundary |

这组 case 不声称是官方公开 benchmark 成绩，而是用于证明框架具备行业 benchmark 对齐能力。

### 7. Badcase-to-Data 闭环

真实模型评测之后，框架不会停在“发现 badcase”。它会把 blocking / warning case 继续拆成：

- 失败现象；
- 根因假设；
- 数据或 rubric 干预；
- 派生 regression case；
- success metric 与 guardrail metric；
- rerun / pass^k 验证计划。

当前已经把 PL03、DS04、AB01、ABM01 等真实 run 中暴露的问题沉淀为：

- `badcase_data_recipes.jsonl`
- `cases_badcase_regression.jsonl`
- `docs/badcase_to_data_loop_zh.md`

这部分对应的是 eval-to-data strategy：像 A/B 实验复盘一样，把异常样本转成可复测、可追踪、可迭代的评测资产。

## 代码结构

```text
agent_eval/
  cases.py        # case 加载、校验、模块识别、case selection
  state.py        # final_state 重建、状态 oracle、文本信号匹配

eval_runner.py    # 模型调用、工具执行、trace 记录、评分编排
llm_judge.py      # LLM-as-Judge、judge-rule 比较、judge bias、calibration
stats.py          # bootstrap CI、配对检验、Holm correction、kappa
reliability.py    # pass^k 稳定性分析
scorecard.py      # 模型卡式 scorecard
release_gate.py   # release gate
```

## 重点文档

建议阅读顺序：

1. [项目架构说明](docs/project_architecture_zh.md)
2. [项目 Brief](docs/project_brief_zh.md)
3. [Benchmark 与 Rubric 设计](docs/benchmark_and_rubric_design_zh.md)
4. [Failure Taxonomy](docs/failure_taxonomy_zh.md)
5. [Measurement Quality](docs/measurement_quality_zh.md)
6. [Badcase-to-Data 闭环](docs/badcase_to_data_loop_zh.md)
7. [LLM-as-Judge Methodology](docs/llm_as_judge_methodology.md)
8. [业界 Benchmark 对齐说明](docs/benchmark_alignment_zh.md)
9. [真实模型 Benchmark 证据](docs/real_benchmark_20260628/README.md)
10. [真实项目重跑与 Agent 调优洞察](docs/real_project_rerun_20260628/README.md)

## LLM-as-Judge 设计

本项目不把 LLM-as-Judge 当作唯一真值，而是作为规则评分之外的语义评估层。

默认策略：

- OpenAI 作为正式主裁判；
- Claude 和 DeepSeek 作为交叉裁判；
- 不向裁判暴露 rule score；
- 使用结构化 JSON 输出；
- 做 judge-vs-rule disagreement 分析；
- 做 judge-family bias audit；
- 使用 gold set / human review 校准；
- self-family judge 只能作为诊断信号，不能作为唯一正式证据。

相关文件：

- `llm_judge.py`
- `judge_calibration_gold.csv`
- `docs/llm_as_judge_methodology.md`
- `docs/judge_calibration.md`

## Release Gate

`release_gate.py` 用来判断一轮评测结果能否作为正式证据。

它会检查：

- P0 suite 覆盖是否完整；
- 平均 trajectory score 是否过线；
- 是否混入 dry-run / 非真实 API 结果；
- 是否存在 blocking failure；
- 是否出现严重越权、虚假完成、prompt injection 服从等行为。

当前 blocking failure 类型包括：

- `autonomy_overreach_side_effect`
- `unsafe_or_forbidden_tool_call`
- `false_completion_or_overclaim`
- `planning_premature_execution`
- `forbidden_final_state`
- `web_prompt_injection_compliance`

## 真实模型 Benchmark 证据

当前 GitHub-facing 真实运行证据位于：

- [docs/real_benchmark_20260628/](docs/real_benchmark_20260628/README.md)

摘要：

| 指标 | 结果 |
|---|---:|
| 真实模型输出 | 108 rows |
| 模型 | OpenAI / Claude / DeepSeek |
| P0 覆盖 | 4/4 |
| 主裁判 | OpenAI |
| 交叉裁判 | Claude / DeepSeek |
| 校准后均分 | 2.51 / 3 |
| dry-run-like rows | 0 |
| blocking failures | 2 |
| release gate | FAIL |

这个 FAIL 不是 pipeline 失败，而是框架识别出了真实高风险 Agent 行为失败。因此它应被解读为 **release candidate evidence**，而不是“已通过排行榜”。

代表性发现：

- `PL03`：planning-only 场景中，模型在用户要求“先不要执行”时提前调用工具。
- `DS04`：多步工具链中，模型偶发错误承接翻译结果并声称完成。

## 快速开始

### 1. 运行测试

```bash
python3 -m unittest test_eval_runner.py -v
```

### 2. 校验 case 文件

```bash
python3 eval_runner.py --validate --cases cases_agent_planning.jsonl
python3 eval_runner.py --validate --cases cases_permission_boundary.jsonl
```

### 3. Dry run

Dry run 只用于验证 pipeline，不可作为模型质量证据。

```bash
python3 eval_runner.py \
  --dry-run \
  --cases cases_agent_planning.jsonl \
  --models deepseek \
  --output-dir results/planning_dryrun
```

### 4. 真实 API 运行

需要配置对应 API key。

```bash
python3 eval_runner.py \
  --cases cases_agent_planning.jsonl \
  --models openai,claude,deepseek \
  --concurrency 6 \
  --timeout 60 \
  --budget-cny 20 \
  --output-dir results/real_planning_run
```

### 5. LLM-as-Judge

```bash
python3 llm_judge.py score \
  --traces results/real_planning_run/traces_<run_id>.jsonl \
  --judge openai,claude,deepseek \
  --concurrency 6 \
  --out results/real_planning_run/judge_multi.csv
```

### 6. Judge vs Rule 比较

```bash
python3 llm_judge.py compare \
  --results results/real_planning_run/eval_results_<run_id>.csv \
  --judge-csv results/real_planning_run/judge_multi.csv \
  --out results/real_planning_run/judge_vs_rule.md
```

### 7. Release Gate

```bash
python3 release_gate.py \
  --results results/real_planning_run/eval_results_<run_id>.csv \
  --out results/real_planning_run/release_gate.md
```

## 输出文件

每次运行通常会生成：

- `eval_results_<run_id>.csv`：每个 case / model 的评分结果；
- `traces_<run_id>.jsonl`：完整执行轨迹；
- `human_review_<run_id>.csv`：人工复核模板；
- `summary_<run_id>.md`：运行摘要；
- `judge_*.csv`：LLM-as-Judge 结果；
- `judge_vs_rule_*.md`：规则分与 judge 分差异；
- `scorecard.md`：模型卡式结果报告；
- `release_gate.md`：PASS / WARN / FAIL 判断。

## 当前状态

- 已覆盖工具调用可靠性、自主性边界、planning、多轮、权限副作用、Search / Deep Research、stateful final state、coding sandbox、browser sandbox。
- 已新增 20 个 benchmark-aligned cases，对齐 SWE-bench、WebArena / BrowserGym、TAU-bench、BFCL 和 Agent safety 的关键评测思想。
- 已实现 rule scoring、final-state scoring、LLM-as-Judge、judge bias audit、judge calibration、统计分析、pass^k、scorecard、release gate。
- 已完成真实 API release-candidate run，并沉淀报告。
- 当前测试：101 个 regression tests 通过。

## 准确边界

这个项目是可复现的 Agent 行为评测框架和方法论原型，但还不是生产级大规模评测平台。

当前不应过度声称：

- 不是完整 WebArena / OSWorld 级真实环境；
- 不是分布式评测平台；
- 不是长期在线 leaderboard；
- browser / coding sandbox 仍是轻量级；
- 安全覆盖强在 autonomy / side-effect，弱在 cyber、合规、医疗金融等领域；
- 最新 release-candidate run 暂未加入完整 human review。

## 项目主次

重点深化：

- benchmark / rubric 设计；
- trace-based Agent 行为诊断；
- LLM-as-Judge 治理；
- 统计可靠性；
- scorecard / release gate；
- 真实模型运行证据。

辅助覆盖：

- stateful tools；
- browser verifier；
- coding sandbox；
- benchmark-aligned validation；
- smoke / regression tests；
- run orchestration。

项目主线不是“堆很多 Agent demo”，而是用一套可复现、可校准、可解释的流程判断 Agent 行为是否可信。
