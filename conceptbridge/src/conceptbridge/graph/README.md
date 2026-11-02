# graph — 异构图谱（Owner: P2）

## 图的形状（冻结）

- **节点 = 概念**（`GraphNode`）：`id / label / domain / type`。
- **边 = 机制**（`GraphEdge`）：`source=subject.concept_id`、`target=object.concept_id`、`action_class`。
- 领域标签来自 `papers.jsonl` 的 `domain` 字段，别自己造。

## 对外接口（P3 的 API 只认这三个）

```python
class GraphStore:
    @classmethod
    def load(cls, path: Path) -> "GraphStore": ...
    def subgraph(self, concept_id: str, hops: int = 2) -> Subgraph: ...
    def mechanisms_for(self, concept_ids: set[str]) -> list[MechanismUnit]: ...
    def all_mechanisms(self) -> list[MechanismUnit]: ...
```

`load()` 必须 <2s（答辩现场冷启动就靠它）。

## 持久化

`data/index/g-YYYYMMDD-N/` 下放 `graph.pkl`、`mechanisms.jsonl`、`embeddings.npy`、`manifest.json`。
`manifest.json` 必须含 `git_sha` 与条数，答辩时指着它说"可复现"。

## 向量

用 `fastembed`（不是 sentence-transformers——不要引入 torch，2GB 下载会毁掉 Day1）。
模型来自 `settings.embed_model`（默认 `intfloat/multilingual-e5-large`）。归一化后存 `float32`。

## 验收（P2-T1）

500 条机制建图 <10s；`GraphStore.load()` <2s；`subgraph()` 有单测。

## 边界

只写 `src/conceptbridge/graph/**`、`tests/graph/**`；`eval/**` 同属 P2。
