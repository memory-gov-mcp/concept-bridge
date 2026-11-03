import pytest

from conceptbridge.extract.normalize import concept, condition_key
from conceptbridge.extract.validators import validate_paper


@pytest.fixture
def paper():
    return {
        "paper_id": "W1",
        "domain": "biology",
        "abstract": "Membranes transport ions under a concentration gradient.",
    }


@pytest.fixture
def draft(paper):
    return {
        "subject": {"surface": "Membranes", "type": "structure"},
        "action": {"verb": "transport", "action_class": "transport", "polarity": "neutral"},
        "object": {"surface": "ions", "type": "substance"},
        "conditions": ["concentration gradient", "浓度梯度"],
        "result": "ions are transported",
        "causality": "direct",
        "evidence": {"span": paper["abstract"]},
        "confidence": 0.8,
    }


def test_signature_and_offsets(paper, draft):
    unit = validate_paper(paper, [draft])[0]
    assert unit.signature.condition_keys == ["concentration_gradient"]
    assert unit.signature.condition_count == 1
    assert unit.signature.subject_type == unit.subject.type
    assert (
        paper["abstract"][unit.evidence.char_start : unit.evidence.char_end] == unit.evidence.span
    )
    assert unit == validate_paper(paper, [draft])[0]


def test_wrong_evidence_and_same_entity(paper, draft):
    draft["evidence"] = {"span": "invented"}
    with pytest.raises(ValueError):
        validate_paper(paper, [draft])
    draft["evidence"] = {"span": paper["abstract"]}
    draft["object"] = draft["subject"]
    with pytest.raises(ValueError):
        validate_paper(paper, [draft])


def test_repeated_span_requires_position(paper, draft):
    paper["abstract"] *= 2
    with pytest.raises(ValueError):
        validate_paper(paper, [draft])
    draft["evidence"]["char_start"] = 0
    assert validate_paper(paper, [draft])[0].evidence.char_start == 0


def test_domain_split_and_conservative_aliases():
    membrane = concept("biology", "structure", "Membranes")
    assert membrane == concept("biology", "structure", "membrane")
    assert membrane != concept("biology", "structure", "cell membrane")
    assert membrane != concept("materials_science", "structure", "membrane")
    assert concept("biology", "structure", "细胞膜") == concept(
        "biology", "structure", "plasma membrane"
    )
    assert condition_key("电场") == "electric_field"
    assert concept("biology", "structure", "MEMBRANES") == membrane
    assert concept("chemistry", "substance", "Li") != concept("chemistry", "substance", "li")


def test_confidence_cannot_disguise_duplicate_mechanisms(paper, draft):
    with pytest.raises(ValueError, match="duplicate"):
        validate_paper(paper, [draft, {**draft, "confidence": 0.9}])
