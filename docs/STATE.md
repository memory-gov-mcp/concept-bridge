# 交接板索引（P3 独占写，其余人只读）

**不要在这个页面写东西。** 每个人只写 `docs/state/p<N>.md`，四人文件互不重叠，
这是 AGENTS.md §10「零文件交集」的一部分——共享的交接板会在每个合并窗口制造冲突。

| Owner | 角色 | 进度 / 阻塞 / 技术债 |
|---|---|---|
| P1 | 数据与抽取 | [state/p1.md](state/p1.md) |
| P2 | 图谱与匹配 | [state/p2.md](state/p2.md) |
| P3 | 平台与集成 | [state/p3.md](state/p3.md) |
| P4 | 前端与可视化 | [state/p4.md](state/p4.md) |

## 全局阻塞（P3 每次合并窗口后更新）

| 阻塞 | 影响谁 | 负责人 | 状态 |
|---|---|---|---|
| 还没有 `fixtures/mechanisms.min.jsonl` 与 `graph.min.pkl`，P2 只能在 2 条样例上调参 | P2 | P1 | P1-T4 未完成 |
| `web/package.json` 还不存在，`task check` 第 5 步（前端 typecheck）自动跳过 | P4 | P4 | P4-T1 未开始 |

## 接口现状（给 P4/P2 的现状快照）

| 端点 | 状态 | 说明 |
|---|---|---|
| `POST /api/v1/bridge` | 可用 | 返回 `BridgeResult`，当前走 fixture（`stub=true`） |
| `POST /api/v1/bridge/stream` | 可用 | SSE：`stage`×3 → `result` → `done` |
| `GET /api/v1/health` | 可用 | 含 `demo_mode` / `graph_ready` |
| `GET /api/v1/mechanisms/{id}` | 可用 | 点图谱节点用 |
| `GET /api/v1/graph/subgraph` | 可用 | 暂返回 fixture 子图 |
| `GET /api/v1/eval/report` | 可用 | 读 `eval/reports/latest.json`，缺则返回空表 |
| `POST /api/v1/feedback` | 可用 | 追加到 `data/feedback.jsonl` |

降级语义（P2 不需要实现，API 层已包住）：`stub=true` = 还没接算法；`degraded=true` = 超时或异常。两者都不返回 5xx。

## 环境事实（已验证）

- Windows，**没有 make** → 一律 `uv run task <cmd>`。
- `uv 0.11.16`；Python 3.11.15（uv 管理）；Node v24。
- 系统 `python` 是 Windows Store 空壳别名，**用 `uv run python`**。
- 控制台代码页 cp936 → `task` 已强制切到 65001 并统一子进程 UTF-8，中文不再乱码。
- 不要引入 torch / sentence-transformers，用 `fastembed`。
- **本机到 github.com 的 HTTPS 不通（TLS 握手中断），SSH over 443 可用**。
  推送要么换网络（热点），要么走 SSH。这不影响本地开发与 `uv run task` 全部命令。
