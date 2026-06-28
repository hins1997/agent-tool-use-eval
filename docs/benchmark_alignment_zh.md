# 业界 Benchmark 对齐说明

## 为什么新增这组 case

本项目的核心定位是 Agent 行为评测框架，而不是复刻某一个公开 benchmark。为了让项目能和业务先进公司的 Agent 评测要求对齐，新增 `cases_benchmark_aligned.jsonl` 作为一组小规模、高质量、可解释的 benchmark-aligned case suite。

这组 case 的目的不是声称“跑通了 SWE-bench / WebArena / TAU-bench / BFCL”，而是验证框架能覆盖这些业界 benchmark 背后的关键评测思想：

- execution-based coding eval；
- browser state verification；
- dynamic user simulation；
- function calling 参数准确率；
- permission / side-effect safety。

## Suite 概览

| 分组 | 数量 | 参考思想 | 本项目验证点 |
|---|---:|---|---|
| SWE-bench-inspired coding | 4 | 读 repo 文件、改代码、跑测试 | patch state + test execution |
| WebArena / BrowserGym-inspired browser | 4 | 浏览器导航、表单、按钮、网页注入 | DOM-like final state + injection resistance |
| TAU-bench-inspired dynamic user | 4 | 用户模拟器根据 Agent 行为继续交互 | clarify/act/refuse/stop 的多轮稳定性 |
| BFCL-inspired tool calling | 4 | 函数选择与参数抽取 | tool sequence + strict parameters |
| Agent safety / permission | 4 | 高风险副作用边界 | privacy、external send、delete、purchase |

## 文件

- Case 文件：`cases_benchmark_aligned.jsonl`
- Manifest suite：`benchmark_aligned_agent_tasks`
- 优先级：P1
- Oracle：`rule_trace_plus_final_state_plus_execution_verification`

## 设计原则

1. **只借鉴评测思想，不声称官方成绩**  
   每个 case 都包含 `benchmark_reference` 字段，明确 `family`、`borrowed_idea` 和 `not_claimed_as`。

2. **小规模但高区分度**  
   当前只放 20 个 case。目标是证明框架能处理关键 Agent 行为类型，而不是堆数量。

3. **复用现有 pipeline**  
   这组 case 可以直接接入：
   - `eval_runner.py`
   - `llm_judge.py`
   - `scorecard.py`
   - `release_gate.py`
   - `coding_sandbox.py`
   - `browser_sandbox.py`

4. **不冲淡主线**  
   项目主线仍然是工具调用可靠性和自主性边界控制。这组 suite 是行业对齐证据，放在 P1，而不是替代 P0 核心 benchmark。

## 运行方式

```bash
python3 eval_runner.py --validate --cases cases_benchmark_aligned.jsonl
```

Dry run：

```bash
python3 eval_runner.py \
  --dry-run \
  --cases cases_benchmark_aligned.jsonl \
  --models deepseek \
  --output-dir results/benchmark_aligned_dryrun
```

真实模型运行：

```bash
python3 eval_runner.py \
  --cases cases_benchmark_aligned.jsonl \
  --models openai,claude,deepseek \
  --concurrency 6 \
  --timeout 60 \
  --budget-cny 30 \
  --output-dir results/benchmark_aligned_real
```

## 如何解读

这组 case 可以支持这样的表述：

> 本项目不是复刻某一个公开 benchmark，而是参考 SWE-bench、WebArena / BrowserGym、TAU-bench、BFCL 等评测思想，构建了一组 benchmark-aligned Agent 行为 case，用来验证框架对 coding、browser、dynamic-user、function-calling 和 permission-boundary 场景的覆盖能力。

不应表述为：

> 本项目跑通了 SWE-bench / WebArena / TAU-bench / BFCL。

## 后续扩展

下一步如果要继续增强，可以优先做：

1. 对 browser 子集增加真实 Playwright screenshot / DOM evidence；
2. 对 coding 子集增加更接近真实 patch diff 的验证；
3. 对 dynamic-user 子集增加更多用户策略分支；
4. 对 BFCL-inspired 子集增加嵌套参数、并行工具选择和歧义澄清；
5. 对 safety 子集扩展 cyber、privacy、compliance、finance risk。
