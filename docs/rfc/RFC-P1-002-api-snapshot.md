# RFC-P1-002 API 统一读取机制快照

提出人 P1，2026-11-03，状态为待 P3 评审。
离线联调使用隔离的八篇合成数据，经 P1 抽取导出与 install-index 后调用真实 API。
bridge 返回 200、两条桥、stub=false、degraded=false，graph_version 与导出快照一致。
新机制详情与新概念子图均返回 404，health 的 graph_version 仍是固定值。
建议由 P3 让 mechanisms、graph/subgraph、health 复用与 bridge 相同的 GraphStore 快照来源。
既有响应契约可保持现有字段，原文展示通过 paper_id 回查同批论文记录。
验收需覆盖 bridge 返回 ID 的详情可访问、节点邻域可访问、所有端点版本一致。

## 结论（2026-11-04，P3）

已采纳。实现方式：新增 `src/conceptbridge/api/services/snapshot.py` 作为唯一快照来源，
`mechanisms`、`graph/subgraph`、`health` 三个路由改为向它取数，与 `match.pipeline.load_corpus()`
的解析顺序一致（`data/index/g-*` 最新快照优先，无则退回 fixture）。

三项验收由 `tests/api/test_graph_endpoints.py` 覆盖：bridge 返回的机制 ID 详情 200、
涉及概念邻域 200、`/health.graph_version` 与 `/bridge.meta.graph_version` 相等。
契约字段未变，`task contract` 无漂移。

附带修正：`/bridge` 的 fixture 降级路径原先报 fixture JSON 里写死的 `g-20261102-0`，
现改为取快照版本，避免同页两个版本号。`graph` 依赖改为惰性导入，
没有 numpy / networkx 时退化为 fixture 只读，不影响 API 启动。
真实索引快照路径需在 CI（`uv sync --extra analyze`）下验证。

