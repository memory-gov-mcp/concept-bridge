# RFC-P1-002 API 统一读取机制快照

提出人 P1，2026-11-03，状态为待 P3 评审。
离线联调使用隔离的八篇合成数据，经 P1 抽取导出与 install-index 后调用真实 API。
bridge 返回 200、两条桥、stub=false、degraded=false，graph_version 与导出快照一致。
新机制详情与新概念子图均返回 404，health 的 graph_version 仍是固定值。
建议由 P3 让 mechanisms、graph/subgraph、health 复用与 bridge 相同的 GraphStore 快照来源。
既有响应契约可保持现有字段，原文展示通过 paper_id 回查同批论文记录。
验收需覆盖 bridge 返回 ID 的详情可访问、节点邻域可访问、所有端点版本一致。
