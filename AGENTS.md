# AGENTS.md — ConceptBridge 概念桥

> 四人并行、每人一个编码 Agent。本文件是**唯一权威源**：项目定义、契约、分工、约束、任务卡都在这。
> 版本 v1.0 ｜ 冻结于 2026-11-02 23:00 ｜ 维护人：P3 ｜ **只有 P3 或人类负责人可改本文件**
> 赛程：提交截止 11-04 24:00（周四 8:00 起互评），决赛答辩 11-06。
> 可用开发时间 ≈ 2.2 天。所有排期与取舍以这个前提为准。

---

## 0. 给 Agent 的 60 秒速览

1. **只写你 owner 拥有的路径**，其余一律只读。越界改动会被 revert，不加讨论。
2. 开工顺序：本文件 §3 项目定义 → §8 数据契约 → §10 所有权 → §11 你的任务卡。**没有任务卡的任务不要做。**
3. 提交前 `uv run task check` 必须全绿。新逻辑必须带测试，测试禁止联网。
4. 要改契约、加依赖、动 `pyproject.toml` → 写 RFC（§13.4），等 owner 确认。**永远不要自己改。**
5. 任务完成的唯一标准：`uv run task check` 绿 + 一条可复现命令和它的输出证据写进 `docs/state/p<N>.md`。「已完成」三个字不算交付。

---

## 1. 这份文件怎么用

- 人看 §3–§5 就够了（做什么、值多少分）。
- **Agent 每次新会话必须完整读本文件**，再读自己 owner 目录下的 `README.md`，然后只领一张任务卡。
- 一个任务卡 = 一个会话。做完提交、更新 `docs/state/p<N>.md`，**开新会话做下一张**，不要在一个会话里连做三张卡（上下文污染是并行开发最大的隐性 bug 源）。
- 本文件若继续膨胀，按 §19 拆到 `docs/`，AGENTS.md 只留入口和硬约束。

---

## 2. 一句话与赛题自证

**一句话**：输入领域 A 的一个具体难题，从领域 B 的文献里检索**结构相似**的机制，输出可迁移假设、差异说明与原文出处。

**赛题自证（必须显式命中，否则有 20 分跑题风险）**：本项目归属高级组主题 3「跨域知识探索」下的「**跨学科知识发现**」。提交材料的标题、摘要、PPT 首页**必须**同时出现「跨学科」「知识发现」或「跨域知识」这三组词中的至少两组。不要只写「科研助手」「文献工具」——那会被判成主题 2。

**不是**：论文摘要器、通用 RAG 问答、文献管理工具、知识图谱可视化玩具。

**价值主张（答辩第一句）**：现在的跨学科检索找的是"同一个词"，我们要找的是"同一个道理"。

---

## 3. 目标与非目标

### 3.1 必须做到（P0，缺一不可）

| # | P0 能力 | 判定标准 |
|---|---|---|
| 1 | 真实文献入库 | ≥1500 篇 OpenAlex 论文，含摘要、年份、领域标签，落 `data/raw/` |
| 2 | 机制抽取 | 每篇论文抽 1–5 个「机制四元组」，schema 通过率 ≥98% |
| 3 | 异构图谱 | 概念节点 + 机制边，可持久化、可秒级加载、可查 N 跳子图 |
| 4 | 结构匹配 | 一次查询返回 top-5 跨域桥，单次 P95 ≤ 4s |
| 5 | 可解释输出 | 每个桥带「可迁移假设 + 差异说明 + 原文引用片段」 |
| 6 | 可视化 | 双域图谱 + 桥接动画 + 对齐高亮，3 秒内看懂 |
| 7 | 评测 | ≥30 对金标准，报 P@5 / MRR + 消融表 |
| 8 | 离线可演示 | `uv run task demo` 断网可完整跑通，不依赖现场网络 |

### 3.2 明确不做（Non-goals）

- 用户系统、登录、收藏、付费、移动端。
- 全学科覆盖：只做 **材料/化学 → 生物/医学** 与 **算法/物理 → 生物** 两组跨域样板。
- 模型训练或微调：本赛制下性价比极低，且无法形成可解释的技术叙事。
- PDF 全文解析（默认只用 OpenAlex 摘要；`fulltext` 是 P1）。
- 多轮对话式交互：一次查询一次结果，把"能演"做到极致。
- 通用化：不追求别人换个领域也能用，追求**评委现场看到的 3 个例子无法反驳**。

---

## 4. 评分对齐（每一行都要能指出证据在哪）

| 维度 | 权重 | 评委实际在找什么 | 我们的工程动作 | 证据位置 |
|---|---|---|---|---|
| Tech | 40%/25% | 功能完整、算法正确、不崩 | 契约测试 + 离线模式 + 消融证明结构打分有增益 | `eval/reports/latest.md` |
| Idea | 30%/25% | 选题新、且说得清 | "结构相似而非文字相似"一句话 + 反琐碎惩罚 | 答辩第 2 页 |
| UX | 30%/25% | 易用、好看、有交互设计 | 双域图 + 桥动画 + 假设卡分层 | `web/` |
| Show | 25% | PPT、时间、流畅 | 3 分钟固定脚本 + 两次彩排 + 双备份 | `docs/demo/script.md` |

三条由此推出的铁律：

1. **技术难度只"兼顾"** → 不追算法复杂度，追"讲得清的一个技术点 + 跑得稳"。
2. **创新分是相对分** → 必须能在 3 秒内被看出和"又一个 RAG"不一样，这靠**桥动画**，不靠论文。
3. **互评是同学视角** → 首屏必须无教学成本；不要让评委先读 200 字说明才明白你在做什么。

---

## 5. 核心设计（技术叙事，答辩就讲这一页）

### 5.1 数据流

```
OpenAlex API
    │  ingest (P1)
    ▼
data/raw/papers.jsonl ──► extract (P1, LLM + JSON Schema 校验)
    │                            │
    │                            ▼
    │                    data/normalized/mechanisms.jsonl
    │                            │
    │                       normalize (P1: 概念归一 + 动作分类)
    │                            ▼
    ▼                    data/normalized/concepts.parquet
graph build (P2) ──► data/index/graph.pkl + faiss.index + manifest.json
                            │
query ──► api (P3) ──► match (P2: 候选 → 结构打分 → 重排) ──► BridgeResult
                            │
                            ▼
                    web (P4) 双域图谱 / 桥动画 / 假设卡
```

### 5.2 为什么是"结构相似"

向量检索只能找到**用词相近**的段落。"细胞膜的选择性通透"和"SEI 膜的离子筛分"字面几乎没有交集，但机制同构：**一个选择性屏障在浓度梯度下放行特定离子、阻挡其余**。所以相似度必须建在**机制的结构签名**上：

```python
class StructuralSignature(BaseModel):
    subject_type: ConceptType   # structure | process | substance | signal | state
    action_class: ActionClass   # 12 类，见下
    object_type: ConceptType
    causality: Literal["direct", "mediated", "feedback", "threshold"]
    polarity: Literal["promote", "inhibit", "neutral"]
    condition_count: int
    condition_keys: list[str]   # 归一后的条件标签，如 ["concentration_gradient"]
    arity: int                  # 机制涉及实体数 2..5
```

`ActionClass` 固定 12 类，**必须**枚举，不许自由发挥：
`inhibit | promote | transport | transform | recognize | amplify | stabilize | degrade | compete | isolate | trigger | regulate`

分类器用「规则词典 + LLM 兜底」：常见动词走词典（快、可解释），未命中才调 LLM 并写缓存。

### 5.3 打分公式（`src/conceptbridge/match/config.py`，P2 用评测调参）

```
struct_sim  = 0.30 * role_type_match        # 主客体类型是否同构
            + 0.25 * action_class_match     # 动作类别是否同类
            + 0.15 * causality_match
            + 0.15 * condition_jaccard
            + 0.15 * polarity_match

sem_sim     = cosine(embed(action + conditions + result))     # 软约束，防结构对上但语义荒谬

domain_dist = 领域距离 0..1    # 同 OpenAlex 顶层 field 记 0，跨 field 记 1，跨 domain 加权

triviality  = 惩罚项，满足任一即 +1：
              condition_count == 0
              arity < 2
              action_class 命中泛化词表（影响 / 促进 / 相关 / 参与）
              源与目标概念的名字或向量相似度 > 0.95（说明是同一领域换皮）

final = 0.45 * struct_sim + 0.30 * sem_sim + 0.25 * domain_dist - 0.35 * triviality
```

**消融就是把这行公式拆开跑**：`sem only` → `+struct` → `+domain` → `+rerank`。这是证明"我们不是套壳"的唯一硬证据，比任何 PPT 都有用。

### 5.4 两个必须写进代码的"反套壳"设计

1. **反琐碎惩罚（triviality）**：LLM 最容易给的跨域类比是"都有能量输入""都受环境影响"这类废话。没有这个惩罚项，P@5 会被垃圾结果占满，现场一问就露馅。
2. **每条结论必须挂 span**：`transferable_hypothesis` 和 `differences` 里引用的任何事实，都要能落到 `evidence.span`（论文原文片段 + 字符偏移）。前端点击引用必须高亮原文。**不许出现无出处的断言。**

---

## 6. 技术栈（锁定版本，升级需 RFC）

| 层 | 选型 | 理由 / 注意 |
|---|---|---|
| 运行时 | Python 3.11 + `uv` | 装依赖快，锁 `uv.lock` |
| Web 框架 | FastAPI 0.115 + uvicorn | 自动 OpenAPI，直接当契约源 |
| 校验 | Pydantic v2 | 契约即代码，导出 JSON Schema |
| HTTP | httpx + tenacity | 重试退避，OpenAlex 礼貌池 |
| LLM | OpenAI 兼容接口（DeepSeek 为主） | 统一走 `common/llm.py`，JSON mode |
| Embedding | `fastembed` + `intfloat/multilingual-e5-large` | **不要 sentence-transformers**：它拉 2GB torch，会毁掉 Day1 |
| 向量检索 | FAISS `IndexFlatIP`（归一化后内积） | 万级向量无需 ANN，简单可靠 |
| 图 | NetworkX + pickle/parquet 持久化 | 不引 Neo4j：省运维，演示更稳 |
| 关系存储 | SQLite + SQLAlchemy 2.0 | 单文件，随仓库快照走 |
| 前端 | Vite + React 18 + TypeScript | **不用 Next.js**：无 SSR 需求，构建更快，Agent 踩坑更少 |
| 样式 | Tailwind + shadcn/ui | 出图快，风格统一 |
| 图可视化 | Cytoscape.js | 力导向 + 自定义布局，双 cluster 可控 |
| 动效 | Framer Motion + 自绘 SVG 弧 | 桥动画的核心 |
| 测试 | pytest / vitest / MSW | 前端从 Day0 用 mock 独立跑 |
| 质量 | ruff + mypy（`common/` + `api/`）+ eslint | `uv run task check` |
| 部署 | 本地裸跑：`uv run task dev` / `task demo` | docker-compose **已推迟**——两天工期里多一个中间件就是多一个现场故障点 |

**禁止引入**：Neo4j、Kafka、Redis、Celery、LangChain、LlamaIndex、sentence-transformers / torch、pandas 之外的重型数据处理库。理由：两天工期，每个中间件都是一次现场故障机会。（确需引入走 RFC，P3 评估。）

---

## 7. 目录结构与所有权

```
conceptbridge/
├── AGENTS.md                    # P3
├── README.md                    # P3
├── Makefile                     # P3
├── pyproject.toml               # P3 独占（依赖变更在此）
├── docker-compose.yml           # P3（**已推迟**：本机无法验证容器，见 docs/state/p3.md 技术债）
├── .env.example                 # P3
├── contracts/                   # P3 独占，全员只读
│   ├── openapi.yaml
│   └── schemas/{mechanism_unit,bridge_result,eval_report}.json
├── fixtures/                    # P1 生产，全员只读
│   ├── papers.min.jsonl
│   ├── mechanisms.min.jsonl
│   ├── graph.min.pkl
│   └── bridge.sample.json
├── data/                        # .gitignore，绝不入库
│   ├── raw/  normalized/  llm_cache/  index/
├── src/conceptbridge/
│   ├── common/                  # P3：config / schemas / llm / logging / errors
│   ├── ingest/                  # P1：openalex / normalize_text / cli
│   ├── extract/                 # P1：prompts/v1 / extractor / validators / cli
│   ├── graph/                   # P2：builder / store / embeddings / taxonomy
│   ├── match/                   # P2：candidate / structural / scoring / rerank / config
│   └── api/                     # P3：main / routes / services / deps
├── eval/                        # P2
│   ├── gold/analogy_pairs.jsonl
│   ├── run_eval.py
│   └── reports/
├── tests/                       # 按 owner 前缀分目录，见下表
│   ├── ingest/ extract/         # P1
│   ├── graph/ match/            # P2
│   ├── api/ contract/           # P3
├── web/                         # P4
│   ├── src/{pages,components,lib,mocks}
│   └── vite.config.ts
├── scripts/                     # 共用，改动需 RFC
└── docs/
    ├── STATE.md                 # P3 独占：索引 + 全局阻塞，其余人只读
    ├── state/p1.md ~ p4.md      # 每人独占：进度 / 阻塞 / 技术债，互不重叠
    ├── rfc/RFC-000-template.md
    └── demo/script.md
```

| 目录 | 负责 | 不负责 |
|---|---|---|
| `src/conceptbridge/common` | 配置、Pydantic 契约、LLM 网关、日志、错误码 | 任何业务逻辑 |
| `src/conceptbridge/ingest` | 抓取、去重、文本清洗、摘要还原 | 抽机制、建图 |
| `src/conceptbridge/extract` | 机制抽取、prompt、校验、概念归一 | 匹配、打分 |
| `src/conceptbridge/graph` | 建图、持久化、领域体系、向量索引 | 排序、生成话术 |
| `src/conceptbridge/match` | 候选生成、结构打分、反琐碎、重排 | 抽取、HTTP |
| `src/conceptbridge/api` | 路由、编排、超时降级、SSE | 算法细节 |
| `web` | 交互、可视化、动画、演示模式 | 任何业务计算（只消费 API） |
| `eval` | 金标准、指标、消融、报告 | 生产代码 |

---

## 8. 数据契约（**冻结，改动需 RFC**）

### 8.1 `MechanismUnit` — 系统的原子单位

```json
{
  "id": "mu_01J9A2",
  "paper_id": "W4382917",
  "domain": "materials_science",
  "subject":   {"concept_id": "c_selective_barrier", "surface": "SEI 膜", "type": "structure"},
  "action":    {"verb": "selectively_transport", "action_class": "transport", "polarity": "neutral"},
  "object":    {"concept_id": "c_li_ion_flux", "surface": "锂离子通量", "type": "process"},
  "conditions": ["concentration_gradient", "electric_field"],
  "result": "锂离子定向通过，溶剂分子与阴离子被阻挡",
  "signature": {
    "subject_type": "structure", "action_class": "transport", "object_type": "process",
    "causality": "direct", "polarity": "neutral",
    "condition_count": 2, "condition_keys": ["concentration_gradient", "electric_field"],
    "arity": 2
  },
  "evidence": {"span": "...原文 20~120 字...", "section": "abstract", "char_start": 120, "char_end": 340},
  "confidence": 0.82,
  "extractor_version": "ext-v1.3"
}
```

### 8.2 `BridgeResult` — 主接口返回（前端唯一数据源）

```json
{
  "query": "锂枝晶抑制",
  "source": {
    "domain": "materials_science",
    "mechanisms": [ /* MechanismUnit[] */ ],
    "subgraph": {"nodes": [{"id":"c_x","label":"锂枝晶","domain":"materials_science","type":"process"}],
                 "edges": [{"id":"e1","source":"c_x","target":"c_y","action_class":"inhibit"}]}
  },
  "bridges": [{
    "target_mechanism": { /* MechanismUnit */ },
    "target_domain": "biology",
    "scores": {"structural": 0.71, "semantic": 0.55, "domain_distance": 0.93,
               "triviality": 0.0, "final": 0.68},
    "alignment": [
      {"source_role": "subject", "source_concept_id": "c_selective_barrier",
       "target_role": "subject", "target_concept_id": "c_plasma_membrane", "reason": "同为选择性屏障结构"}
    ],
    "transferable_hypothesis": "用生物膜的选择性通道蛋白思路，在 SEI 中引入离子筛分位点以抑制枝晶",
    "differences": ["生物膜有主动转运泵，SEI 只有被动扩散", "尺度差 3 个数量级，需考虑应力效应"],
    "citations": [{"paper_id": "W4382917", "span": "...", "char_start": 120, "char_end": 340}]
  }],
  "meta": {"latency_ms": 1830, "candidates": 412, "graph_version": "g-20261102-0", "degraded": false, "stub": false}
}
```

### 8.3 不变式（测试必须覆盖）

1. `bridges` 中每个 `target_domain` **必须** ≠ `source.domain`；否则丢弃。
2. 每个桥的 `citations` 非空，且每条 `span` 能在对应 `paper_id` 的原文中按偏移取到。
3. `scores.final` ∈ [0,1]，且 `candidates` ≥ `len(bridges)`。
4. 契约字段**只增不改**：新增字段必须 optional 且有默认值；改名/改类型一律视为破坏性变更。
5. 时间戳统一 ISO-8601 UTC；ID 统一字符串；金额/评分不用科学计数法。

---

## 9. API 契约（`contracts/openapi.yaml` 为权威，代码必须与之一致）

| 方法 | 路径 | 说明 | 备注 |
|---|---|---|---|
| GET | `/api/v1/health` | 存活 + 图规模 + 版本 | 前端启屏探活 |
| POST | `/api/v1/bridge` | 主接口，返回 `BridgeResult` | 同步，硬超时 15s |
| POST | `/api/v1/bridge/stream` | SSE 渐进返回：stage×3 → result → done | 已实现；前端可选，退化用同步接口 |
| GET | `/api/v1/mechanisms/{id}` | 机制详情 + 原文 | 点击节点用 |
| GET | `/api/v1/graph/subgraph` | 概念 N 跳子图 | `?concept_id=&hops=2` |
| GET | `/api/v1/eval/report` | 评测指标 JSON | 答辩看板用 |
| POST | `/api/v1/feedback` | 有用/没用 | 演示期收集，不参与评分 |

请求体（`/bridge`）：

```json
{"query": "锂枝晶抑制", "source_domain": null, "top_k": 5, "exclude_domains": [], "debug": false}
```

错误码统一 `{code, message, trace_id}`；**前端必须为每个错误码准备人话文案**，不许把 traceback 弹给评委。

---

## 10. 四人分工

| 人 | 角色 | 拥有的路径（**只可写这些**） | 只读依赖 |
|---|---|---|---|
| **P1** | 数据与抽取 | `src/conceptbridge/ingest/**`、`extract/**`、`tests/ingest|extract/**`、`fixtures/**`、`scripts/ingest_*.py`、`docs/state/p1.md` | `common/schemas.py`、`common/llm.py` |
| **P2** | 图谱与匹配 | `src/conceptbridge/graph/**`、`match/**`、`eval/**`、`tests/graph|match/**`、`docs/state/p2.md` | 同上 + `fixtures/**` |
| **P3** | 平台与集成（**架构负责人**） | `common/**`、`api/**`、`contracts/**`、`tests/api|contract/**`、`Makefile`、`pyproject.toml`、`docker-compose.yml`、`AGENTS.md`、`README.md`、`docs/STATE.md` | 全部只读 |
| **P4** | 前端与可视化 | `web/**`（含 `web/src/mocks/**`）、`docs/state/p4.md` | `contracts/**`、`fixtures/**` |

**为什么这样切**：P3 独占"脊柱"（common + contracts + api），另外三人各自一块纵向切片，四个人之间**零文件交集**。合并冲突在这一刀下几乎归零——这是并行开发能成立的唯一前提。

**P3 是唯一瓶颈，因此 P3 的 Day0 任务必须最先完成**（骨架 + 契约 + `uv run task check`）。P3 卡住时，其余三人用 `fixtures/` + `web/src/mocks/` 不阻塞。

---

## 11. 任务卡（照抄执行，不许自行扩大范围）

> 优先级：**P0 必须在 11-04 18:00 前完成；P1 只有提前完成才做；P2 一律不做。**
> 每张卡都有 Owner 与允许修改路径；越界即视为任务失败。

### P1 — 数据与抽取

| ID | 任务 | 优先 | 允许修改 | DoD（可复现命令 + 断言） |
|---|---|---|---|---|
| P1-T1 | OpenAlex 采集器：search API 分页、`abstract_inverted_index` 还原成文本、按 `concepts.domain` 打领域标签 | P0 | `ingest/**` | `python -m conceptbridge.ingest.cli --limit 1500` 产出 `data/raw/papers.jsonl`；条数 ≥1500，摘要非空率 ≥90%，有 pytest（用 3 条录制响应，不联网） |
| P1-T2 | 机制抽取：prompt v1（8 篇一批）、JSON mode、Pydantic 校验、失败重试 2 次、失败样本落盘 | P0 | `extract/**` | 500 篇 → ≥1200 条机制；schema 通过率 ≥98%；人工抽检 30 条正确率 ≥80%，结论写进 `docs/state/p1.md` |
| P1-T3 | 概念归一：字符串规范化（大小写/复数/连字符/中英括号）+ 别名合并 + 同名跨域拆分 | P0 | `ingest/**`、`extract/**` | 合并前后节点数报告；抽 20 组检查无误合并（如"膜"不能和"细胞膜"合并） |
| P1-T4 | `fixtures/` 迷你集：200 篇 + 500 机制 + 预建 `graph.min.pkl`，供 P2/P4/CI 使用 | P0 | `fixtures/**` | 文件总和 < 5MB；`pytest tests/contract -q` 能用它跑通 |
| P1-T5 | LLM 缓存层：内容哈希键、命中率统计、并发上限、**用量记录**（本赛程不限预算，只记不打闸） | P0 | `extract/**` | 同一输入二次运行命中率 100%；零重复计费；有单测 |
| P1-T6 | `manifest.json`：条数、抽取器版本、模型名、git sha、时间戳 | P0 | `ingest/**` | 每次产出自动写；答辩可指着它说"数据可复现" |
| P1-T7 | 全文补充（arXiv / PMC）+ PDF 解析 | P1 | `ingest/**` | 200 篇正文入库，失败率记录 |

### P2 — 图谱与匹配

| ID | 任务 | 优先 | 允许修改 | DoD |
|---|---|---|---|---|
| P2-T1 | 建图：机制 → 异构图（概念为点、机制为边）；领域体系挂载；pickle 持久化 + 加载 <2s | P0 | `graph/**` | 500 机制建图 <10s；`GraphStore.load()` <2s；有 pytest |
| P2-T2 | 动作分类器：12 类词典 + LLM 兜底 + 缓存 | P0 | `graph/**` | 抽 100 条人工核对准确率 ≥85%；未命中率 <15% |
| P2-T3 | L1 匹配器：候选生成（FAISS top-200）→ 结构签名打分 → 反琐碎惩罚 → top-k | P0 | `match/**` | `python -m conceptbridge.match.cli --query "锂枝晶抑制" --fixtures` 输出合法 `BridgeResult`（过 schema）；P95 <1500ms（500 机制） |
| P2-T4 | LLM 重排 + 生成「可迁移假设 / 差异说明 / 引用」 | P0 | `match/**` | 每条输出都能定位到 `evidence.span`；失败时有规则兜底文案，不许空 |
| P2-T5 | 金标准 30 对 + `eval/run_eval.py`（P@5 / MRR@10 / 四段消融） | P0 | `eval/**` | `uv run task eval` 生成 `eval/reports/latest.md`；含消融表与 3 个 case study |
| P2-T6 | 多步机制子图匹配（节点≤8，VF2/近似 GED，超限降级为单三元组） | P1 | `match/**` | 有降级路径的单测；无超时 |
| P2-T7 | 领域距离与 hard negative 集（10 对"像但不对"） | P1 | `eval/**` | 误报率下降记录 |

### P3 — 平台与集成

| ID | 任务 | 优先 | 允许修改 | DoD |
|---|---|---|---|---|
| P3-T1 | 仓库骨架：uv 工程、ruff/mypy/eslint、pytest 配置、`Makefile`、`.gitignore` | P0 | 全局 | 空项目上 `uv run task check` 绿；`uv run task setup` 一把过 |
| P3-T2 | `common/schemas.py`（Pydantic v2）+ 导出 `contracts/schemas/*.json` + `contracts/openapi.yaml` | P0 | `common/**`、`contracts/**` | OpenAPI 通过 `redocly lint`；`bridge.sample.json` 能过 schema 校验 |
| P3-T3 | `common/llm.py`：统一网关（超时/重试/JSON mode/缓存钩子/成本统计） | P0 | `common/**` | 有失败重试单测；无 key 时给出明确报错不许静默 |
| P3-T4 | FastAPI 路由 + 错误码 + CORS + 请求校验 | P0 | `api/**` | `pytest tests/contract` 全绿；错误码表与 §9 一致 |
| P3-T5 | 编排服务：query → 图检索 → 匹配 → 重排，带超时与降级 | P0 | `api/**` | `uv run task e2e` 跑通 3 条 demo query；超时返回 `degraded=true` 而非 500 |
| P3-T6 | 离线演示模式 `uv run task demo`：预生成图与缓存结果，断网可跑 | P0 | 全局 | 拔网线后全流程可用（录屏为证） |
| P3-T7 | `docs/STATE.md` 索引维护 + 每日合并窗口 + CI 门禁 | P0 | `docs/STATE.md` | 每次合并后 `main` 上 `uv run task check` 绿；四人文件无冲突 |

### P4 — 前端与可视化

| ID | 任务 | 优先 | 允许修改 | DoD |
|---|---|---|---|---|
| P4-T1 | Vite + React + TS + Tailwind + shadcn 骨架；MSW 按 `openapi.yaml` 造假；一键 mock 启动 | P0 | `web/**` | 无后端时 `npm run dev:mock` 可出完整结果页 |
| P4-T2 | 双域图：Cytoscape 双 cluster 布局、领域配色、节点/边样式系统 | P0 | `web/**` | 200 节点流畅（≥50fps）；缩放/拖拽可用 |
| P4-T3 | 桥动画：SVG 弧线 + 对齐节点高亮 + 时序编排 | P0 | `web/**` | 3s 内完成、可重播、可跳过；无动画时信息不丢失 |
| P4-T4 | 结果面板：假设卡 / 差异卡 / 引用卡 / 分数条，引用点击高亮原文 | P0 | `web/**` | 5 人盲测可读性 ≥4/5；引用必可点 |
| P4-T5 | 首页：搜索框 + 3 个示例 query 快捷入口 + loading/空态/错误态 | P0 | `web/**` | 首屏 3 秒内明白要输入什么 |
| P4-T6 | 演示模式：键盘一键推进、预置 query、离线回放 | P0 | `web/**` | 按 `→` 一步一屏，全程不用鼠标讲解 |
| P4-T7 | 评测看板页（读 `/api/v1/eval/report`） | P1 | `web/**` | 消融表可读，答辩可投屏 |

---

## 12. Agent 工作准则（硬规则，违反即拒绝合并）

### 12.1 十二条

1. 只写 owner 路径；其余**只读**。要改别人的，写 RFC 并 @ 对应 owner，**不自行修改**。
2. 不新增第三方依赖、不动 `pyproject.toml`（P3 除外）。需要则走 RFC。
3. 不改 `contracts/` 已冻结的字段名与类型；新增字段必须 optional 且有默认值。
4. 不硬编码任何密钥、Token、绝对路径；一律走 `common/config.py` + `.env`。
5. `data/` 永不 `git add`；大文件只进 `fixtures/`（<5MB）。
6. 不给通过测试而放宽断言、加 `skip`、或改 fixtures 迁就代码。
7. 库代码里不许留 `print`（用 `common/logging.py` 的 `get_logger`）；不许 `except: pass`。
8. 不顺手重构别人目录；发现问题写进 `docs/state/p<N>.md` 的「技术债」区。
9. 不做没有测试的新逻辑；核心算法（`match/`、`extract/`、`ingest/` 归一）单测覆盖 ≥70%。
10. 单次 PR diff ≤400 行（生成代码除外），超了拆卡。
11. 输出必须可复现：随机种子固定，LLM 一律走缓存，`DEMO_MODE=1` 时不打外网。
12. 卡住 30 分钟 → 写进 `docs/state/p<N>.md` 的「阻塞」区（现象 / 试过什么 / 需要谁），然后换下一张卡，**不要死磕也不要越界改**。

### 12.2 任务执行循环（每张卡照做）

1. **领卡**：在 `docs/state/p<N>.md` 里把自己那张卡改成 `in_progress` + 分支名。**只改自己的文件。**
2. **读**：本文件 → owner 目录 `README.md` → 相关 `contracts/schemas/*` → 已有测试。
3. **红**：先写失败测试，跑一次确认它真的失败（防假绿）。
4. **绿**：最小实现。**不预判未来需求**，不做用不上的抽象。
5. **验**：`uv run task check`；跑任务卡里的 DoD 命令，原样贴输出。
6. **交**：Conventional Commit → 推分支 → 开 PR（按 §12.4 模板）。
7. **报**：`docs/state/p<N>.md` 里改成 `done`，附命令与关键数字（条数/耗时/准确率）。

### 12.3 分支与合并

- 从 `main` 切短分支：`feat/p<N>-<短语>`、`fix/p<N>-<短语>`、`docs/<短语>`。
- 不直接提交到 `main`；`main` 只接收 PR 的 merge。**本项目不使用 `develop`**——2026-11-03 决策：团队实际按 feature → `main` 走，多一层分支只多一次操作失误。
- 禁止 `git push --force` / `--force-with-lease`；撤销用 `git revert`。
- Conventional Commits，中文祈使句、一行、不加句号：
  `feat(match): 增加结构签名打分与反琐碎惩罚`
- **合并窗口：每天 12:30 与 22:00，各 30 分钟。** 窗口外只推分支不开 PR。由 P3 合并并跑 `uv run task e2e`。
- `main` 被弄红 → 30 分钟内由破坏者修复，修不了立即 `git revert`，不许挂到第二天。

### 12.4 PR 模板（必填这 5 行）

```
卡号: P2-T3
改了什么: 新增结构签名打分与反琐碎惩罚，接入候选生成
怎么验的: uv run task check 绿; python -m conceptbridge.match.cli --query "锂枝晶抑制" --fixtures 输出 5 个桥
影响面: 无契约变更; 仅 match 内部
风险: 泛化词表不全, 已记 tech-debt
```

### 12.5 契约变更流程（RFC）

改动 `contracts/`、`common/schemas.py`、`pyproject.toml`、`Makefile` 前，在 `docs/rfc/` 新建 10 行以内的文件：

```
RFC-003 给 BridgeResult 增加 degraded 字段
提出人: P3  时间: 11-03 14:20
动机: 超时降级需要让前端区分"结果少"和"没结果"
变更: meta 下新增 optional bool degraded, 默认 false
影响: 前端加一条提示条; P2 无需改
结论: 已同意 / P4 ack 14:35
```

**契约变更只在这两个窗口处理**，窗口外一律用 optional 字段绕开。这不是官僚，是四人四 Agent 并行下唯一能防"合并地狱"的办法。

---

## 13. 时间表（按提交 11-04 24:00 / 答辩 11-06）

> 如果赛程实际是 11-06 才截止，整表按比例拉长到 5 天即可，任务卡顺序不变。

### Day 0 · 11-02 晚（20:00–24:00）· 目标：**契约冻结，四人解除阻塞**

| 时段 | P1 | P2 | P3 | P4 |
|---|---|---|---|---|
| 20:00–21:30 | 读题 + OpenAlex 字段调研 | 读题 + 定 12 类动作词表 + 金标准前 10 对 | **T1 骨架 + T2 契约**（最高优先） | 读契约 + 出 3 屏线框 |
| 21:30–23:00 | 抓 200 篇试跑 | 写建图与打分伪代码 + 分数权重初版 | `bridge.sample.json` + `uv run task check` 绿 | 搭 Vite 骨架 + MSW 假数据 |
| 23:00 | **契约 v0 冻结会议（15 分钟，全员）** | 同左 | 同左 | 同左 |

**Day0 出口条件**：`uv run task check` 绿、`fixtures/` 有 200 篇、`web` 能用 mock 出一张结果页。**任一条不满足，Day1 全部停下先补。**

> **Day0 进度（2026-11-02 21:00 更新）**：骨架 + 契约 + API + fixture 兜底已完成并验证——
> `uv run task check` 绿、`uv run task e2e` 3 条 query 通过、金标准 40 条已入库。
> **四个人现在就可以开工，不必等 23:00 的冻结会。** P3 七张卡已全部 done；
> 剩余：P1 的 200 篇 fixture、P4 的 web 骨架、P2 的 `match/pipeline.py`。

### Day 1 · 11-03 · 目标：**端到端跑通（fixture 数据）**

| 时段 | P1 | P2 | P3 | P4 |
|---|---|---|---|---|
| 上午 | T1 全量 1500 篇 + T6 manifest | T1 建图 + T2 动作分类 | T3 LLM 网关 + T4 路由 | T2 双域图 + T5 首页 |
| 下午 | T2 抽取 500 篇 + T5 缓存 | T3 L1 匹配器 | T5 编排 + T4 契约测试 | T3 桥动画 |
| 20:00–22:00 | — | — | **集成 #1：`uv run task e2e` 跑通 fixture 端到端** | — |
| 22:00–23:00 | 修集成暴露的问题 | 修 | 修 + 更新 STATE | 修 |

**Day1 出口条件**：输入「锂枝晶抑制」，页面出现两个领域、一条桥、一张假设卡。**哪怕数据是 fixture 的。**

### Day 2 · 11-04 · 目标：**真实数据 + 可讲 + 可交付**

| 时段 | 全部 |
|---|---|
| 上午 | 真实数据全链路（1500 篇 → 3000 机制 → 图）；P4 接真接口；P2 出首版评测 |
| 14:00 | **集成 #2 + 第一次彩排**（骂醒会：找最丢人的 3 个问题） |
| 15:00–18:00 | 按彩排问题修；P2 补消融表；P4 加演示模式；P1 补 30 对金标准协作 |
| **18:00** | **代码冻结（打 tag `v0.9-submit`）**，只允许 P0 bug 修复 |
| 19:00 | 提交材料定稿：README、3 分钟录屏、PPT v1、离线包 |
| 21:00 | 第二次彩排（严格计时 3 分钟） |
| **24:00** | **提交（互评周四 8:00 开始，逾期 0 分 → 扣 100 分）** |

### Day 3 · 11-05 · 目标：**只有答辩准备，禁止改功能**

- 上午：读互评反馈（如有）、修演示路径上的 bug（仅限 3 条 demo query）。
- 下午：PPT 定稿 + 逐字稿 + 预判 10 个提问并写答案。
- 晚上：第三次彩排 + 双设备验证 + U 盘/云盘双备份。

### Day 4 · 11-06 · 目标：**现场**

提前 40 分钟到场，先跑 `uv run task demo` 预热（首次加载最慢），再开讲。

---

## 14. 质量门禁

```bash
uv run task setup    # uv sync + npm ci
uv run task dev      # api + web 一起起
npm --prefix web run dev:mock   # 只起前端 + MSW（P4 负责脚本）
uv run task check    # ruff + mypy + pytest(unit) + 契约测试 + tsc + eslint   ← 必须绿
uv run task merge    # 合并窗口闸门 = check + e2e，不过不许合入 main
uv run task e2e      # 3 条 demo query 端到端冒烟
uv run task eval     # 生成 eval/reports/latest.md
uv run task demo     # 冻结样例 + 禁外网（绝不翻车，只有 4 条机制）
uv run task demo --corpus  # 真实语料 + 禁外网（LLM 只读缓存），答辩用这个
```

`uv run task check` 的组成（缺一不可）：

1. `ruff check .` 零 error。
2. `mypy` 零 error（配置在 `pyproject.toml`，当前覆盖 `common/` + `api/`；`match/` 落地后把它加进去）。
3. `pytest tests -q --ignore=tests/e2e` 全绿。
4. `pytest tests/contract -q`：所有样例 JSON 过 schema，所有响应符合 OpenAPI。
5. `npm --prefix web run typecheck` 零 error（P4 提供的脚本，内部跑 `tsc --noEmit` + `eslint`）。

**覆盖率只对三处强制 ≥70%**：`extract/`（抽取校验）、`match/`（打分）、`ingest/`（归一）。其余不作要求，别为覆盖率写垃圾测试。

---

## 15. 评测方案（这是 Tech 40% 的真正抓手）

### 15.1 金标准（`eval/gold/analogy_pairs.jsonl`，已完成 30 正 + 10 负）

**文件已在仓库里，由领域分析产出。P2 只消费、不要重写。** 正例字段：

```jsonl
{"id":"g01","group":"G1","query":"硅负极循环粉化失效","source_domain":"materials_science","target_domain":"biology","source_mechanism":"主体+动作+条件+结果","target_mechanism":"...","shared_structure":"structure→stabilize→structure | direct | promote","why":"为什么同构，可迁移什么","transferable_hypothesis":"具体到能设计实验的假设","usefulness":5}
```

负例字段：`{"id":"n01",...,"why_invalid":"...","trap_type":"generic_property|same_word_diff_meaning|scale_mismatch|reverse_causality"}`。

- 分布：G1 16 条、G2 14 条；`usefulness` 5×8 / 4×20 / 3×2；负例四类陷阱各 2–3 条。
- `shared_structure` 格式为 `概念类型→动作类别→概念类型 | 因果形态 | 极性`，动作类别必须命中 12 类枚举。
- **`why` 字段是评测的锚**：模型出结果后要人工核对"找到的是不是这一条"，否则 P@5 是自欺欺人。

### 15.2 指标与消融

| 配置 | struct | domain_dist | rerank | P@5 | MRR@10 |
|---|---|---|---|---|---|
| A 纯语义（baseline，即"套壳"） | ✗ | ✗ | ✗ | 待填 | 待填 |
| B + 结构签名 | ✓ | ✗ | ✗ | 待填 | 待填 |
| C + 领域距离 | ✓ | ✓ | ✗ | 待填 | 待填 |
| D 完整 | ✓ | ✓ | ✓ | 待填 | 待填 |

**答辩必说的一句**：「纯语义 baseline 的 P@5 是 x，加上结构签名到 y，说明我们的增益来自结构而非提示词。」这句话同时打死"套壳"质疑和"技术难度"质疑。

### 15.3 三个 case study（写进 PPT）

1. **成功的**：锂枝晶 → 细胞膜选择性通透（有可迁移假设）。
2. **反琐碎的**：展示一条被惩罚项压下去的废话桥，说明"我们知道什么是坏答案"。
3. **失败的**：诚实展示一个错配 + 说明原因（跨域尺度过大）。**主动认错比被问出来强十倍。**

---

## 16. 演示脚本（3 分钟，`docs/demo/script.md` 定稿）

| 时间 | 画面 | 台词要点 |
|---|---|---|
| 0:00–0:20 | 标题页 + 一句话 | "跨学科检索现在找的是同一个词，我们找的是同一个道理" |
| 0:20–0:40 | 输入「锂枝晶抑制」，图谱展开 | 指出这是材料学的真问题 |
| 0:40–1:00 | 左侧材料机制成形 | 讲清"机制四元组"是什么，一句话 |
| 1:00–1:30 | **桥动画飞到生物学** + 对齐高亮 | 全场唯一必须"哇"的 8 秒，讲慢一点 |
| 1:30–2:00 | 假设卡 + 差异卡 + 引用高亮 | "它给的不是摘要，是一个可验证的假设" |
| 2:00–2:30 | 第二个例子（快，15 秒一个） | 证明不是手工调的一个 demo |
| 2:30–2:50 | 消融表 | "结构打分带来 P@5 +x，这是它和 RAG 的区别" |
| 2:50–3:00 | 价值与边界 | 主动说局限：只做两类跨域，不吹通用 |

**现场兜底（按顺序降级）**：
1. 主用 `uv run task demo` 离线模式（启动前自动预检 5 项资产，缺东西直接拒绝启动，不会带到台上）。
2. 网络/服务异常 → 立即切录屏（3 分钟 MP4，提前录好，播放器已打开）。
3. 录屏也异常 → 用 PPT 内嵌的 GIF 逐帧讲。
4. 无论哪级，**讲解不停**，别在台上 debug。

---

## 17. 降级阶梯（进度落后时按顺序砍，不许自己发明砍法）

| 顺序 | 砍什么 | 代价 | 何时触发 |
|---|---|---|---|
| 1 | 去掉 `stream` SSE、去掉全文 PDF（P1-T7） | 无感 | Day1 结束仍未跑通 e2e |
| 2 | 概念归一降级为"别名表 + 字符串规范化"，不做聚类 | 节点略冗余 | Day2 上午仍无真实数据 |
| 3 | 匹配只用 L1 三元组，砍多步子图（P2-T6） | 技术叙事变薄，用消融表补 | Day2 14:00 彩排仍不稳 |
| 4 | top_k 从 20 降到 5，砍 rerank，用规则模板生成话术 | 假设质量下降 | Day2 16:00 |
| 5 | 图谱可视化降级为"两栏卡片 + 一条连接线" | 丢掉最强 wow 点，**尽量别到这步** | Day2 17:00 |
| 6 | 只保 3 条预置 query，砍自由输入 | 可接受，答辩不明显 | 任何时刻 |

**永不砍**：离线演示模式、消融表、3 分钟录屏、契约测试。这四样是"不崩"的底。

---

## 18. 附录

### 18.1 环境变量（`.env.example`）

```bash
OPENALEX_MAILTO=team@example.com      # 礼貌池必需
LLM_BASE_URL=https://api.deepseek.com
LLM_API_KEY=
LLM_MODEL=deepseek-chat
EMBED_MODEL=intfloat/multilingual-e5-large
DATA_DIR=./data
DEMO_MODE=0        # 1 = 冻结图谱到预置样例 + 禁外网（绝不翻车的现场演示）
LLM_OFFLINE=0      # 1 = 仍用真实语料，但禁止任何 LLM 外网请求（只读缓存）
TOP_K=5
LOG_LEVEL=INFO
```

### 18.2 命名

- Python：`snake_case` 文件/函数，`PascalCase` 类；模块内不写 `__all__`。
- 前端：组件 `PascalCase.tsx`，hook `useXxx.ts`，样式用 Tailwind 原子类不写 css 文件。
- 数据快照：`data/index/g-YYYYMMDD-N/`，`manifest.json` 记 `git_sha` + 版本。
- 日志行格式：`[module] [event] key=value`，禁止打印正文全文（只打 `content_len`）。

### 18.3 学术与合规

- OpenAlex 数据 CC0，可自由使用；arXiv 遵守速率限制（≥3s/请求），**不重新分发全文**。
- 论文原文片段仅用于引用展示，界面上标注来源与链接。
- 演示数据可含真实论文标题与作者，但**不得伪造引用**——评委抽查一条就够致命。

### 18.4 本文件的演进

两天内不改结构，只改任务卡状态与数字。赛后若复用，按此拆分：`docs/architecture.md`（§5）、`docs/api.md`（§8–§9）、`docs/standards/dev.md`（§12）、`docs/plan.md`（§11–§13），AGENTS.md 回到 60 行以内。

---

## 19. 现在就开始

**骨架已搭好并验证过，不要重新 `uv init`。** 四个人的第一条命令：

```bash
git clone <repo> && cd conceptbridge
uv sync --extra analyze
uv run task check          # 必须先看到 [check] OK，再动代码
```

| 人 | 第一条命令 | 期望看到 |
|---|---|---|
| P1 | `uv run python -m conceptbridge.ingest.cli --limit 200` | `data/raw/papers.jsonl` 有 200 行 |
| P2 | 写 `src/conceptbridge/match/pipeline.py` 的 `run_bridge()` | API 自动从 fixture 切到真实实现，无需通知任何人 |
| P3 | 七张卡已完成；后续只维护合并窗口与契约变更 | `uv run task merge` 全绿 |
| P4 | `npm create vite@latest web -- --template react-ts` | 能对着 `:8000` 的结果页出界面 |

**最重要的纪律**：只改 `docs/state/p<N>.md`，四个人四个文件，永不冲突。
这两天最贵的浪费不是写错代码，是四个人同时改一个还没定型的文件或契约。
