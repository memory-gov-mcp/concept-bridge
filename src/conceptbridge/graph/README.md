# graph — 异构图谱（Owner: P2）

## 图的形状（冻结）

- **节点 = 概念**（`GraphNode`）：`id / label / domain / type`。
- **边 = 机制**（`GraphEdge`）：`source=subject.concept_id`、`target=object.concept_id`、`action_class`。
- 领域标签来自论文的 `domain` 字段，别自己造。

## 已交付接口

```python
class GraphStore:
    @classmethod
    def from_mechanisms(cls, mechanisms: list[MechanismUnit], *, version: str = "g-local") -> "GraphStore": ...
    def save(self, directory: Path) -> None: ...
    @classmethod
    def load(cls, path: Path) -> "GraphStore": ...
    def subgraph(self, concept_id: str, hops: int = 2) -> Subgraph: ...
    def mechanisms_for(self, concept_ids: set[str]) -> list[MechanismUnit]: ...
    def all_mechanisms(self) -> list[MechanismUnit]: ...
```

`load()` 只读磁盘上的 pickle 与 npy，不重建向量。500 条机制建图与加载的实测数字在 `docs/state/p2.md`。

`/api/v1/graph/subgraph` 仍读样例 JSON。把 HTTP 接到 `GraphStore.subgraph` 属于 P3。

## 持久化

`save(directory)` 在该目录写下 `graph.pkl`、`mechanisms.jsonl`、`embeddings.npy`、`manifest.json`。
`manifest.json` 含 `git_sha`、`mechanism_count`、`node_count`、`graph_version`、`created_at`。
约定目录名是 `data/index/g-YYYYMMDD-N/`。`data/` 不入库。

`match.pipeline.load_corpus()` 若发现 `data/index/` 下带 `graph.pkl` 的快照，用最新一份；否则用 fixture。

## 向量

默认是 `hash_embed`：特征哈希、L2 归一化、`float32`。单测和 CI 走这条路径，不下载模型。
语义分因此不能当成 `intfloat/multilingual-e5-large` 的结果。
不要引入 sentence-transformers 或 torch。

## 动作词典

`classify_action(verb)` 覆盖 12 类。未命中返回 `None`。概念名如「膜」「细胞膜」不会被当成动词。本模块不调用 LLM。

## 验收（P2-T1）

500 条机制建图 <10s；`GraphStore.load()` <2s；`subgraph()` 有单测。证据见 `docs/state/p2.md`。

## 边界

只写 `src/conceptbridge/graph/**`、`tests/graph/**`；`eval/**` 同属 P2。
