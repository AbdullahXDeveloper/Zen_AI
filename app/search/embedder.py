"""
ZenAI — Search: Embedder
Sentence Transformers wrapper for generating text embeddings.
Model is loaded once and reused across all calls.
"""

from __future__ import annotations

import numpy as np

# Lazy import so app starts fast even if model not downloaded yet
_model = None
MODEL_NAME = "all-MiniLM-L6-v2"  # fast, good quality, 384-dim


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        print(f"[ZenAI Search] Loading embedding model: {MODEL_NAME}")
        _model = SentenceTransformer(MODEL_NAME)
        print("[ZenAI Search] Model loaded.")
    return _model


def embed_text(text: str) -> np.ndarray:
    """
    Generate a 384-dim float32 embedding for a single string.
    Returns numpy array shape (384,).
    """
    if not text or not text.strip():
        # Return zero vector for empty text
        return np.zeros(384, dtype=np.float32)

    model = _get_model()
    vec = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
    return vec.astype(np.float32)


def embed_batch(texts: list[str]) -> np.ndarray:
    """
    Generate embeddings for a list of strings.
    Returns numpy array shape (N, 384).
    """
    if not texts:
        return np.zeros((0, 384), dtype=np.float32)

    # Replace empty strings with a space so model doesn't crash
    cleaned = [t.strip() if t and t.strip() else " " for t in texts]

    model = _get_model()
    vecs = model.encode(cleaned, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)
    return vecs.astype(np.float32)


def embedding_dim() -> int:
    """Return the embedding dimension (384 for MiniLM)."""
    return 384
