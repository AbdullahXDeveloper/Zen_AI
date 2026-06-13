"""
ZenAI — Search: Public API
The only file other modules should import from.

Usage:
    from app.search.search import search, search_exact, rebuild_index

    results = search("ruthless warrior who betrayed his faction")
    results = search("Raven", entity_type="character")
    results = search_exact("character", "species", "Human")
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.models import (
    Character, Faction, Location,
    Event, Artifact, Story,
)
from app.search.embedder import embed_text
from app.search import faiss_store
from app.search.indexer import rebuild_index as _rebuild_index, index_entity


# ─────────────────────────────────────────────
# EXACT SEARCH
# ─────────────────────────────────────────────

# Maps entity_type → (model_class, searchable fields)
EXACT_SEARCH_MAP = {
    "character": (Character, ["name", "titles", "aliases", "species", "personality", "motivations", "goals", "ideology"]),
    "faction":   (Faction,   ["name", "ideology", "description"]),
    "location":  (Location,  ["name", "type", "description"]),
    "event":     (Event,     ["name", "event_type", "date_label", "description"]),
    "artifact":  (Artifact,  ["name", "description"]),
    "story":     (Story,     ["title", "summary", "story_mode"]),
}


def search_exact(
    session: Session,
    entity_type: str,
    field: str,
    value: str,
) -> list[dict]:
    """
    Exact (ILIKE) field search on one entity type.

    Args:
        session:     SQLAlchemy session
        entity_type: 'character' | 'faction' | 'location' | 'event' | 'artifact' | 'story'
        field:       column name to search (must be in EXACT_SEARCH_MAP)
        value:       search term (case-insensitive partial match)

    Returns:
        List of dicts: [{entity_type, entity_id, name, score=1.0}, ...]
    """
    if entity_type not in EXACT_SEARCH_MAP:
        raise ValueError(f"Unknown entity_type '{entity_type}'.")

    model_class, allowed_fields = EXACT_SEARCH_MAP[entity_type]

    if field not in allowed_fields:
        raise ValueError(
            f"Field '{field}' not searchable for '{entity_type}'. "
            f"Allowed: {allowed_fields}"
        )

    col = getattr(model_class, field)
    rows = session.query(model_class).filter(col.ilike(f"%{value}%")).all()

    results = []
    for row in rows:
        results.append({
            "entity_type": entity_type,
            "entity_id": row.id,
            "name": getattr(row, "name", None) or getattr(row, "title", str(row.id)),
            "score": 1.0,
            "match_type": "exact",
        })
    return results


# ─────────────────────────────────────────────
# SEMANTIC SEARCH
# ─────────────────────────────────────────────

def search_semantic(
    session: Session,
    query: str,
    entity_type: str = None,
    top_k: int = 10,
) -> list[dict]:
    """
    Semantic vector search using FAISS.

    Args:
        session:     SQLAlchemy session (used to resolve names)
        query:       free-text search query
        entity_type: optional filter (None = search all types)
        top_k:       max results to return

    Returns:
        List of dicts: [{entity_type, entity_id, name, score, match_type='semantic'}, ...]
    """
    query_vec = embed_text(query)
    raw_results = faiss_store.search_vectors(query_vec, top_k=top_k, entity_type=entity_type)

    # Resolve entity names from DB
    enriched = []
    for r in raw_results:
        name = _resolve_name(session, r["entity_type"], r["entity_id"])
        enriched.append({
            "entity_type": r["entity_type"],
            "entity_id": r["entity_id"],
            "name": name,
            "score": r["score"],
            "match_type": "semantic",
        })
    return enriched


# ─────────────────────────────────────────────
# COMBINED SEARCH (main public function)
# ─────────────────────────────────────────────

def search(
    session: Session,
    query: str,
    entity_type: str = None,
    top_k: int = 10,
) -> list[dict]:
    """
    Hybrid search: exact matches first, then semantic, deduplicated.

    Args:
        session:     SQLAlchemy session
        query:       free-text search query
        entity_type: optional filter — None searches all entity types
        top_k:       max total results

    Returns:
        List of dicts sorted by relevance:
        [{entity_type, entity_id, name, score, match_type}, ...]
        Exact matches always appear before semantic matches.
    """
    results: list[dict] = []
    seen: set[tuple] = set()  # (entity_type, entity_id)

    # ── Step 1: Exact search ──
    types_to_search = [entity_type] if entity_type else list(EXACT_SEARCH_MAP.keys())

    for etype in types_to_search:
        model_class, fields = EXACT_SEARCH_MAP[etype]
        # Search name field for exact matches
        name_field = "title" if etype == "story" else "name"
        if name_field in fields:
            for row in _exact_name_search(session, etype, model_class, name_field, query):
                key = (row["entity_type"], row["entity_id"])
                if key not in seen:
                    seen.add(key)
                    results.append(row)

    # ── Step 2: Semantic search ──
    semantic = search_semantic(session, query, entity_type=entity_type, top_k=top_k * 2)
    for row in semantic:
        key = (row["entity_type"], row["entity_id"])
        if key not in seen:
            seen.add(key)
            results.append(row)

    # ── Step 3: Sort (exact first, then by score desc) ──
    results.sort(key=lambda r: (0 if r["match_type"] == "exact" else 1, -r["score"]))

    return results[:top_k]


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _exact_name_search(session, entity_type, model_class, field, value) -> list[dict]:
    col = getattr(model_class, field)
    rows = session.query(model_class).filter(col.ilike(f"%{value}%")).all()
    return [
        {
            "entity_type": entity_type,
            "entity_id": row.id,
            "name": getattr(row, "name", None) or getattr(row, "title", str(row.id)),
            "score": 1.0,
            "match_type": "exact",
        }
        for row in rows
    ]


def _resolve_name(session: Session, entity_type: str, entity_id: int) -> str:
    """Fetch the display name of any entity by type + id."""
    if entity_type not in EXACT_SEARCH_MAP:
        return f"{entity_type}#{entity_id}"

    model_class, _ = EXACT_SEARCH_MAP[entity_type]
    obj = session.query(model_class).filter(model_class.id == entity_id).first()
    if not obj:
        return f"{entity_type}#{entity_id}"

    return getattr(obj, "name", None) or getattr(obj, "title", str(entity_id))


# ─────────────────────────────────────────────
# RE-EXPORTS (so other modules only import from here)
# ─────────────────────────────────────────────

def rebuild_index(session: Session) -> int:
    """Rebuild the full FAISS index from DB. Returns total entities indexed."""
    return _rebuild_index(session)


def index_single_entity(entity_type: str, entity_id: int, session: Session):
    """
    Index one entity after create/update.
    Call this from CRUD layer hooks or after AI generation approval.
    """
    index_entity(entity_type, entity_id, session)
    faiss_store.save_index()
