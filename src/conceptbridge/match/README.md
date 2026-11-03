# match — 结构匹配（Owner: P2）

## 入口（签名冻结，改动需 RFC）

```python
# src/conceptbridge/match/pipeline.py
async def run_bridge(
    query: str,
    source_domain: str | None = None,
    top_k: int = 5,
    exclude_domains: list[str] | None = None,
) -> BridgeResult: ...
```

`api/services/bridge_service.py` 能导入这个函数时，非 `DEMO_MODE` 的 `/api/v1/bridge` 就调用它，成功时 `meta.stub=false`。

`load_corpus()` 的语料：`data/index/` 里有带 `graph.pkl` 的快照就用最新一份，否则用 `fixtures/bridge.sample.json`。

```bash
uv run python -m conceptbridge.match.cli --query "锂枝晶抑制" --fixtures
```

`--fixtures` 只读样例，不碰 `data/index`。输出要能过 `BridgeResult` 校验。

## 打分（公式见 AGENTS.md §5.3，权重放 `config.py`）

```
struct_sim  = 0.30*role_type + 0.25*action_class + 0.15*causality
            + 0.15*condition_jaccard + 0.15*polarity
final = 0.45*struct_sim + 0.30*sem_sim + 0.25*domain_dist - 0.35*triviality
```

`final` 夹到 `[0, 1]`。语义相似度用哈希向量的内积，不是 e5。

两条已经在结果里的约束：

1. **反琐碎惩罚**。泛化表面词「影响 / 促进 / 相关 / 参与」以及空条件会把 `triviality` 打成 1。12 类里的 `promote` 本身不因此被判死。
2. **`alignment`**。规则解释为每条桥生成 subject、object 两条角色对齐。前端靠它画高亮。引用的 `span` 等于目标机制的 `evidence.span`。LLM 缓存命中时只替换假设和差异，不改引用。

## 降级路径

`run_bridge` 用 `settings.bridge_timeout_s`（默认 15 秒）。预算用尽时停在下一条桥之前，保留已经生成的桥，`meta.degraded=true`，`meta.stub=false`。这些桥的引用仍是目标机制的 `evidence.span`。

内部异常不向外抛。返回空桥的合法 `BridgeResult`，`degraded=true`，`stub=false`，源域记为 `unknown`。不把 fixture 样例桥填进来。API 若仍收到异常，会再退回 fixture，那是第二层。

## 多步子图

`match_subgraphs` 在概念节点不超过 8 个时用 VF2；结构对不上时用节点类型和边动作的排序差当作近似编辑距离，不跑精确 GED。任一侧超过 8 个节点就退回两条列表里的第一条机制，`degraded=True`，`mode="triple"`。在线 `run_bridge` 仍是单条机制打分。

## 验收（P2-T3）

上面的 CLI 对「锂枝晶抑制」返回跨域桥，`stub=false`。证据见 `docs/state/p2.md`。

## 边界

只写 `src/conceptbridge/match/**`、`tests/match/**`、`eval/**`。
