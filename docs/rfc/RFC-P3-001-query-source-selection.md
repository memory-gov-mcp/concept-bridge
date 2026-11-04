# RFC-P3-001 查询 → 源机制定位的修复

提出人 P3，2026-11-04。**涉及 P2 的文件**：`src/conceptbridge/match/candidate.py`、`tests/match/*`。
P2 请复核；如需回退，单独 revert 本提交即可，不牵连其它改动。

## 缺陷（实测）

`select_sources` 用"查询里的字符是否出现在机制文本中"计分：

```python
sum(1 for char in query if not char.isspace() and char in text)
```

三种失效方式：

1. **英文语料 + 中文查询**：汉字一个都不出现在英文摘要里 → 零命中 → 落到兜底
   `return by_domain["materials_science"]`，把整个领域当源（92 条），**查询被完全忽略**。
2. **英文查询**：单个字母 `p/r/o/t/e/n` 几乎每个文本里都有 → 大量命中 →
   `dendrite` 与 `protein folding` 返回**同一个源机制**。
3. **取分规则过宽**：`score > 0` 的机制全部收进结果，一个弱命中就能把整个领域拖进来。

后果：任何输入都收敛到同一条桥。**评测 P@5=1.0 掩盖了它**——评测显式传 `source_domain`，
走的是 `if source_domain: return 该领域全部` 分支，从未验证"查询 → 选源"。

## 修复

1. ASCII 查询按**整词**匹配，并用 IDF 加权压掉 `li` / `inhibit` 这类到处都有的泛词。
2. 中文查询经术语表映射为英文**名词**（`锂枝晶→dendrite`、`催化剂→catalyst`…），
   刻意不收「抑制/促进」这类泛化动作词——fixture 里生物的动词就是 `suppress`，收进来会把生物误判成源。
3. 词面零命中且查询含中文 → 回退中文字符二元组，保证中文语料（fixture）仍能解析。
4. 选源改为**只取最高分档**，同分时取数量最多的领域。

## 验证

- `tests/match` 7 条、`tests/api + contract + match + graph` 60 条、e2e 3 条全过；ruff / mypy 通过。
- 真实 500 条语料（`fixtures/mini200` → `data/index/g-mini200`）实测：

| 查询 | 源机制数 | 领域 |
|---|---|---|
| `dendrite` | 9 | materials_science |
| `protein folding` | 2 | biology |
| `锂枝晶抑制` | 3 | materials_science |
| `热失控` | 3 | materials_science |
| `催化剂失活` | 2 | materials_science |

修复前这五个查询全部返回 92 条且结果相同。

## 附带修复

`tests/api`、`tests/match` 增加 `DATA_DIR` 隔离夹具。原先这两个目录的用例断言依赖
"本机没装 `data/index`"，装了索引就会红——CI 与实际环境不一致的经典陷阱。

## 遗留

- 无词形还原：查 `immunity` 命不中 `immune`，仍走兜底。
- 术语表是 demo 级。真正的跨语言检索应改用多语种向量（`fastembed` 已装，
  但模型需一次下载；当前 TLS 不通，等网络恢复）。
