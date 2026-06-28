# Benchmark 与 Rubric 设计

## 定位

本项目的定位是 Agent 行为评测框架；benchmark 是让评测可复现、可比较、可发布的组织方式。

一个完整 benchmark 不只是 case 文件，而是包含：

| 层级 | 含义 | 项目实现 |
|---|---|---|
| Scenario | 要评测的 Agent 场景 | tool use、autonomy、planning、permission、search、多轮 |
| Case suite | 具体输入样本 | `cases_*.jsonl` |
| Rubric / Oracle | 评分细则与判定标准 | expected calls、forbidden tools、required signals、final state |
| Runner protocol | 如何调用模型与记录证据 | `eval_runner.py` |
| Trace evidence | Agent 实际做了什么 | trace JSONL |
| Judge / review | 语义质量补充判断 | `llm_judge.py`, judge calibration |
| Measurement | 结果可信度 | stats、pass^k、robustness、power |
| Release decision | 能否作为正式证据 | `scorecard.py`, `release_gate.py` |

## Rubric 的证据来源

Rubric 不是主观写分数，而是从四类证据推导：

1. **Agent 能力目标**：工具调用、规划、多轮、自主性边界、权限控制、搜索证据。
2. **风险 taxonomy**：错误工具、参数错误、越权副作用、虚假完成、prompt injection、final-state mismatch。
3. **Case ground truth**：每个 case 写明 expected calls、forbidden tools、required keywords、expected/forbidden final state。
4. **真实运行 badcase**：通过 judge-rule disagreement、blocking failures、pass^k 稳定性测试反向校准 rubric。

## Case Schema

核心字段：

| 字段 | 作用 |
|---|---|
| `id` | 稳定 case 标识 |
| `module` | 评测模块，例如 tool_use、autonomy_boundary、agent_planning |
| `category` | 任务族或风险类型 |
| `prompt` / `conversation` | 用户输入 |
| `expected_tool_calls` | 应调用工具与参数 |
| `forbidden_tools` | 不能调用的工具 |
| `required_response_keywords` | 用户可见回复必须体现的信号 |
| `forbidden_response_claims` | 不能声称完成的动作 |
| `expected_final_state` | 期望环境状态 |
| `forbidden_final_state` | 禁止出现的环境状态 |
| `ground_truth_outcome` | 人类可读的正确行为 |
| `key_failure_modes` | 预期会暴露的失败模式 |
| `manual_review_focus` | 复核时重点看什么 |

## Scoring Layers

| 层级 | 判断什么 | 代表失败 |
|---|---|---|
| Tool sequence | 工具是否选对、顺序是否正确 | `tool_selection_or_order_failure` |
| Parameter matching | 参数是否完整且语义等价 | `parameter_error` |
| Boundary action | 是否该行动、澄清、拒绝、停止 | `autonomy_overreach_side_effect` |
| Final state | 文件、邮件、日历、浏览器状态是否正确 | `final_state_mismatch`, `forbidden_final_state` |
| Response signals | 回复是否如实说明状态 | `response_quality_gap`, `false_completion_or_overclaim` |
| Judge review | 开放式语义质量 | judge-rule disagreement |

## 主次分层

核心能力应重点深化：

- benchmark taxonomy；
- rubric / oracle；
- trace-based scoring；
- LLM-as-Judge governance；
- statistics / reliability；
- scorecard / release gate。

辅助能力应覆盖但不抢主线：

- stateful mock tools；
- browser local verifier；
- coding sandbox；
- CI / smoke checks；
- engineering runners。

这些辅助模块证明框架可以连接执行环境，但项目主张仍然是 Agent 行为评测方法论。

