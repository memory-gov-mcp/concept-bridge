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

## P1-T1 实现与 P2 对接

`--limit` 是整库目标条数。默认检索六组固定主题，1500 篇时每组 250 篇。
已有数据超过目标时保留已有记录。后续调大目标会利用 checkpoint 中的未消费记录继续采集。
`DATA_DIR` 与 `OPENALEX_MAILTO` 通过现有 `common/config.py` 读取。

- 领域由 `primary_topic.field.id` 映射为 P2 已使用的 `materials_science`、`chemistry`、
  `biology`、`medicine`、`computer_science`、`physics`。`field` 保留上游 field 名称，
  完整的 `primary_topic` 保留上游 topic/subfield/field/domain 层级。
- 额外的 `openalex_url` 和 `source_query` 用于溯源。摘要保持按倒排位置还原的文本，
  后续抽取的字符偏移以此文本为准。缺失位置、重复位置和无摘要论文记录为失败并跳过。
- 当前使用固定每页 200 条的普通分页。2026-11-03 实测普通第二页可用，cursor 第二页返回
  HTTP 401，要求 API key。普通分页最多扫描每个查询的前 10000 条，超限明确报错。
- `checkpoint.json` 原子保存已接收论文、下一页与当前页剩余记录。重复 paper ID 去重。
  中断后重复同一命令即可恢复。`papers.jsonl` 与 `manifest.json` 可从 checkpoint 重建。
- SQLite 文件锁拒绝同一数据目录的并发采集，进程退出后自动释放。
- `failed_records.jsonl` 同时保留被拒论文和请求失败历史，`manifest.json` 记录数量、
  领域分布、摘要比例、文件 SHA-256 及 UTC 生成时间。检索耗尽而目标未达成时退出码为 1。
- `DEMO_MODE=1` 只使用已有 checkpoint。缓存不足会报错，已有完整语料可离线重跑。

P2 的建图输入仍是后续 T2/T4 交付的 `MechanismUnit`。
当前采集产物为这些机制提供 `paper_id`、领域及可回查的原文。

测试中的 `tests/ingest/openalex_works.json` 是 2026-11-03 从 OpenAlex 录制的三条响应，
分别对应材料、生物与计算机查询，仅保留采集所需字段。所有测试使用 MockTransport。
