"""文本向量。默认哈希嵌入，保证单测和 CI 不下载模型。

`embed_texts(..., backend="fastembed")` 才懒加载 fastembed。
模块导入本身不加载模型。
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


def embed_texts(texts: list[str], *, backend: str = "hash") -> np.ndarray:
    """按 backend 出向量。未知 backend 抛 ValueError。fastembed 不在本函数的默认路径上。"""
    if backend == "hash":
        return hash_embed(texts)
    if backend == "fastembed":
        return _fastembed(texts)
    raise ValueError(f"unknown embedding backend: {backend}")


def _fastembed(texts: list[str]) -> np.ndarray:
    from fastembed import TextEmbedding

    from ..common.config import get_settings

    model = TextEmbedding(model_name=get_settings().embed_model)
    rows = [np.asarray(vector, dtype=np.float32) for vector in model.embed(texts)]
    if not rows:
        return np.zeros((0, DIM), dtype=np.float32)
    stacked = np.vstack(rows)
    norms = np.linalg.norm(stacked, axis=1, keepdims=True)
    zero = norms == 0.0
    norms[zero] = 1.0
    return stacked / norms


def _grams(text: str) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return [""]
    if any("\u4e00" <= ch <= "\u9fff" for ch in stripped):
        if len(stripped) == 1:
            return [stripped]
        return [stripped[i : i + 2] for i in range(len(stripped) - 1)]
    return stripped.lower().split()
