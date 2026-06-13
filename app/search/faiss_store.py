"""
ZenAI — Search: FAISS Store
Manages the FAISS vector index.
Handles: build, add, save, load, and similarity search.

Index file:   data/cache/faiss_index.bin
Mapping file: data/cache/faiss_map.json
  → maps FAISS position (int) to {"entity_type": str, "entity_id": int}
"""

from __future__ import annotations

import json
import os

import numpy as np

# ── Paths ──
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE_DIR = os.path.join(BASE_DIR, "data", "cache")
INDEX_PATH = os.path.join(CACHE_DIR, "faiss_index.bin")
MAP_PATH = os.path.join(CACHE_DIR, "faiss_map.json")

DIM = 384  # must match embedder.embedding_dim()


# ─────────────────────────────────────────────
# INTERNAL STATE (module-level singletons)
# ─────────────────────────────────────────────

_index = None          # faiss.IndexFlatIP
_id_map: list[dict] = []   # [{entity_type, entity_id}, ...]


def _get_faiss():
    import faiss
    return faiss


def _ensure_index():
    """Initialize an empty FAISS index if not already loaded."""
    global _index
    if _index is None:
        faiss = _get_faiss()
        _index = faiss.IndexFlatIP(DIM)  # Inner Product (cosine on normalized vectors)


# ─────────────────────────────────────────────
# SAVE / LOAD
# ─────────────────────────────────────────────

def save_index():
    """Persist FAISS index + ID map to disk."""
    global _index, _id_map
    if _index is None:
        return

    os.makedirs(CACHE_DIR, exist_ok=True)
    faiss = _get_faiss()
    faiss.write_index(_index, INDEX_PATH)

    with open(MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(_id_map, f)

    print(f"[ZenAI Search] Index saved — {_index.ntotal} vectors, map: {len(_id_map)} entries")


def load_index() -> bool:
    """
    Load FAISS index + ID map from disk.
    Returns True if loaded, False if no index file found.
    """
    global _index, _id_map

    if not os.path.isfile(INDEX_PATH) or not os.path.isfile(MAP_PATH):
        return False

    faiss = _get_faiss()
    _index = faiss.read_index(INDEX_PATH)

    with open(MAP_PATH, "r", encoding="utf-8") as f:
        _id_map = json.load(f)

    print(f"[ZenAI Search] Index loaded — {_index.ntotal} vectors")
    return True


def reset_index():
    """Wipe the in-memory index and map (does NOT delete disk files)."""
    global _index, _id_map
    faiss = _get_faiss()
    _index = faiss.IndexFlatIP(DIM)
    _id_map = []


def clear_disk_index():
    """Delete saved index files from disk."""
    for path in [INDEX_PATH, MAP_PATH]:
        if os.path.isfile(path):
            os.remove(path)
    print("[ZenAI Search] Disk index cleared.")


# ─────────────────────────────────────────────
# ADD VECTORS
# ─────────────────────────────────────────────

def add_vectors(
    vectors: np.ndarray,
    entity_type: str,
    entity_ids: list[int],
):
    """
    Add a batch of embeddings to the FAISS index.

    Args:
        vectors:     shape (N, 384) float32
        entity_type: e.g. 'character', 'faction', 'location'
        entity_ids:  list of DB integer ids, length N
    """
    global _index, _id_map
    _ensure_index()

    if vectors.shape[0] == 0:
        return

    _index.add(vectors)
    for eid in entity_ids:
        _id_map.append({"entity_type": entity_type, "entity_id": eid})


def add_single(vector: np.ndarray, entity_type: str, entity_id: int):
    """Add a single embedding to the index."""
    vec2d = vector.reshape(1, -1)
    add_vectors(vec2d, entity_type, [entity_id])


# ─────────────────────────────────────────────
# SEARCH
# ─────────────────────────────────────────────

def search_vectors(
    query_vector: np.ndarray,
    top_k: int = 10,
    entity_type: str = None,
) -> list[dict]:
    """
    Search the FAISS index for the most similar vectors.

    Args:
        query_vector: shape (384,) float32
        top_k:        number of results to return
        entity_type:  if set, filter results to only this entity type

    Returns:
        List of dicts: [{entity_type, entity_id, score}, ...]
        Sorted by score descending (1.0 = perfect match).
    """
    global _index, _id_map

    if _index is None or _index.ntotal == 0:
        return []

    # Fetch more than top_k if filtering by type, so we have enough after filter
    fetch_k = top_k * 5 if entity_type else top_k
    fetch_k = min(fetch_k, _index.ntotal)

    query = query_vector.reshape(1, -1).astype(np.float32)
    scores, indices = _index.search(query, fetch_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or idx >= len(_id_map):
            continue
        entry = _id_map[idx]
        if entity_type and entry["entity_type"] != entity_type:
            continue
        results.append({
            "entity_type": entry["entity_type"],
            "entity_id": entry["entity_id"],
            "score": float(score),
        })
        if len(results) >= top_k:
            break

    return results


def index_size() -> int:
    """Return total number of vectors in the index."""
    if _index is None:
        return 0
    return _index.ntotal
