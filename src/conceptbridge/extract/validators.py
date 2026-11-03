"""校验模型草稿，生成冻结的 MechanismUnit。"""

import hashlib
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..common.schemas import ActionRef, Causality, ConceptType, MechanismUnit
from ..graph.taxonomy import classify_action
from .normalize import NORMALIZER_VERSION, concept, condition_key

EXTRACTOR_VERSION = "ext-v1"


class DraftConcept(BaseModel):
    model_config = ConfigDict(extra="forbid")
    surface: str = Field(min_length=1)
    type: ConceptType


class DraftEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    span: str = Field(min_length=1)
    char_start: int | None = Field(default=None, ge=0, strict=True)


class DraftMechanism(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject: DraftConcept
    action: ActionRef
    object: DraftConcept
    conditions: list[str]
    result: str = Field(min_length=1)
    causality: Causality
    evidence: DraftEvidence
    confidence: float = Field(ge=0, le=1)


def validate_paper(paper: dict[str, Any], drafts: Any) -> list[MechanismUnit]:
    if not isinstance(drafts, list) or not 1 <= len(drafts) <= 5:
        raise ValueError("each paper needs 1..5 evidence-supported mechanisms")
    units = []
    for item in drafts:
        draft = DraftMechanism.model_validate(item)
        abstract, span = paper["abstract"], draft.evidence.span
        start = draft.evidence.char_start
        if start is None:
            start = abstract.find(span)
            if start < 0 or abstract.find(span, start + 1) >= 0:
                raise ValueError("evidence must occur exactly once or provide char_start")
        end = start + len(span)
        if abstract[start:end] != span:
            raise ValueError("evidence offsets do not match abstract")
        subject = draft.subject.model_dump()
        subject["concept_id"] = concept(paper["domain"], draft.subject.type, draft.subject.surface)[
            0
        ]
        obj = draft.object.model_dump()
        obj["concept_id"] = concept(paper["domain"], draft.object.type, draft.object.surface)[0]
        if subject["concept_id"] == obj["concept_id"]:
            raise ValueError("binary mechanism needs two distinct concepts")
        action = draft.action.model_dump()
        action["action_class"] = classify_action(draft.action.verb) or draft.action.action_class
        conditions = sorted({condition_key(value) for value in draft.conditions})
        data = {
            "paper_id": paper["paper_id"],
            "domain": paper["domain"],
            "subject": subject,
            "object": obj,
            "action": action,
            "conditions": conditions,
            "result": draft.result,
            "signature": {
                "subject_type": subject["type"],
                "object_type": obj["type"],
                "action_class": action["action_class"],
                "polarity": action["polarity"],
                "causality": draft.causality,
                "condition_keys": conditions,
                "condition_count": len(conditions),
                "arity": 2,
            },
            "evidence": {"span": span, "char_start": start, "char_end": end, "section": "abstract"},
            "confidence": draft.confidence,
            "extractor_version": EXTRACTOR_VERSION,
        }
        identity_data = {key: value for key, value in data.items() if key != "confidence"}
        identity = json.dumps(
            [NORMALIZER_VERSION, identity_data], sort_keys=True, ensure_ascii=False
        )
        data["id"] = "mu_" + hashlib.sha256(identity.encode()).hexdigest()[:24]
        units.append(MechanismUnit.model_validate(data))
    if len({unit.id for unit in units}) != len(units):
        raise ValueError("duplicate mechanisms")
    return units
