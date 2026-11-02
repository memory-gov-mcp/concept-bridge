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
| 还没有 `fixtures/mechanisms.min.jsonl`，P2 只能在 2 条样例上调参 | P2 | P1 | P1-T4 未完成 |
| `web/package.json` 还不存在，`task check` 第 5 步自动跳过 | P4 | P4 | P4-T1 未开始 |

## 环境事实（已验证）

- Windows，**没有 make** → 一律 `uv run task <cmd>`。
- `uv 0.11.16`；Python 3.11.15（uv 管理）；Node v24。
- 系统 `python` 是 Windows Store 空壳别名，**用 `uv run python`**。
- 不要引入 torch / sentence-transformers，用 `fastembed`。
