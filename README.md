# ConceptBridge 概念桥

跨学科结构类比检索：输入领域 A 的一个难题，从领域 B 的文献里检索**结构相似**的机制，
输出可迁移假设、差异说明与原文出处。

> 一句话：现在的跨学科检索找的是"同一个词"，我们找的是"同一个道理"。

赛题归属：高级组主题 3「跨域知识探索 / 跨学科知识发现」。
**完整规范、契约、分工、任务卡全部在 [AGENTS.md](AGENTS.md)，开工前必读。**

---

## 30 秒跑起来

```bash
uv sync --extra analyze --extra dev   # 装依赖
uv run task contract                  # 生成 contracts/
uv run task check                     # 必须绿
uv run task dev                       # http://127.0.0.1:8000/docs
```

没有 `make`（本队全是 Windows），一切命令都走 `uv run task <cmd>`。

| 命令 | 作用 |
|---|---|
| `uv run task setup` | 装 Python + 前端依赖 |
| `uv run task contract` | 从代码重新生成 `contracts/`（改了模型必须跑） |
| `uv run task check` | ruff + mypy + pytest + 契约漂移 + 前端 typecheck |
| `uv run task e2e` | 3 条演示 query 端到端冒烟 |
| `uv run task eval` | 生成 `eval/reports/latest.json` |
| `uv run task dev` | 起 API（:8000） |
| `uv run task demo` | 起 API，`DEMO_MODE=1` 离线模式 |
| `uv run task freeze v0.9-submit` | 冻结打 tag |

---

## 现在能不能开工？

可以。P2 的 `run_bridge()` 已经合入 `main`。未开 `DEMO_MODE` 时，`/api/v1/bridge` 走真实匹配，`meta.stub=false`。当前语料仍是 `fixtures/bridge.sample.json`。`DEMO_MODE=1` 继续只读这份样例。

- **P4 前端**：对着 `http://127.0.0.1:8000/api/v1/bridge` 写页面。返回的是样例机制上的结构匹配结果。
- **P2 匹配**：P0 卡 T1–T5 已完成。进度、消融数字和阻塞见 [docs/state/p2.md](docs/state/p2.md)。真实机制库等 P1-T4。
- **P1 数据**：见 `src/conceptbridge/ingest/README.md`、`src/conceptbridge/extract/README.md`。

---

## 四个人各自的第一件事

| 人 | 角色 | 第一件事 |
|---|---|---|
| P1 | 数据与抽取 | 读 `ingest/README.md`，跑 P1-T1，先把 200 篇抓下来 |
| P2 | 图谱与匹配 | P0（T1–T5）已合入 `main`。详情见 [docs/state/p2.md](docs/state/p2.md) |
| P3 | 平台与集成 | 骨架已就绪；做 P3-T5 编排 + P3-T6 离线演示 |
| P4 | 前端与可视化 | 建 `web/`，MSW 按 `contracts/openapi.yaml` 造假，先出结果页 |

任务卡与验收标准见 [AGENTS.md](AGENTS.md) §11。

---

## 目录

```
src/conceptbridge/
  common/   配置、Pydantic 契约、LLM 网关、日志、错误码   (P3 独占)
  ingest/   OpenAlex 抓取与清洗                          (P1)
  extract/  机制四元组抽取、prompt、归一                  (P1)
  graph/    异构图谱、向量索引、持久化                    (P2)
  match/    候选生成、结构打分、反琐碎、重排              (P2)
  api/      路由、编排、降级                             (P3)
contracts/  openapi.yaml + json schema（由代码生成，勿手改）
fixtures/   迷你数据 + 合法样例（CI 与前端 mock 用）
eval/       金标准与消融报告                            (P2)
docs/       STATE.md 交接板 / 阻塞 / 技术债 / RFC
```
