# P1 剩余任务实现设计

本设计覆盖 T2–T6，承接已完成的 T1。用户已要求在本次工作中继续完成 P1，按任务分步实现和验证。
代码范围为 P1 的 ingest、extract、tests/ingest、tests/extract、fixtures 与 scripts/ingest_*.py。

## 数据与执行流程

论文从 `settings.resolved_data_dir/raw/papers.jsonl` 读取，按领域轮流取样，领域内按 paper_id 排序。
CLI 默认处理 8 篇、关闭自动重抽，每批最多 8 篇。同一 paper_id 重复出现直接报错，避免覆盖不同原文。
用户于本次工作确认先试跑 8 篇，核算用量后再决定扩量。500 篇是真实验收门槛，尚未授权执行。
摘要是证据偏移的唯一基准，传给模型后不改写。

模型响应为 `papers` 数组，每项包含 `paper_id` 与 `mechanisms`。机制草稿包含 subject、action、
object、conditions、result、causality、evidence、confidence。subject/object 只含 surface 和 type。
代码生成 concept_id、机制 ID、结构签名、证据偏移、domain 与 extractor_version。
每篇需 1–5 条独立机制，无充分机制证据时允许返回空数组并记录无有效机制的失败。

因果类型由模型判断并受枚举约束，其余签名字段从校验后的主客体、动作和条件推导。
首版只输出二元机制，arity=2，主客体归一后相同则拒绝。动作优先使用 P2 的 classify_action，
词典未命中时采用草稿中的合法枚举。surface 必须保持论文中的概念表述。

证据片段必须在摘要内精确出现。出现一次时由代码定位，重复出现时要求模型提供可验证的
char_start。char_end 由片段长度计算。偏移按 Python Unicode 字符计算，P4 使用 UTF-16
索引时需要转换。证据检查与 MechanismUnit 校验均通过后才入库。

## 归一与身份

使用 Unicode NFKC、空白、连字符和括号规范化。英文普通词归一大小写，缩写和化学式保留大小写。
复数只处理明确词表，避免任意删除末尾 s。别名按领域和概念类型限定，膜与细胞膜保持独立。
concept_id 基于领域、类型与规范名的 SHA-256。condition_keys 使用独立条件别名表，去重排序。
不认识的条件保留规范化标签，规则版本变更会改变抽取任务键。

`concepts.parquet` 包含 concept_id、canonical_name、domain、type、surfaces。
报告同时记录归一前不同 surface 数和归一后概念数。人工抽检的 20 组映射单独导出供审核。

## 缓存、重试与恢复

复用 common/llm.py 的 JSON 网关。抽取层限制同时一个请求，CLI 用 SQLite 锁拒绝同目录并发写。
网关缓存按提供商地址隔离。任务缓存键覆盖论文内容、模型、提供商、prompt 内容和归一版本。
成功任务以原子文件保存，重跑可跳过成功论文，即使批次边界变化也不重复调用模型。

每批先请求一次，显式启用 --retries 2 时只对缺失或无效的论文最多重抽两次。校验错误加入重抽提示，避免重复命中原错误
响应。重复/未知 paper_id 视为批次结构错误。传输错误由公共网关重试，配置错误和不可用错误向上
报告并保留已完成任务。最终失败写 failed_papers.jsonl，可通过 --retry-failed 显式重试。
显式重试携带递增 generation，避免重读旧失败响应。公共网关最多进行三次传输尝试，试跑预检查
将其上限单列。零机制重抽的试跑最多一批请求，对应最多三次底层传输尝试。

使用固定模型参数，prompt 变更新增版本目录。损坏缓存明确失败，保留现场。用量报告区分任务命中、
网关缓存命中和网关调用。公共网关只提供字符计数，无法据此宣称精确 token 或费用。
上游处理成功但客户端超时造成的计费不确定性依赖供应商幂等能力。

## 产物与可复现清单

每次选定语料形成独立运行目录，完整写好 mechanisms.jsonl、concepts.parquet、failed_papers.jsonl、
审核样本与 manifest.json 后，原子更新 normalized/current.json。供旧消费者读取的
normalized/mechanisms.jsonl 和 concepts.parquet 是最新完整运行的导出副本。
失败的配置检查保留上一份完整导出。单篇失败会明确进入报告，不伪造机制补足数量。

manifest 记录输入/输出哈希、模型、prompt 哈希、抽取器/归一版本、Git SHA、UTC 时间、选中论文数、
成功/失败数、首次及最终论文校验通过率、机制数、缓存用量和归一统计。人工准确率默认待审核。
500 篇产生至少 1200 条、通过率至少 98%、30 条人工审核正确率至少 80% 才能宣布 T2 完成。

## P2 交付接口

T4 从完整运行中确定性选择 200 篇有成功机制的论文，覆盖六领域，再取其 500 条机制，
保证每篇至少一条。不足时明确报错，保持旧 fixtures。
先在临时目录生成并验证所有文件、文件总和小于 5MB，再发布。
输出 papers.min.jsonl、mechanisms.min.jsonl、graph.min.pkl 与 fixtures/graph.min/ 快照目录。
根目录 graph.min.pkl 与快照 graph.pkl 内容相同，用于符合原任务卡的文件名要求。
GraphStore.load 接收 fixtures/graph.min 目录，配套 mechanisms.jsonl、embeddings.npy、manifest.json。
完整快照通过现有 GraphStore.from_mechanisms/save 生成。当前嵌入为 P2 的 hash_embed，报告标注。
8 篇试跑可显式设置 --paper-count 8 --mechanism-count 8，输出到独立试跑目录。

P1 的脚本提供显式 --install-index 开关，将已验证快照复制到 data/index/g-YYYYMMDD-N/，供现有
match.load_corpus 读取。成功后发布 graph.pkl，避免匹配器读到不完整快照。
P2/P3 的 API 详情和子图读取入口仍需各自 owner 对接。bridge.sample.json 保留现有用途。

## T7 可选全文补充设计

必做链路通过后再实现。输入沿用 paper_id、doi 与开放获取链接，优先使用 PMC XML 或 arXiv
可访问正文。下载与解析分开缓存，保留来源 URL、许可证、内容哈希和 section 字符偏移。
arXiv 请求间隔至少 3 秒，禁止重新分发原始全文。200 篇正文验收报告单列失败率。
当前依赖缺少 PDF 解析器，需要先由 P3 评审依赖 RFC。全文证据须携带文本版本，不能复用摘要偏移。

## 验证

离线测试覆盖坏 JSON、重复论文、模型漏返、签名推导、错误/重复证据、条件归一、跨域同名、
缓存重放、修复请求、失败恢复、迷你集体积、P2 GraphStore 加载与匹配调用。
运行 task check、task e2e 和 extract/ingest 覆盖率检查。真实抽取与人工审核单独记录证据。
