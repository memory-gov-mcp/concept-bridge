"""将 OpenAlex 元数据转换为 P1/P2 共同使用的论文记录。"""

import re
from typing import Any

# OpenAlex field IDs, not its four broad domains. Labels match P2 match/config.py.
FIELD_DOMAINS = {
    "25": "materials_science",
    "16": "chemistry",
    "13": "biology",
    "27": "medicine",
    "17": "computer_science",
    "31": "physics",
    "11": "biology",
    "24": "biology",
    "28": "biology",
}


def restore_abstract(index: dict[str, list[int]] | None) -> str:
    if not index:
        return ""
    positions: dict[int, str] = {}
    for word, offsets in index.items():
        if not isinstance(word, str) or not word or not isinstance(offsets, list):
            raise ValueError("invalid abstract token")
        for offset in offsets:
            if type(offset) is not int or offset < 0 or offset in positions:
                raise ValueError("invalid or duplicate abstract position")
            positions[offset] = word
    if sorted(positions) != list(range(len(positions))):
        raise ValueError("abstract has missing positions")
    return " ".join(positions[i] for i in range(len(positions)))


def normalize_work(work: dict[str, Any]) -> dict[str, Any]:
    paper_id = str(work.get("id", "")).rstrip("/").rsplit("/", 1)[-1]
    if not re.fullmatch(r"W\d+", paper_id):
        raise ValueError("invalid paper_id")
    topic = work.get("primary_topic") or {}
    field = topic.get("field") or {}
    field_id = str(field.get("id", "")).rsplit("/", 1)[-1]
    if field_id not in FIELD_DOMAINS:
        raise ValueError("missing or unsupported primary_topic.field")
    abstract = restore_abstract(work.get("abstract_inverted_index"))
    title, year = work.get("title"), work.get("publication_year")
    if not abstract or not isinstance(title, str) or not title.strip() or type(year) is not int:
        raise ValueError("missing abstract, title or year")
    return {
        "paper_id": paper_id,
        "title": title,
        "abstract": abstract,
        "year": year,
        "domain": FIELD_DOMAINS[field_id],
        "field": field.get("display_name", ""),
        "cited_by": work.get("cited_by_count", 0),
        "doi": work.get("doi"),
        "openalex_url": f"https://openalex.org/{paper_id}",
        "primary_topic": topic,
    }
