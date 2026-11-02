"""文本向量。默认哈希嵌入，保证单测和 CI 不下载模型。

生产索引若要换 fastembed，调用方显式传 backend="fastembed"。
这里不在 import 时加载模型。
"""

from __future__ import annotations

import hashlib

import numpy as np

DIM = 64


def hash_embed(texts: list[str], dim: int = DIM) -> np.ndarray:
    """特征哈希后的 L2 归一化向量，dtype float32。"""
    out = np.zeros((len(texts), dim), dtype=np.float32)
    for row, text in enumerate(texts):
        grams = _grams(text)
        for gram in grams:
            digest = hashlib.sha256(gram.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], "little") % dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            out[row, bucket] += sign
        norm = float(np.linalg.norm(out[row]))
        if norm == 0.0:
            out[row, 0] = 1.0
        else:
            out[row] /= norm
    return out


def _grams(text: str) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return [""]
    if any("\u4e00" <= ch <= "\u9fff" for ch in stripped):
        if len(stripped) == 1:
            return [stripped]
        return [stripped[i : i + 2] for i in range(len(stripped) - 1)]
    return stripped.lower().split()
