# 交接板索引（P3 独占写，其余人只读）

**不要在这个页面写东西。** 每个人只写 `docs/state/p<N>.md`，四人文件互不重叠，
这是 AGENTS.md §10「零文件交集」的一部分——共享的交接板会在每个合并窗口制造冲突。

| Owner | 角色 | 进度 / 阻塞 / 技术债 |
|---|---|---|
| P1 | 数据与抽取 | [state/p1.md](state/p1.md) |
| P2 | 图谱与匹配 | [state/p2.md](state/p2.md) |
| P3 | 平台与集成 | [state/p3.md](state/p3.md) |
| P4 | 前端与可视化 | [state/p4.md](state/p4.md) |

## 全局阻塞（2026-11-04 21:20）

| 阻塞 | 影响谁 | 负责人 | 状态 |
|---|---|---|---|
| 500 篇 / 1394 条已可运行，正式抽取门槛（500 篇 ≥1200 条且通过率 ≥98%、30 条人工抽检）仍未关闭 | 答辩口径 | P1 | 进行中，见 state/p1.md |
| 评测仍是 30 条正例闭集，不是这 500 篇上的 P@5 | 答辩口径 | P2 | 报告已生成，不要把闭集数字说成全库 |
| 默认嵌入是哈希，假设无缓存时是规则模板 | 结果质量 | P2 | 技术债，未改 |

`fixtures/mechanisms.min.jsonl`、`graph.min.pkl`、`web/` 都已在仓库里。`uv run task check` 会跑前端 typecheck。

## 现在这版作品（2026-11-04）

可运行语料：`fixtures/corpus500.zip`，安装到 `data/index/g-20261104-corpus500-v1`（500 篇原文、1394 条机制）。命令与三个示例见仓库根 [README.md](../README.md)。

未开 `DEMO_MODE` 时，`POST /api/v1/bridge` 走 `run_bridge`，`stub=false`。自动选源最多 5 条，三个预置查询的图彼此不同。`DEMO_MODE=1` 与 `--fixtures` 仍只读 `fixtures/bridge.sample.json`。

## 接口现状

| 端点 | 状态 | 说明 |
|---|---|---|
| `POST /api/v1/bridge` | 可用 | 有索引时走真实匹配；`DEMO_MODE=1` 只读冻结样例 |
| `POST /api/v1/bridge/stream` | 可用 | SSE：`stage`×3 → `result` → `done`。`progress` 不是真实百分比 |
| `GET /api/v1/health` | 可用 | `graph_version` 来自当前快照，含 `demo_mode` / `graph_ready` |
| `GET /api/v1/mechanisms/{id}` | 可用 | 与 `/bridge` 同一份快照 |
| `GET /api/v1/graph/subgraph` | 可用 | 与 `/bridge` 同一份快照 |
| `GET /api/v1/eval/report` | 可用 | 读 `eval/reports/latest.json`，缺则返回空表 |
| `POST /api/v1/feedback` | 可用 | 追加到 `data/feedback.jsonl` |
| `GET /` | 可用 | 无 Node 时的极简页面，不进 OpenAPI |

`stub=true` 表示还没接上算法、返回的是样例。`degraded=true` 表示超时或异常。两者都不返回 5xx。匹配器自己超时会保留已生成的桥并标 `degraded`；API 在导入失败或未捕获异常时仍退回样例并标 `degraded`。

## 环境事实（已验证）

- Windows 与 Linux 都用 `uv run task <cmd>`。Windows 上若没有 make，不要改走 `make`。
- 用 `uv run python`，不要用系统 `python`。
- 不要引入 torch / sentence-transformers。默认嵌入是哈希；`fastembed` 仅在显式选择时使用。
- 部分网络环境下到 github.com 的 HTTPS 会握手失败，SSH 可用。这不影响本地 `uv run task`。
