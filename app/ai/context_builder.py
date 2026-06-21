"""
app/ai/context_builder.py

Pulls relevant, well-formatted context from the database before any
Claude generation call. Keeps prompts grounded in actual lore data
instead of letting Claude hallucinate world details.

All functions return PLAIN STRINGS ready to drop into a prompt's
system or user content. Keep these concise — token budget matters.
"""
from typing import Optional

from app.database import crud
from app.search.search import search as semantic_search


# ----------------------------------------------------------------------
# Low-level formatters
# ----------------------------------------------------------------------
def _fmt_entity(entity, entity_type: str) -> str:
    """Generic one-line summary for any entity with name/description."""
    name = getattr(entity, "name", "Unknown")
    uuid = getattr(entity, "uuid", "")
    desc = getattr(entity, "description", "") or ""
    canon = getattr(entity, "canon_status", "canon")
    importance = getattr(entity, "importance_score", "?")
    desc_short = (desc[:200] + "...") if len(desc) > 200 else desc
    return f"- [{entity_type}] {name} ({uuid}) | canon={canon} | importance={importance}\n  {desc_short}"


def _fmt_block(title: str, lines: list[str]) -> str:
    if not lines:
        return ""
    return f"## {title}\n" + "\n".join(lines) + "\n"


# ----------------------------------------------------------------------
# Entity-specific context
# ----------------------------------------------------------------------
def build_character_context(session, character_id: int) -> str:
    """Full context for a single character: self, faction, powers, relationships, events."""
    char = crud.get_character(session, character_id)
    if not char:
        return ""

    parts = [_fmt_block("Character", [_fmt_entity(char, "character")])]

    # Powers
    powers = crud.list_character_powers(session, character_id)
    if powers:
        power_lines = [f"- {getattr(p, 'name', '?')}: {getattr(p, 'description', '')[:120]}" for p in powers]
        parts.append(_fmt_block("Powers", power_lines))

    # Faction — find any faction where this character is the founder
    from app.database.models import Faction as _Faction
    founded_factions = session.query(_Faction).filter(
        _Faction.founder_id == character_id
    ).all()
    if founded_factions:
        faction_lines = [_fmt_entity(f, "faction") for f in founded_factions]
        parts.append(_fmt_block("Founded Factions", faction_lines))

    # Variants (alternate versions)
    if hasattr(crud, "list_character_variants"):
        variants = crud.list_character_variants(session, character_id)
        if variants:
            var_lines = [_fmt_entity(v, "character") for v in variants]
            parts.append(_fmt_block("Alternate Versions", var_lines))

    return "\n".join(p for p in parts if p)


def build_universe_context(session, universe_id: int, max_per_type: int = 10) -> str:
    """High-level context for an entire universe: top characters, factions, locations, events."""
    universe = crud.get_universe(session, universe_id)
    if not universe:
        return ""

    parts = [_fmt_block("Universe", [_fmt_entity(universe, "universe")])]

    characters = crud.list_characters(session, universe_id=universe_id)[:max_per_type]
    if characters:
        parts.append(_fmt_block("Key Characters", [_fmt_entity(c, "character") for c in characters]))

    factions = crud.list_factions(session, universe_id=universe_id)[:max_per_type]
    if factions:
        parts.append(_fmt_block("Factions", [_fmt_entity(f, "faction") for f in factions]))

    locations = crud.list_locations(session, universe_id=universe_id)[:max_per_type]
    if locations:
        parts.append(_fmt_block("Locations", [_fmt_entity(l, "location") for l in locations]))

    events = crud.list_events(session, universe_id=universe_id)[:max_per_type]
    if events:
        parts.append(_fmt_block("Major Events", [_fmt_entity(e, "event") for e in events]))

    return "\n".join(p for p in parts if p)


def build_root_entity_context(session, root_entity_id: int) -> str:
    """Context for a root entity and its cross-universe links."""
    root = crud.get_root_entity(session, root_entity_id)
    if not root:
        return ""

    parts = [_fmt_block("Root Entity", [_fmt_entity(root, "root_entity")])]

    if hasattr(crud, "list_root_entity_links"):
        links = crud.list_root_entity_links(session, root_entity_id)
        if links:
            link_lines = []
            for link in links:
                uni_id = getattr(link, "universe_id", None)
                uni = crud.get_universe(session, uni_id) if uni_id else None
                uni_name = getattr(uni, "name", "Unknown universe") if uni else "Unknown universe"
                role = getattr(link, "role", "") or getattr(link, "link_type", "")
                link_lines.append(f"- Appears in {uni_name} as: {role}")
            parts.append(_fmt_block("Cross-Universe Presence", link_lines))

    return "\n".join(p for p in parts if p)


# ----------------------------------------------------------------------
# Search-driven context (for free-form queries / story prompts)
# ----------------------------------------------------------------------
# def build_search_context(session, query: str, entity_type: Optional[str] = None,
#                           top_k: int = 5) -> str:
#     """
#     Run semantic search against the lore DB and format the top results
#     as context. Useful when the user gives a free-form prompt and we
#     need to find what's relevant before generating.
#     """
#     results = semantic_search(session, query, entity_type=entity_type)
#     results = results[:top_k]
#     if not results:
#         return ""

#     lines = []
#     for r in results:
#         # search() result shape per Module 6: dict-like with entity_type, id, name, description, score
#         etype = r.get("entity_type", "?") if isinstance(r, dict) else getattr(r, "entity_type", "?")
#         name = r.get("name", "?") if isinstance(r, dict) else getattr(r, "name", "?")
#         uuid = r.get("uuid", "") if isinstance(r, dict) else getattr(r, "uuid", "")
#         desc = r.get("description", "") if isinstance(r, dict) else getattr(r, "description", "")
#         desc_short = (desc[:150] + "...") if desc and len(desc) > 150 else (desc or "")
#         lines.append(f"- [{etype}] {name} ({uuid})\n  {desc_short}")

#     return _fmt_block(f"Relevant Lore (search: \"{query}\")", lines)
def build_search_context(session, query: str, entity_type: Optional[str] = None,
                          top_k: int = 5) -> str:
    results = semantic_search(session, query, entity_type=entity_type)
    results = results[:top_k]
    if not results:
        return ""

    from app.database import crud

    GETTERS = {
        "character": crud.get_character,
        "faction": crud.get_faction,
        "location": crud.get_location,
        "event": crud.get_event,
        "artifact": crud.get_artifact,
        "story": crud.get_story,
    }

    lines = []
    seen = set()
    for r in results:
        etype = r.get("entity_type")
        eid = r.get("entity_id")
        key = (etype, eid)
        if key in seen:
            continue
        seen.add(key)

        getter = GETTERS.get(etype)
        if not getter:
            continue
        obj = getter(session, eid)
        if not obj:
            continue

        lines.append(_fmt_entity(obj, etype))

    if not lines:
        return ""

    return _fmt_block(f"Relevant Lore (search: \"{query}\")", lines)

# ----------------------------------------------------------------------
# Combined builder
# ----------------------------------------------------------------------
def build_context(session, entity_type: str, entity_id: Optional[int] = None,
                   query: Optional[str] = None) -> str:
    """
    General-purpose entry point. Dispatches to the right builder based
    on entity_type, optionally appending search context for a free-form
    query.

    entity_type ∈ {character, universe, root_entity, search}
    """
    parts = []

    if entity_type == "character" and entity_id:
        parts.append(build_character_context(session, entity_id))
    elif entity_type == "universe" and entity_id:
        parts.append(build_universe_context(session, entity_id))
    elif entity_type == "root_entity" and entity_id:
        parts.append(build_root_entity_context(session, entity_id))

    if query:
        parts.append(build_search_context(session, query, entity_type=None))

    return "\n".join(p for p in parts if p)
