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

## 降级路径（现状）

成功路径上 `meta.degraded` 固定为 false。匹配内部若抛异常，异常会冒到 API；API 退回 fixture，并把 `degraded` 标成 true、`stub` 标成 true。超时预算 `settings.bridge_timeout_s`（15 秒）尚未在 `run_bridge` 里使用。

## 验收（P2-T3）

上面的 CLI 对「锂枝晶抑制」返回跨域桥，`stub=false`。证据见 `docs/state/p2.md`。

## 边界

只写 `src/conceptbridge/match/**`、`tests/match/**`、`eval/**`。
