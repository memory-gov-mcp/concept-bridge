# match — 结构匹配（Owner: P2）

## 必须实现的唯一入口

```python
# src/conceptbridge/match/pipeline.py
async def run_bridge(
    query: str,
    source_domain: str | None = None,
    top_k: int = 5,
    exclude_domains: list[str] | None = None,
) -> BridgeResult: ...
```

**这个文件一存在，P3 的 API 就自动从 fixture 切到真实实现**（见 `api/services/bridge_service.py`）。
签名已冻结，改动需 RFC。

## 打分（公式见 AGENTS.md §5.3，权重放 `config.py`）

```
struct_sim  = 0.30*role_type + 0.25*action_class + 0.15*causality
            + 0.15*condition_jaccard + 0.15*polarity
final = 0.45*struct_sim + 0.30*sem_sim + 0.25*domain_dist - 0.35*triviality
```

两个必须有的东西：

1. **反琐碎惩罚**。没有它，LLM 会给"都有能量输入"这类废话，P@5 直接被垃圾占满。
2. **`alignment`**。前端靠它画对齐高亮，是"3 秒 wow"的数据基础。没有 alignment，桥动画画不出来。

## 降级路径

任何内部异常都不许冒到 API 层。超时 → 返回 `degraded=True` 的少结果，而不是 500。

## 验收（P2-T3）

```bash
uv run python -m conceptbridge.match.cli --query "锂枝晶抑制" --fixtures
```
输出能过 `BridgeResult` 校验；P95 <1500ms（500 机制）。

## 边界

只写 `src/conceptbridge/match/**`、`tests/match/**`、`eval/**`。
