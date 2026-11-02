"""规则话术。引用必须是目标机制 evidence 的原文片段，不许另写无出处的事实。"""

from __future__ import annotations

from dataclasses import dataclass

from ..common.schemas import Citation, MechanismUnit, RoleAlignment


@dataclass(frozen=True)
class Explanation:
    hypothesis: str
    differences: list[str]
    citations: list[Citation]
    alignment: list[RoleAlignment]


def explain_bridge(source: MechanismUnit, target: MechanismUnit) -> Explanation:
    alignment = [
        RoleAlignment(
            source_role="subject",
            source_concept_id=source.subject.concept_id,
            target_role="subject",
            target_concept_id=target.subject.concept_id,
            reason=f"主体角色对应，类型 {source.subject.type} 对 {target.subject.type}",
        ),
        RoleAlignment(
            source_role="object",
            source_concept_id=source.object.concept_id,
            target_role="object",
            target_concept_id=target.object.concept_id,
            reason=f"客体角色对应，类型 {source.object.type} 对 {target.object.type}",
        ),
    ]
    hypothesis = (
        f"沿用{target.subject.surface}的{target.action.action_class}结构，"
        f"把{source.subject.surface}对{source.object.surface}的"
        f"{source.action.verb}迁到{target.domain}："
        f"{target.result}"
    )
    differences = [
        f"源域条件是 {', '.join(source.conditions) or '无'}，目标域条件是 {', '.join(target.conditions) or '无'}",
        f"源域结果侧重「{source.result}」，目标域结果侧重「{target.result}」",
    ]
    citations = [
        Citation(
            paper_id=target.paper_id,
            span=target.evidence.span,
            char_start=target.evidence.char_start,
            char_end=target.evidence.char_end,
        )
    ]
    return Explanation(hypothesis, differences, citations, alignment)
