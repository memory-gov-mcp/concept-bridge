# extract — 机制抽取（Owner P1）

实现设计见 [DESIGN.md](DESIGN.md)。T2–T6 的代码共用现有 MechanismUnit、LLMClient 与 P2 GraphStore。
当前真实执行范围由用户确认为先试跑 8 篇，核算用量后再决定扩量。

## 执行

从仓库根运行。依赖使用 `uv sync --extra analyze` 安装。
通过根目录 `.env` 配置 `LLM_BASE_URL`、`LLM_MODEL`、`LLM_API_KEY`，由公共 Settings 读取。

```powershell
uv run python -m conceptbridge.extract.cli --limit 8 --dry-run
uv run python -m conceptbridge.extract.cli --limit 8 --retries 0
```

`--dry-run` 显示论文数、首轮批次数、提示词字符数和输出 token 上限。
每批最多 8 篇，默认 8 篇、零机制重抽。公共网关的传输重试最多 3 次，预检查单列其上限。
字符数和模型请求数分别记录。供应商 token/费用目前需要 P3 补齐公共网关用量字段，提案见
`docs/rfc/RFC-P1-001-token-usage.md`。

成功论文逐篇缓存。重复同一输入会直接复用，调大 limit 后也可复用已完成论文。
`--retry-failed` 显式重试已缓存的失败论文，`--retries 2` 启用最多两次机制修复。
同一数据目录的抽取与导出用 SQLite 锁串行执行。
`DEMO_MODE=1` 由公共网关约束为只使用缓存，缺少必要缓存时报错并保留已完成任务。

## 产物

`data/normalized/runs/run-*/` 保存一次完整运行的机制、概念、失败论文、审核样本和 manifest。
`data/normalized/current.json` 是多文件读取的提交标记。
根目录 mechanisms.jsonl、concepts.parquet、failed_papers.jsonl、manifest.json 为最新运行的导出副本。

模型只返回机制草稿。代码继承论文领域、生成概念及机制 ID、推导结构签名、校验证据偏移。
span 必须精确匹配原始摘要。重复片段需要明确 char_start。
动作分类复用 P2 的 classify_action，词典外使用受枚举约束的模型分类。
概念用领域和类型隔离，归一规则包含有限复数词表与显式别名。

manifest 记录模型、prompt/代码哈希、抽取器/归一版本、Git SHA、UTC 时间、输入/输出哈希、
机制数、归一前后概念数、缓存与调用统计。schema_pass_rate 按通过 schema 和证据双校验的
论文比例统计。首次通过率只统计本次新抽取论文。人工准确率保持待审核状态。
review_mechanisms.json 包含最多 30 条机制，review_concepts.json 包含最多 20 组概念，供人工填写。

## 交付 P2

完整任务卡要求 200 篇 / 500 机制，数据足够后运行以下命令。

```powershell
uv run python scripts/ingest_fixtures.py --install-index
```

8 篇试跑全部成功后，可以单独导出试跑图谱。

```powershell
uv run python scripts/ingest_fixtures.py --paper-count 8 --mechanism-count 8 --output data/pilot-fixtures --install-index
```

脚本验证原文、哈希、数量和总计小于 5MB 后发布。已有不同内容的输出包会报错，可指定新的输出目录。
输出包含 papers.min.jsonl、mechanisms.min.jsonl、graph.min.pkl 与 graph.min/ 配套目录。
P2 调用 `GraphStore.load(Path("fixtures/graph.min"))` 可直接读取正式包，试跑包使用其对应目录。
`--install-index` 将快照安装到 data/index/g-*/，现有 match.load_corpus 会识别。
嵌入沿用 P2 当前 hash_embed 实现，记录在清单中。

## 验收与当前边界

```powershell
uv run task check
uv run pytest tests/extract tests/ingest -q -p pytest_cov --cov=conceptbridge.extract --cov=conceptbridge.ingest --cov-report=term-missing --cov-fail-under=70
uv run task e2e
```

离线测试使用假网关，包含 200 篇 / 500 机制导出、GraphStore 往返和 P2 跨域匹配。
真实 T2 验收还需 500 篇、至少 1200 机制、通过率至少 98%，以及人工 30 条正确率至少 80%。
T3 还需人工检查 20 组映射。当前执行授权为 8 篇试跑，真实验收结果按 docs/state/p1.md 记录。
可选 T7 全文补充设计位于 DESIGN.md，依赖评审由 P3 负责。
