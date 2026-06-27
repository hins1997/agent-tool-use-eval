# Results 目录规则

- `dryrun/`：模拟输出，只验证工程链路，永远不能作为简历或报告证据。
- `eval_results_*.csv`：真实 API 自动评分结果，包含 `module` 字段，可区分工具调用可靠性与自主性边界控制。
- `traces_*.jsonl`：真实完整轨迹。
- `human_review_*.csv`：人工复核工作表。
- `summary_*.md`：运行器自动摘要，仅包含轨迹层，并按模块/场景拆分。
- `merged_results_*.csv`：人工复核与自动分合并结果。
- `analysis_*.md`：分析器生成的报告草稿。

正式报告引用数据时，必须同时注明结果 CSV、模型 ID、运行日期、评测模块和是否已完成人工复核。
