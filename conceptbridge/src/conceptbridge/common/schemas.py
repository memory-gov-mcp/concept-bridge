"""项目数据契约（唯一权威定义）。

冻结于 Day0 2026-11-02。改动流程见 AGENTS.md §12.5：
只增不改，新增字段必须 optional 且有默认值。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ConceptType = Literal["structure", "process", "substance", "signal", "state"]

ActionClass = Literal[
    "inhibit",
    "promote",
    "transport",
    "transform",
    "recognize",
    "amplify",
    "stabilize",
    "degrade",
    "compete",
    "isolate",
    "trigger",
    "regulate",
]

Causality = Literal["direct", "mediated", "feedback", "threshold"]
Polarity = Literal["promote", "inhibit", "neutral"]
Role = Literal["subject", "object"]
Section = Literal["abstract", "intro", "results", "discussion", "conclusion", "unknown"]

# extra="forbid"：任何未定义字段直接报错，防止抽取器偷偷塞字段。
_BASE = ConfigDict(extra="forbid")


class ConceptRef(BaseModel):
    """机制里的一个实体。concept_id 是归一后的 ID，surface 是原文写法。"""

    model_config = _BASE

    concept_id: str = Field(min_length=1)
    surface: str = Field(min_length=1)
    type: ConceptType


class ActionRef(BaseModel):
    """机制里的动作。action_class 只能取 12 类之一。"""

    model_config = _BASE

    verb: str = Field(min_length=1)
    action_class: ActionClass
    polarity: Polarity


class EvidenceSpan(BaseModel):
    """原文证据。前端点击引用时按 char_start/char_end 高亮。"""

    model_config = _BASE

    span: str = Field(min_length=1)
    section: Section = "abstract"
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)

    @model_validator(mode="after")
    def _span_range(self) -> EvidenceSpan:
        if self.char_end <= self.char_start:
            raise ValueError("char_end 必须大于 char_start")
        return self


class StructuralSignature(BaseModel):
    """结构签名——本项目"结构相似而非文字相似"的载体。"""

    model_config = _BASE

    subject_type: ConceptType
    action_class: ActionClass
    object_type: ConceptType
    causality: Causality
    polarity: Polarity
    condition_count: int = Field(ge=0)
    condition_keys: list[str] = Field(default_factory=list)
    arity: int = Field(ge=2, le=8)


class MechanismUnit(BaseModel):
    """系统的原子单位：一个可比较的机制。"""

    model_config = _BASE

    id: str = Field(min_length=1)
    paper_id: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    subject: ConceptRef
    action: ActionRef
    object: ConceptRef
    conditions: list[str] = Field(default_factory=list)
    result: str = Field(min_length=1)
    signature: StructuralSignature
    evidence: EvidenceSpan
    confidence: float = Field(ge=0.0, le=1.0)
    extractor_version: str = Field(min_length=1)

    @model_validator(mode="after")
    def _signature_consistent(self) -> MechanismUnit:
        sig = self.signature
        errors: list[str] = []
        if sig.subject_type != self.subject.type:
            errors.append(f"signature.subject_type={sig.subject_type} != subject.type={self.subject.type}")
        if sig.object_type != self.object.type:
            errors.append(f"signature.object_type={sig.object_type} != object.type={self.object.type}")
        if sig.action_class != self.action.action_class:
            errors.append(
                f"signature.action_class={sig.action_class} != action.action_class={self.action.action_class}"
            )
        if sig.polarity != self.action.polarity:
            errors.append(f"signature.polarity={sig.polarity} != action.polarity={self.action.polarity}")
        if sig.condition_count != len(sig.condition_keys):
            errors.append(
                f"condition_count={sig.condition_count} != len(condition_keys)={len(sig.condition_keys)}"
            )
        if sig.condition_count > len(self.conditions):
            errors.append(
                f"condition_count={sig.condition_count} 超过 conditions 条数={len(self.conditions)}"
            )
        if errors:
            raise ValueError("机制内部不一致: " + "; ".join(errors))
        return self


class GraphNode(BaseModel):
    model_config = _BASE

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    type: ConceptType


class GraphEdge(BaseModel):
    model_config = _BASE

    id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    action_class: ActionClass


class Subgraph(BaseModel):
    model_config = _BASE

    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)

    @model_validator(mode="after")
    def _edges_reference_nodes(self) -> Subgraph:
        ids = {n.id for n in self.nodes}
        for e in self.edges:
            if e.source not in ids or e.target not in ids:
                raise ValueError(f"边 {e.id} 的端点不在 nodes 中")
        return self


class BridgeScores(BaseModel):
    model_config = _BASE

    structural: float = Field(ge=0.0, le=1.0)
    semantic: float = Field(ge=0.0, le=1.0)
    domain_distance: float = Field(ge=0.0, le=1.0)
    triviality: float = Field(ge=0.0, le=1.0)
    final: float = Field(ge=0.0, le=1.0)


class RoleAlignment(BaseModel):
    """一个桥的节点级对应关系，前端用它做对齐高亮。"""

    model_config = _BASE

    source_role: Role
    source_concept_id: str = Field(min_length=1)
    target_role: Role
    target_concept_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class Citation(BaseModel):
    model_config = _BASE

    paper_id: str = Field(min_length=1)
    span: str = Field(min_length=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)


class Bridge(BaseModel):
    """一条跨域桥：目标机制 + 为什么能对上 + 能迁移什么。"""

    model_config = _BASE

    target_mechanism: MechanismUnit
    target_domain: str = Field(min_length=1)
    scores: BridgeScores
    alignment: list[RoleAlignment] = Field(default_factory=list)
    transferable_hypothesis: str = Field(min_length=1)
    differences: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(min_length=1)


class BridgeSource(BaseModel):
    model_config = _BASE

    domain: str = Field(min_length=1)
    mechanisms: list[MechanismUnit] = Field(default_factory=list)
    subgraph: Subgraph = Field(default_factory=Subgraph)


class ResultMeta(BaseModel):
    model_config = _BASE

    latency_ms: int = Field(ge=0)
    candidates: int = Field(ge=0)
    graph_version: str = Field(min_length=1)
    degraded: bool = False
    stub: bool = False


class BridgeResult(BaseModel):
    """POST /api/v1/bridge 的返回，也是前端唯一数据源。"""

    model_config = _BASE

    query: str = Field(min_length=1)
    source: BridgeSource
    bridges: list[Bridge] = Field(default_factory=list)
    meta: ResultMeta

    @model_validator(mode="after")
    def _invariants(self) -> BridgeResult:
        for b in self.bridges:
            if b.target_domain == self.source.domain:
                raise ValueError(f"桥 {b.target_mechanism.id} 与源同域({self.source.domain})，应被丢弃")
        if self.meta.candidates < len(self.bridges):
            raise ValueError(
                f"candidates={self.meta.candidates} 小于桥数={len(self.bridges)}"
            )
        return self


# --------------------------------------------------------------------------- #
# 请求 / 评测
# --------------------------------------------------------------------------- #


class BridgeRequest(BaseModel):
    model_config = _BASE

    query: str = Field(min_length=2, max_length=200)
    source_domain: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)
    exclude_domains: list[str] = Field(default_factory=list)
    debug: bool = False


class FeedbackRequest(BaseModel):
    model_config = _BASE

    query: str = Field(min_length=1)
    bridge_mechanism_id: str = Field(min_length=1)
    useful: bool
    note: str | None = None


class EvalRow(BaseModel):
    """消融表的一行。"""

    model_config = _BASE

    config: str = Field(min_length=1)
    use_structural: bool = False
    use_domain_distance: bool = False
    use_rerank: bool = False
    p_at_5: float | None = Field(default=None, ge=0.0, le=1.0)
    mrr_at_10: float | None = Field(default=None, ge=0.0, le=1.0)


class EvalReport(BaseModel):
    model_config = _BASE

    generated_at: str = Field(min_length=1)
    gold_pairs: int = Field(ge=0)
    hard_negatives: int = Field(ge=0)
    kappa: float | None = Field(default=None, ge=-1.0, le=1.0)
    rows: list[EvalRow] = Field(default_factory=list)
    case_study_ids: list[str] = Field(default_factory=list)
    notes: str | None = None


class HealthResponse(BaseModel):
    model_config = _BASE

    status: Literal["ok", "degraded"]
    version: str
    graph_version: str
    graph_ready: bool
    demo_mode: bool


class SubgraphResponse(BaseModel):
    model_config = _BASE

    concept_id: str
    hops: int = Field(ge=1, le=3)
    subgraph: Subgraph


class ErrorBody(BaseModel):
    model_config = _BASE

    code: str
    message: str
    trace_id: str
