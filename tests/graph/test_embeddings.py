"""哈希嵌入：单测与 CI 不下载向量模型。"""

from __future__ import annotations

import numpy as np
import pytest

from conceptbridge.graph.embeddings import _with_e5_prefix, embed_texts, hash_embed


def test_hash_embed_is_deterministic_unit_vectors() -> None:
    left = hash_embed(["SEI membrane", "plasma membrane"])
    right = hash_embed(["SEI membrane", "plasma membrane"])
    assert left.shape == (2, 64)
    assert left.dtype == np.float32
    assert np.allclose(left, right)
    norms = np.linalg.norm(left, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-5)


def test_different_texts_are_not_identical() -> None:
    vectors = hash_embed(["锂枝晶", "细胞膜"])
    assert not np.allclose(vectors[0], vectors[1])


def test_embed_texts_hash_matches_hash_embed() -> None:
    texts = ["SEI membrane", "锂枝晶"]
    got = embed_texts(texts, backend="hash")
    assert got.shape == (2, 64)
    assert got.dtype == np.float32
    assert np.allclose(got, hash_embed(texts))


def test_embed_texts_rejects_unknown_backend() -> None:
    with pytest.raises(ValueError):
        embed_texts(["SEI membrane"], backend="faiss")


def test_import_does_not_load_fastembed() -> None:
    import sys

    assert "fastembed" not in sys.modules


def test_e5_prefix_is_applied_once() -> None:
    model = "intfloat/multilingual-e5-large"
    assert _with_e5_prefix(["SEI membrane"], model) == ["query: SEI membrane"]
    assert _with_e5_prefix(["query: SEI"], model) == ["query: SEI"]
    assert _with_e5_prefix(["passage: SEI"], model) == ["passage: SEI"]
    assert _with_e5_prefix(["SEI"], "bge-small") == ["SEI"]
