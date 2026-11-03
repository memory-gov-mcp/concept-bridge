"""保守的概念与条件归一。规则变更时递增版本。"""

import hashlib
import re
import unicodedata

NORMALIZER_VERSION = "norm-v1"
PLURALS = {
    "membranes": "membrane",
    "ions": "ion",
    "channels": "channel",
    "cells": "cell",
    "proteins": "protein",
    "gradients": "gradient",
}
ALIASES = {
    ("biology", "structure", "细胞膜"): "cell membrane",
    ("biology", "structure", "plasma membrane"): "cell membrane",
    ("materials_science", "structure", "solid electrolyte interphase"): "SEI",
}
CONDITIONS = {
    "浓度梯度": "concentration_gradient",
    "concentration gradient": "concentration_gradient",
    "电场": "electric_field",
    "electric field": "electric_field",
    "膜电位": "membrane_potential",
    "membrane potential": "membrane_potential",
    "高温": "high_temperature",
    "high temperature": "high_temperature",
}


def canonical_name(surface: str) -> str:
    text = unicodedata.normalize("NFKC", surface).strip()
    text = re.sub(r"[-‐‑–—_]", " ", text)
    text = re.sub(r"\s*([()])\s*", r"\1", text)
    words = text.split()
    # Preserve uppercase abbreviations and mixed-case chemical formulae.
    words = [
        word.lower()
        if (word.istitle() and len(word) > 2)
        or word.lower() in PLURALS
        or word.lower() in PLURALS.values()
        else word
        for word in words
    ]
    return " ".join(PLURALS.get(word, word) for word in words)


def concept(domain: str, kind: str, surface: str) -> tuple[str, str]:
    name = canonical_name(surface)
    name = ALIASES.get((domain, kind, name), name)
    if not name:
        raise ValueError("empty concept")
    key = "\0".join((domain, kind, name))
    return "c_" + hashlib.sha256(key.encode()).hexdigest()[:24], name


def condition_key(surface: str) -> str:
    name = canonical_name(surface).lower()
    if not name:
        raise ValueError("empty condition")
    return CONDITIONS.get(name, name.replace(" ", "_"))
