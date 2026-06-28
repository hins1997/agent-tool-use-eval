# Agent 行为评测框架：面试项目 Brief

## 一句话定位

我做了一个 trace-first 的 Agent 行为评测框架，用来评估模型是否会可靠使用工具，以及是否能控制自主性边界；后来进一步补齐了 planning、Search / Deep Research、动态多轮、权限边界、stateful sandbox、LLM-as-Judge、统计显著性和 model-card scorecard。

## 为什么做

最终回答不能证明 Agent 质量。模型可能说得很像完成了任务，但实际轨迹里可能跳过搜索、编造参数、错误调用工具、在依赖失败后继续执行、越权执行副作用，或者对网页/搜索结果里的恶意指令照单全收。

所以这个项目把执行轨迹作为一等证据：输入、工具调用、参数、工具结果、最终回复、自动评分、人工复核和 judge 评分都被记录下来。

## 核心模块

| 模块 | 评测什么 |
|---|---|
| Tool-use reliability | 工具选择、参数填写、跨步骤状态传递、错误后停止、长链任务 |
| Agent planning | 任务分解、依赖顺序、澄清前置、失败分支、风险边界、工具预算 |
| Search / Deep Research | 搜索新鲜性、来源 URL、证据忠实、不确定性表达、搜索结果注入抵抗 |
| Autonomy boundary | 该主动时主动、该澄清时澄清、该拒绝时拒绝、该停止时停止 |
| Permission boundary | read-only、draft-only、外发确认、资金动作、不可逆删除、隐私披露 |
| Stateful sandbox | 不只看调用序列，也检查最终文件、邮件、日历、浏览器状态 |
| LLM-as-Judge | OpenAI 主裁判，Claude/DeepSeek 交叉裁判，比较 judge / rule / human 差异 |
| Measurement quality | bootstrap CI、配对检验、Holm 校正、Cohen's kappa、pass^k、power analysis |

## 当前证据

- 当前主证据：DeepSeek / OpenAI / Claude 真实 API smoke run，108 行真实模型输出，P0 suite 覆盖 4/4。
- 本轮定位为 no-human-review release candidate；人工复核暂时跳过，但完成了 OpenAI 主裁判、Claude/DeepSeek 交叉裁判、judge bias audit、rule-vs-judge 比较。
- 校准和 targeted rerun 后 mean trajectory score = 2.51 / 3，dry-run-like rows = 0；release gate 仍 FAIL，因为保留了 2 个真实 blocking failures。
- 针对 2 个 blocking case 跑了 DeepSeek pass^k：`PL03` 为 4/8 pass，`DS04` 为 7/8 pass，综合 pass^5 = 0.17，说明存在稳定性风险。
- 历史补充证据：早期 45 行三模型 run 已完成人工复核，可用于说明 human review 工作流。
- 101 个回归测试覆盖 case validation、trajectory scoring、scorer calibration、planning、search/deep research、多轮、动态用户、stateful final state、LLM judge、统计、scorecard。
- `benchmark_manifest.json` 管理 suite、能力标签、风险标签、oracle 类型和优先级。
- `scorecard.py` 输出 model-card 风格报告，避免只报一个平均分。

## 代表性发现

1. 模型在简单工具调用上可能都不错，但边界、对抗和长链任务会暴露明显差异。
2. 高分不一定可信；小样本下模型差异需要置信区间和配对检验，不应只看均值。
3. LLM-as-Judge 不能直接当真值，需要固定主裁判、交叉裁判、人工校准和 self-judge bias 检查。
4. Planning 应单独评测，不能只从长链执行顺序里间接推断。
5. Search / Deep Research 不能只测是否调用搜索，还要测来源保留、证据忠实和不确定性。

## 和岗位 JD 的对应

| JD 要求 | 项目证据 |
|---|---|
| 设计 Agent 评测数据集 | 多 suite case files，覆盖 planning/tool/multi-turn/autonomy/search |
| 分析 Agent trace 失败根因 | trace JSONL、failure taxonomy、human review、analysis report |
| 构建自动化评测流水线 | `eval_runner.py`、`run_full_eval.py`、GitHub Actions smoke |
| LLM-as-Judge / Trace-based Eval | `llm_judge.py`、judge calibration gold、judge bias report |
| 数据科学和统计严谨性 | `stats.py`、`causal_eval.py`、`reliability.py`、`power_analysis.py` |
| 输出评测报告和模型决策依据 | `scorecard.py`、`ANALYSIS_REPORT.md`、`SCORECARD.md` |

## 诚实边界

这个项目已经是 portfolio-grade eval framework，但还不是 production-grade public benchmark。

当前主要缺口：

1. 扩展 suite 还需要真实模型完整运行和人工复核。
2. Browser / coding 环境目前仍是 mock，还不是 Playwright 或真实 repo sandbox。
3. Judge calibration gold set 已有，但还缺自动校准命令和漂移报告。
4. CI 目前是 smoke gate，还没有趋势 dashboard 和 release gate 阈值。
5. 安全覆盖强在 autonomy / side-effect，弱在 cyber、persuasion、domain compliance。

## 60 秒讲法

我做这个项目是为了证明自己不是只会跑 benchmark，而是能设计一套可信的 Agent 行为评测方法。我的核心判断是：Agent 不能只看最终回答，必须看执行轨迹。

我把评测拆成工具调用可靠性、自主性边界、planning、Search / Deep Research、stateful final state，再叠加人工复核、LLM-as-Judge 校准、统计显著性和 scorecard 报告。真实跑过 DeepSeek、OpenAI、Claude，并且没有夸大结论：小样本下排名只是方向性，不是显著胜负。

如果继续推进，我会优先做三件事：补 human review / gold calibration；把 browser/coding 从 mock 升级到更真实的 sandbox；把 release gate、pass^k 和 judge drift 做成持续化 CI 报告。
