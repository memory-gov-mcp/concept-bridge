# ingest — 采集层（Owner: P1）

## 只做这些

- OpenAlex `works` 接口分页抓取，`abstract_inverted_index` 还原成连续文本。
- 按 `primary_topic.domain` / `field` 打领域标签（后续 P2 用它算领域距离）。
- 去重（按 `paper_id`）、断点续抓、失败记录。
- 产出 `data/raw/papers.jsonl` + `manifest.json`。

## 不做

- 不抽机制（那是 `extract/`）。
- 不建图、不算向量（那是 `graph/`）。
- 不解析 PDF（P1-T7 可选，默认只吃摘要）。

## 输出格式（每行一个 JSON）

```json
{"paper_id":"W4382917001","title":"...","abstract":"...","year":2024,
 "domain":"materials_science","field":"Physical Sciences","cited_by":37,"doi":"..."}
```

## 命令

```bash
uv run python -m conceptbridge.ingest.cli --limit 1500
```

## 验收（P1-T1）

条数 ≥1500、`abstract` 非空率 ≥90%、`domain` 缺失率 <5%，且单测用录制响应、不联网。

## 边界

只写 `src/conceptbridge/ingest/**`、`tests/ingest/**`、`fixtures/**`。
`common/schemas.py` 只读，缺字段走 RFC。
