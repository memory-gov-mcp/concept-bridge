# RFC-P1-001 公共 LLM 网关保留实际用量

提出人 P1，2026-11-03，状态为待 P3 评审。
用户要求先试跑 8 篇，核算用量后再决定扩量。
当前 `_post_with_retry()` 丢弃供应商 usage，`_usage.json` 仅记录字符数。
建议由 P3 在 common/llm.py 持久化响应中的 prompt_tokens、completion_tokens、total_tokens、model。
计数缺失时标为 unknown，缓存命中记新增用量为零，避免用字符数冒充 token。
保留 complete_json() 返回正文的现有接口，增加独立的用量记录供 P1 读取。
涉及文件为 P3 独占 common/llm.py，P1 本次仅提交设计。
