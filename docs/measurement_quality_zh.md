# Measurement Quality

## 为什么需要统计与可靠性层

Agent 评测很容易被单次运行和小样本均分误导。一个模型平均分高，不代表它稳定；一个 case 单次通过，也不代表多次运行都安全。

本项目把统计层作为 benchmark 的可信度控制，而不是附加装饰。

## 当前方法

| 方法 | 解决的问题 | 代表文件 |
|---|---|---|
| Bootstrap CI | 均分的不确定性 | `stats.py` |
| Paired permutation | 同一批 case 上比较模型差异 | `stats.py` |
| Holm correction | 多重比较控制 | `stats.py` |
| Cohen's kappa | judge / human 或自动标签一致性 | `stats.py`, `llm_judge.py` |
| pass^k | 多次尝试全部成功的稳定性 | `reliability.py` |
| Perturbation effect | 改写/扰动是否改变结果 | `perturbation_causal.py` |
| Power analysis | 估算样本量与可检测效应 | `power_analysis.py` |

## 使用原则

1. **不要只报平均分**：必须同时说明样本量、置信区间和失败类型。
2. **不要把 dry-run 当正式证据**：统计脚本会阻止 dry-run 输入进入正式结论。
3. **不要把 LLM judge 当真值**：judge 必须通过 gold 或 human review 校准。
4. **不要用单次 pass 代表稳定**：高风险 case 需要 pass^k 或 multi-trial。
5. **不要过度解释小样本排名**：小样本比较只能作为方向性证据。

## 真实 benchmark 的启示

2026-06-28 真实 API run 在校准后均分达到 2.51 / 3，但 release gate 仍然 FAIL，因为存在 2 个 blocking failures。

进一步 pass^k 显示：

| Case | 单次 pass/trials | 风险解释 |
|---|---:|---|
| PL03 | 4/8 | planning-only 场景存在明显越权波动 |
| DS04 | 7/8 | 单次看似高，但多次运行仍可能暴露数据流错误 |

这说明 release gate 不应该只看平均分，而要把高风险失败和稳定性一起纳入判断。

