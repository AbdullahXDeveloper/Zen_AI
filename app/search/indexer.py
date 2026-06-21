"""
ZenAI — Search: Indexer
Pulls entity data from the DB, generates embeddings, and stores in FAISS.

Called:
  - On app startup (load_index or rebuild_index)
  - After any entity create/update (index_entity)
  - After CSV import (rebuild_index)
"""

from __future__ import annotations

import numpy as np
from sqlalchemy.orm import Session

from app.database.models import (
    Character, Faction, Location,
    Event, Artifact, Story,
)
from app.search.embedder import embed_text, embed_batch
from app.search import faiss_store


# ─────────────────────────────────────────────
# TEXT EXTRACTION PER ENTITY TYPE
# Combine the most useful text fields into one string for embedding.
# ─────────────────────────────────────────────

def _character_text(c: Character) -> str:
    parts = [
        c.name or "",
        c.titles or "",
        c.aliases or "",
        c.species or "",
        c.personality or "",
        c.motivations or "",
        c.goals or "",
        c.ideology or "",
    ]
    return " ".join(p for p in parts if p).strip()


def _faction_text(f: Faction) -> str:
    parts = [f.name or "", f.ideology or "", f.description or ""]
    return " ".join(p for p in parts if p).strip()


def _location_text(l: Location) -> str:
    parts = [l.name or "", l.type or "", l.description or ""]
    return " ".join(p for p in parts if p).strip()


def _event_text(e: Event) -> str:
    parts = [e.name or "", e.event_type or "", e.date_label or "", e.description or ""]
    return " ".join(p for p in parts if p).strip()


def _artifact_text(a: Artifact) -> str:
    parts = [a.name or "", a.description or ""]
    return " ".join(p for p in parts if p).strip()


def _story_text(s: Story) -> str:
    parts = [s.title or "", s.summary or ""]
    return " ".join(p for p in parts if p).strip()


# ─────────────────────────────────────────────
# ENTITY TYPE CONFIG
# ─────────────────────────────────────────────

ENTITY_CONFIG = {
    "character": (Character, _character_text),
    "faction":   (Faction,   _faction_text),
    "location":  (Location,  _location_text),
    "event":     (Event,     _event_text),
    "artifact":  (Artifact,  _artifact_text),
    "story":     (Story,     _story_text),
}


# ─────────────────────────────────────────────
# INDEX A SINGLE ENTITY (called on create/update)
# ─────────────────────────────────────────────

def index_entity(entity_type: str, entity_id: int, session: Session):
    """
    Generate embedding for one entity and add to FAISS index.
    Does NOT save to disk — call faiss_store.save_index() after.

    Args:
        entity_type: one of the ENTITY_CONFIG keys
        entity_id:   DB integer id
        session:     SQLAlchemy session
    """
    if entity_type not in ENTITY_CONFIG:
        return

    model_class, text_fn = ENTITY_CONFIG[entity_type]
    obj = session.query(model_class).filter(model_class.id == entity_id).first()
    if not obj:
        return

    text = text_fn(obj)
    vector = embed_text(text)
    faiss_store.add_single(vector, entity_type, entity_id)


# ─────────────────────────────────────────────
# REBUILD INDEX (bulk — all entities)
# ─────────────────────────────────────────────

def rebuild_index(session: Session):
    """
    Wipe and rebuild the entire FAISS index from scratch.
    Use after: initial setup, CSV bulk import, schema changes.

    Saves index to disk when done.
    """
    print("[ZenAI Search] Rebuilding index from DB...")
    faiss_store.reset_index()

    total = 0
    for entity_type, (model_class, text_fn) in ENTITY_CONFIG.items():
        rows = session.query(model_class).all()
        if not rows:
            continue

        texts = [text_fn(r) for r in rows]
        ids = [r.id for r in rows]

        vectors = embed_batch(texts)

        faiss_store.add_vectors(vectors, entity_type, ids)
        total += len(rows)
        print(f"  [ZenAI Search] Indexed {len(rows)} {entity_type}(s)")

    faiss_store.save_index()
    print(f"[ZenAI Search] Rebuild complete — {total} entities indexed.")
    return total


# ─────────────────────────────────────────────
# STARTUP LOADER
# ─────────────────────────────────────────────

def load_or_rebuild(session: Session):
    """
    Try to load existing index from disk.
    If not found, rebuild from DB.
    Call this on app startup.
    """
    loaded = faiss_store.load_index()
    if not loaded:
        print("[ZenAI Search] No index found — building from scratch...")
        rebuild_index(session)
    else:
        print(f"[ZenAI Search] Index ready — {faiss_store.index_size()} vectors loaded.")
