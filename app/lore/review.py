"""
app/lore/review.py

PHASE 3 of the ingestion pipeline: Human Review (Approve/Reject/Edit)
and persistence to the database.

The UI (Module 8) shows the merged extraction result from extractor.py
to the user as a list of proposed entities/relationships. For each item
the user can:
  - Approve  -> persisted via CRUD layer (create or link)
  - Edit     -> user modifies fields, then Approve
  - Reject   -> discarded, nothing happens

This module provides the persistence functions called on Approve, plus
a helper to resolve entity names to DB ids (for relationships/events
that reference other entities by name).
"""
from typing import Optional

from app.database import crud


# ----------------------------------------------------------------------
# Name -> ID resolution
# ----------------------------------------------------------------------
def _find_entity_by_name(session, name: str) -> Optional[dict]:
    """
    Search across entity types for an exact (case-insensitive) name match.
    Returns {"entity_type": str, "id": int, "uuid": str} or None.
    """
    name_lower = name.strip().lower()

    lookups = [
        ("character", crud.list_characters),
        ("faction", crud.list_factions),
        ("location", crud.list_locations),
        ("event", crud.list_events),
        ("artifact", crud.list_artifacts),
        ("universe", crud.list_universes),
    ]
    if hasattr(crud, "list_root_entities"):
        lookups.append(("root_entity", crud.list_root_entities))

    for entity_type, list_fn in lookups:
        try:
            entities = list_fn(session)
        except TypeError:
            entities = []
        for ent in entities:
            ent_name = getattr(ent, "name", None)
            if ent_name and ent_name.strip().lower() == name_lower:
                return {"entity_type": entity_type, "id": ent.id, "uuid": getattr(ent, "uuid", "")}

    return None


# ----------------------------------------------------------------------
# Approve: create new entities
# ----------------------------------------------------------------------
def approve_character(session, item: dict, universe_id: Optional[int] = None,
                       canon_status: str = "canon") -> object:
    """Persist an approved character extraction item. Returns the created Character."""
    return crud.create_character(
        session,
        name=item["name"],
        description=item.get("description", ""),
        universe_id=universe_id,
        importance_score=item.get("importance_score", 5),
        canon_status=item.get("canon_status", canon_status),
    )


def approve_faction(session, item: dict, universe_id: Optional[int] = None,
                     canon_status: str = "canon") -> object:
    """Persist an approved faction extraction item. Returns the created Faction."""
    return crud.create_faction(
        session,
        name=item["name"],
        description=item.get("description", ""),
        universe_id=universe_id,
        importance_score=item.get("importance_score", 5),
        canon_status=item.get("canon_status", canon_status),
    )


def approve_location(session, item: dict, universe_id: Optional[int] = None,
                      canon_status: str = "canon") -> object:
    """Persist an approved location extraction item. Returns the created Location."""
    return crud.create_location(
        session,
        name=item["name"],
        description=item.get("description", ""),
        universe_id=universe_id,
        importance_score=item.get("importance_score", 5),
        canon_status=item.get("canon_status", canon_status),
    )


def approve_artifact(session, item: dict, universe_id: Optional[int] = None,
                      canon_status: str = "canon") -> object:
    """Persist an approved artifact extraction item. Returns the created Artifact."""
    return crud.create_artifact(
        session,
        name=item["name"],
        description=item.get("description", ""),
        universe_id=universe_id,
        importance_score=item.get("importance_score", 5),
        canon_status=item.get("canon_status", canon_status),
    )


def approve_event(session, item: dict, universe_id: Optional[int] = None,
                   canon_status: str = "canon", auto_link_participants: bool = True) -> object:
    """
    Persist an approved event extraction item. If auto_link_participants
    is True, attempts to resolve item["participants"] (names) against
    existing/just-created entities and link them via
    add_event_participant. Unresolved names are skipped silently
    (caller can surface them for manual linking).

    Returns the created Event.
    """
    event = crud.create_event(
        session,
        name=item["name"],
        description=item.get("description", ""),
        event_type=item.get("event_type", "other"),
        date_value=item.get("date_value"),
        universe_id=universe_id,
        importance_score=item.get("importance_score", 5),
        canon_status=item.get("canon_status", canon_status),
    )

    unresolved = []
    if auto_link_participants and hasattr(crud, "add_event_participant"):
        for name in item.get("participants", []):
            match = _find_entity_by_name(session, name)
            if match:
                crud.add_event_participant(
                    session, event_id=event.id,
                    entity_type=match["entity_type"], entity_id=match["id"],
                )
            else:
                unresolved.append(name)

    if unresolved:
        # Attach for caller visibility; not a DB field, just runtime info
        setattr(event, "_unresolved_participants", unresolved)

    return event


def approve_relationship(session, item: dict) -> Optional[object]:
    """
    Persist an approved relationship extraction item. Resolves entity_a
    and entity_b by name; if either is not found, returns None and the
    caller should surface this for manual resolution (the entity may
    need to be approved first).

    Returns the created relationship record, or None if unresolved.
    """
    a = _find_entity_by_name(session, item["entity_a"])
    b = _find_entity_by_name(session, item["entity_b"])

    if not a or not b:
        return None

    if not hasattr(crud, "create_relationship"):
        return None

    return crud.create_relationship(
        session,
        entity_a_type=a["entity_type"], entity_a_id=a["id"],
        entity_b_type=b["entity_type"], entity_b_id=b["id"],
        relationship_type=item.get("relationship_type", "other"),
        description=item.get("description", ""),
    )


# ----------------------------------------------------------------------
# Batch approval (UI calls this after user reviews a whole extraction)
# ----------------------------------------------------------------------
_APPROVERS = {
    "character": approve_character,
    "faction": approve_faction,
    "location": approve_location,
    "artifact": approve_artifact,
    "event": approve_event,
}


def approve_all(session, merged_result: dict, approved_indices: dict[str, list[int]],
                 universe_id: Optional[int] = None, canon_status: str = "canon") -> dict:
    """
    Process a batch of approvals from the review UI.

    merged_result: output of extractor.merge_extraction_results()
    approved_indices: {"characters": [0, 2], "factions": [1], ...,
                        "relationships": [0]}
                       — indices into merged_result[key] that the user approved.
                       Items not listed are treated as rejected (skipped).

    Returns: {
      "created": {"characters": [Character, ...], ...},
      "unresolved_relationships": [item, ...],
      "events_with_unresolved_participants": [(Event, [names]), ...]
    }
    """
    created: dict[str, list] = {k: [] for k in _APPROVERS}
    unresolved_relationships = []
    events_with_unresolved = []

    # Entities first (so relationships/event participants can resolve against them)
    for key, approver in _APPROVERS.items():
        indices = approved_indices.get(key, [])
        items = merged_result.get(key + "s" if key != "artifacts" else "artifacts", [])
        # handle pluralization: characters/factions/locations/events/artifacts
        plural_key = {
            "character": "characters", "faction": "factions",
            "location": "locations", "artifact": "artifacts", "event": "events",
        }[key]
        items = merged_result.get(plural_key, [])

        for idx in indices:
            if idx >= len(items):
                continue
            item = items[idx]
            obj = approver(session, item, universe_id=universe_id, canon_status=canon_status)
            created[key].append(obj)

            if key == "event" and getattr(obj, "_unresolved_participants", None):
                events_with_unresolved.append((obj, obj._unresolved_participants))

    # Relationships last
    for idx in approved_indices.get("relationships", []):
        rels = merged_result.get("relationships", [])
        if idx >= len(rels):
            continue
        item = rels[idx]
        result = approve_relationship(session, item)
        if result is None:
            unresolved_relationships.append(item)

    return {
        "created": created,
        "unresolved_relationships": unresolved_relationships,
        "events_with_unresolved_participants": events_with_unresolved,
    }
