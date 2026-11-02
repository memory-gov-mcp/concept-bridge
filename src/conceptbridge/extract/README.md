# extract — 机制抽取（Owner: P1）

## 只做这些

- 8 篇摘要一批送 LLM，要求返回严格 JSON。
- 用 `MechanismUnit.model_validate()` 校验；失败重试 2 次，再失败落 `data/normalized/failed_papers.jsonl`。
- 概念归一：字符串规范化 + 别名合并 + 同名跨域拆分。
- 产出 `data/normalized/mechanisms.jsonl` 与 `concepts.parquet`。

## 三条硬性提醒

1. **`signature` 必须从三元组推导出来，不许让模型自由发挥。**
   `MechanismUnit` 里有校验器强制 `signature.subject_type == subject.type`，
   与其让模型猜，不如用代码填。
2. **`evidence.char_start/char_end` 必须真的能在摘要里切出 `span`。**
   抽取后立刻自检 `abstract[char_start:char_end] == span`，不等的样本直接判失败重抽。
3. **`conditions` 里的条件标签要归一**（`concentration_gradient` 不要写成十种说法），
   否则 P2 的结构打分里 `condition_jaccard` 恒为 0。

## Prompt 版本化

`prompts/v1/system.md`、`prompts/v1/user.md`。改了 prompt 就新建 `v2/`，不要原地改——
否则昨天的抽取结果和今天的不可比，消融表会变成谎言。

## 命令

```bash
uv run python -m conceptbridge.extract.cli --limit 500
```

## 验收（P1-T2）

500 篇 → ≥1200 条机制；schema 通过率 ≥98%；人工抽检 30 条正确率 ≥80%（把结论写进 `docs/STATE.md`）。

## 边界

只写 `src/conceptbridge/extract/**`、`tests/extract/**`、`fixtures/**`。
