# 曾文轩

**北京 · 29岁 · 4年数据科学 / 评测方法论经验 · 数学硕士（哈尔滨工业大学）**  
电话：15989343362 ｜ 邮箱：1056960934@qq.com ｜ GitHub: https://github.com/hins1997/agent-tool-use-eval

---

## 求职方向

大模型 / Agent 评测、Agent 数据策略、Eval 产品经理、AI 产品评测专家、模型策略评估方向。

我过去 4 年主要做实验评估、因果推断、指标体系和自动化评测护栏；近期将这些方法迁移到大模型 Agent Eval，完成一个 trace-first 的 Agent 行为评测框架，并真实跑通 OpenAI / Claude / DeepSeek 三模型评测、LLM-as-Judge、release gate、scorer calibration 和 pass^k 稳定性分析。

---

## 核心能力

- **评测体系设计**：能把模糊的“效果不好 / 模型不稳 / Agent 越权”拆成 case、rubric、trace、failure taxonomy 和 release gate。
- **Agent 行为评测**：覆盖 tool use、planning、多轮交互、clarify/refuse/stop/defer、自主性边界、side-effect 权限、search evidence、prompt injection。
- **统计与因果推断**：熟悉 A/B test、SRM、Bootstrap、CUPED、Switchback、Causal Impact、DML、Uplift、paired permutation、Holm correction、pass^k。
- **LLM-as-Judge 治理**：使用 OpenAI 主裁判 + Claude/DeepSeek 交叉裁判，区分 rule score、judge score、bias audit 和 human/gold calibration。
- **工程实现**：Python / Pandas / SQL；能用 AI coding 工具快速搭建 eval runner、trace scorer、judge pipeline、scorecard、CI smoke gate。

---

## 近期重点项目：Agent 行为评测框架

**个人项目 · 2026.06 · GitHub: https://github.com/hins1997/agent-tool-use-eval**

项目定位：构建一个面向 Agent 行为的 trace-first 评测框架，评估模型是否会正确使用工具，以及是否能控制自主性边界。

- **设计多 suite 评测集**：覆盖工具调用可靠性、Agent planning、自主性边界、多轮澄清、动态用户纠错、权限副作用、Search / Deep Research、stateful final state、agentic coding、browser web 等。
- **实现自动化评测 pipeline**：`eval_runner.py` 支持多模型 API、并发运行、temperature/trials、完整 trace、规则打分、成本记录和结果 CSV。
- **构建 LLM-as-Judge 机制**：OpenAI 作为正式主裁判，Claude / DeepSeek 作为交叉裁判；输出 judge-vs-rule 对比和 judge-family bias audit，避免 self-judge 虚高被静默纳入结论。
- **引入统计与可靠性评估**：使用 bootstrap CI、paired permutation、Holm correction、robustness perturbation、pass^k 评估稳定性，而不是只看均分。
- **完成真实三模型运行**：OpenAI / Claude / DeepSeek 真实 API smoke run 108 行；校准和 targeted rerun 后 mean trajectory score = 2.51 / 3，dry-run-like rows = 0，但 release gate 仍 FAIL，因为保留 2 个真实 blocking failures。
- **代表性发现**：DeepSeek 在 `PL03` 中偶发违反 “先不要执行” 的 planning-only 边界；在 `DS04` 中偶发工具链数据流缺口。针对两个 blocking case 做 8 次 pass^k，`PL03` 4/8 pass，`DS04` 7/8 pass，综合 pass^5 = 0.17，说明单次通过率会低估稳定性风险。

可展示材料：

- `docs/portfolio_for_interview_zh.md`
- `docs/real_benchmark_20260628/README.md`
- `docs/real_benchmark_20260628/blocking_and_evidence_rerun_analysis.md`
- `docs/real_benchmark_20260628/blocking_case_passk_analysis_zh.md`

---

## 工作经历

### 京东 · 零售商业智能部 · 数据科学 ｜ 2024.07 — 至今

**评测平台自动化护栏与策略评估**

- 设计 SRM 自动检测 + Bootstrap FPR 监控思路，将实验/评测质量从人工经验判断推进到可量化的统计置信区间，减少实验结论被流量分配异常或假阳率污染的风险。
- 开发同期群诊断和长期留存分析工具，识别“短期指标提升但长期价值不足”的策略评估盲区，支持上线评审和策略复盘。
- 参与 LaunchReview / 分层实验方案设计，帮助业务从单次指标比较转向评估假设、样本质量、长期影响和风险边界并重的决策流程。

**Uplift 建模与因果评估**

- 在智能补贴 / 广告投放场景中使用 DML / Uplift 思路评估策略真实增量效果，辅助识别价格敏感或高增量人群，支持差异化策略和预算效率优化。
- 将过去业务策略评估中的“因果归因、实验质量、指标护栏”迁移到 Agent Eval 项目，用于评估模型行为是否稳定、可解释、可发布。

### 美团 · 平台商业分析部 · 数据科学 ｜ 2023.07 — 2024.07

**多业务线实验评测体系与准实验分析**

- 面向搜索、推荐、营销等多分发场景，参与设计跨业务线评测隔离与指标互信机制，降低并行实验、网络效应和场景干扰对结论的污染。
- 针对无法完全随机分流的业务场景，引入 Causal Impact 等准实验方法，剥离自然增长和外部波动，估计策略真实因果效果。
- 将实验方法论沉淀为可复用文档和分析流程，为跨团队策略复盘提供统一评估口径。

### 字节跳动 · TikTok 直播营收策略组 · 数据科学 ｜ 2022.01 — 2023.06

**双边市场评测方案与方差缩减**

- 针对直播双边市场干预溢出问题，设计并迭代 Switchback Analysis，用时间片轮转实验处理网络效应，支持直播营收策略的可信归因。
- 在充值档位推荐等实验中应用 CUPED、去极值、用户分层等方差缩减方法，在保证统计功效的前提下提高实验灵敏度、缩短观测周期。
- 积累了复杂系统中“不能只看均值、必须控制干扰和不确定性”的评估经验，这也是后续设计 Agent Eval release gate 和 pass^k 的方法论来源。

---

## 教育背景

**哈尔滨工业大学 · 数学 · 硕士** ｜ 2019.09 — 2022.01  
**广州大学 · 数学与应用数学 · 本科** ｜ 2015.09 — 2019.07

---

## 关键词

Agent Eval · LLM Evaluation · Trace-based Evaluation · Tool Use · Planning · Autonomy Boundary · LLM-as-Judge · Judge Bias · Release Gate · pass^k · A/B Test · Causal Inference · Bootstrap · CUPED · SRM · Switchback · Causal Impact · Python · SQL
