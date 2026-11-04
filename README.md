# ConceptBridge 概念桥

跨学科结构类比检索：输入领域 A 的一个难题，从领域 B 的文献里检索**结构相似**的机制，
输出可迁移假设、差异说明与原文出处。

> 一句话：现在的跨学科检索找的是"同一个词"，我们找的是"同一个道理"。

赛题归属：高级组主题 3「跨域知识探索 / 跨学科知识发现」。
**完整规范、契约、分工、任务卡全部在 [AGENTS.md](AGENTS.md)，开工前必读。**

---

## 30 秒跑起来

```bash
uv sync --extra analyze             # 装依赖；dev 工具组由 uv sync 默认安装
uv run task contract                  # 生成 contracts/
uv run task check                     # 必须绿
uv run task dev                       # http://127.0.0.1:8000/docs
```

Windows 与 Linux 都用 `uv run task <cmd>`。装了 GNU make 时，`make <cmd>` 与之等价。CI 在 Ubuntu 和 Windows 上跑 `check` 与 `e2e`。

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
- **P2 匹配**：P0 卡 T1–T5 已完成。用法见下方，进度见 [docs/state/p2.md](docs/state/p2.md)。真实机制库等 P1-T4。
- **P1 数据**：见 `src/conceptbridge/ingest/README.md`、`src/conceptbridge/extract/README.md`。

### P2 现在怎么用

未开 `DEMO_MODE` 时，`POST /api/v1/bridge` 调用 `run_bridge`，`meta.stub` 为 false。没有 `data/index/*/graph.pkl` 时，语料是 `fixtures/bridge.sample.json`。`DEMO_MODE=1` 只读这份样例。

每条桥的 `alignment` 给前端做对齐高亮。引用片段是目标机制的 `evidence.span`。

```bash
uv run python -m conceptbridge.match.cli --query "锂枝晶抑制" --fixtures
```

接口说明：[src/conceptbridge/graph/README.md](src/conceptbridge/graph/README.md)、[src/conceptbridge/match/README.md](src/conceptbridge/match/README.md)。进度与消融数字：[docs/state/p2.md](docs/state/p2.md)。

---

## 四个人各自的第一件事

| 人 | 角色 | 第一件事 |
|---|---|---|
| P1 | 数据与抽取 | 读 `ingest/README.md`，跑 P1-T1，先把 200 篇抓下来 |
| P2 | 图谱与匹配 | 读 [graph/README.md](src/conceptbridge/graph/README.md) 与 [match/README.md](src/conceptbridge/match/README.md)。试跑：`uv run python -m conceptbridge.match.cli --query "锂枝晶抑制" --fixtures` |
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

## 不装前端也能看界面

`web/node_modules` 缺失时 Vite 起不来，而后端自带一个**自包含**的极简界面
（纯 HTML + 原生 JS，零外部资源，10.8 KB）：

```powershell
uv run task demo
# 浏览器打开 http://127.0.0.1:8000/
```

它直接调 `/api/v1/health` 与 `/api/v1/bridge`，显示健康横幅、双域对照、桥分数、
可迁移假设、差异与原文引用。断网、没装 Node、CI 缓存失效时都能用。

