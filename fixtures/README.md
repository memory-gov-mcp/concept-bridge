# P1 真实语料与图谱

## 当前扩量版本

`corpus500.zip` 包含 500 篇原文和 1394 条机制，475 篇有可用机制，另 25 篇记录了原因。
原交付的 1436 条机制经 Agent 抽查和定向核对后，剔除 42 条比较、相关性或描述性关系，修正 14 条。
原有 8 篇／17 条机制的 ID 和内容完整保留。包内保留原交付报告、排除及修正记录和文件哈希。
用户于 2026-11-04 授权按可用版本接入。独立人工审核仍为 pending，原 95.4% 通过率和清理后的
95% 覆盖率均有记录。结果支持可运行演示，语义质量仍需领域人员复核。

从仓库根安装完整语料并启动真实查询服务。导入无需模型 API key。

```powershell
uv sync --extra analyze
uv run python scripts/ingest_corpus.py
$env:DEMO_MODE = '0'
uv run task dev
```

安装会校验哈希和证据，生成概念表、归一产物及完整 P2 图谱到 `data/index/g-*/`。
已有 1500 篇原始语料会保留，新环境写入包内 500 篇原文。输入冲突会报错，重复安装无需模型请求。
当前主查询读取新图谱。`task demo`、`--fixtures` 仍使用旧预置样例，展示本批语料使用以上命令。
机制详情、邻域和 health 与主查询读同一份快照（`api/services/snapshot.py`）。没装索引时退回 `bridge.sample.json`。

`mini200/` 是另行交付的 200 篇／500 机制小包，可供 P2 直接调用
`GraphStore.load(Path("fixtures/mini200/graph.min"))`。整个 fixtures 目录小于 5 MB。

## 保留的八篇试跑版本

本包包含 8 篇 OpenAlex 文献的真实摘要、17 条机制和 30 个概念。
覆盖材料 2 篇、生物 2 篇，以及化学、医学、计算机和物理各 1 篇。

机制由本次 Codex 对话依据原文辅助整理，extractor_version 为 curated-codex-v1。
草稿与原始证据保存在 pilot8.drafts.json。逐条通过 Pydantic 和原文精确切片校验。
独立领域专家审核状态为 pending，模型 confidence 是整理时的主观置信度。
本批额外模型 API 调用数为 0。自动批量抽取的实测记录仍需另行产生。

## 给 P2 的文件

| 文件 | 内容 |
|---|---|
| papers.min.jsonl | 8 篇文献的标题、摘要、年份、领域、DOI 或 OpenAlex 来源链接 |
| mechanisms.min.jsonl | 17 条合法 MechanismUnit，含精确 evidence span 和字符偏移 |
| graph.min/ | 可通过 GraphStore.load 直接加载的配套图谱目录 |
| graph.min.pkl | 与 graph.min/graph.pkl 相同的任务卡兼容文件 |
| p1.manifest.json | 实际数量、整理来源、版本和交付文件 SHA-256 |
| bridge.pilot8.json | 本机真实主查询返回的 BridgeResult，供界面对接参考 |

从仓库根安装依赖并将图谱接入现有匹配器。

```powershell
uv sync --extra analyze
$env:DEMO_MODE = '0'
$env:PYTHONIOENCODING = 'utf-8'
uv run python -c "from pathlib import Path; from conceptbridge.graph.store import GraphStore; GraphStore.load(Path('fixtures/graph.min')).save(Path('data/index/g-20261103-pilot8'))"
uv run python -m conceptbridge.match.cli --query "锂枝晶抑制" --top-k 5
```

该命令读取本包图谱。现有 CLI 的 --fixtures 参数固定读取 bridge.sample.json。
API 的 DEMO_MODE=1 同样走旧演示样例。读取本包时使用 DEMO_MODE=0。

本机通过 POST /api/v1/bridge 查询锂枝晶抑制，返回 HTTP 200 和 5 条跨域桥，
stub=false、degraded=false；每条引用都可回查本包原文。
详情、子图和 health 的版本已与主查询对齐。

本包可供 P2 进行小规模真实数据建图和匹配联调。正式任务卡中的 200 篇 / 500 机制规模另行补齐。
