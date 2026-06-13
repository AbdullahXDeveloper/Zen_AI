"""
app/ai/lore_generator.py

Generates new lore entities (characters, factions, locations, events,
universes, artifacts) as structured JSON using Claude, grounded in
existing DB context.

KEY RULE: This module NEVER writes to the database. It only returns
JSON dicts. The UI layer must show the user an Approve/Reject/Edit
screen, and only on Approve does it call the CRUD layer to persist.
"""
from typing import Optional

from app.ai.claude_client import get_client
from app.ai.context_builder import build_universe_context, build_character_context


# ----------------------------------------------------------------------
# JSON schemas (as prompt instructions — keep in sync with models.py)
# ----------------------------------------------------------------------
_SCHEMAS = {
    "character": """{
  "name": "string",
  "description": "string (2-4 paragraphs)",
  "canon_status": "canon | non_canon | alt_timeline | experimental",
  "importance_score": "integer 1-100",
  "traits_json": {"personality": ["..."], "appearance": "...", "goals": ["..."]},
  "faction_suggestion": "string or null (name of existing or new faction)",
  "powers_suggestion": ["string", "..."]
}""",
    "faction": """{
  "name": "string",
  "description": "string (2-4 paragraphs)",
  "canon_status": "canon | non_canon | alt_timeline | experimental",
  "importance_score": "integer 1-100",
  "founder_suggestion": "string or null",
  "ideology": "string",
  "notable_members_suggestion": ["string", "..."]
}""",
    "location": """{
  "name": "string",
  "description": "string (2-4 paragraphs)",
  "canon_status": "canon | non_canon | alt_timeline | experimental",
  "importance_score": "integer 1-100",
  "location_type": "string (e.g. city, planet, dimension, building)",
  "notable_features": ["string", "..."]
}""",
    "event": """{
  "name": "string",
  "description": "string (2-4 paragraphs)",
  "canon_status": "canon | non_canon | alt_timeline | experimental",
  "importance_score": "integer 1-100",
  "event_type": "birth | death | rebirth | war | other",
  "date_value": "string (in-universe date, free text)",
  "participants_suggestion": ["string", "..."]
}""",
    "universe": """{
  "name": "string",
  "description": "string (3-5 paragraphs covering tone, history, key themes)",
  "canon_status": "canon | non_canon | alt_timeline | experimental",
  "importance_score": "integer 1-100",
  "core_concept": "string (1-2 sentences, the central 'what if')",
  "connections_suggestion": ["string (names of related universes)", "..."]
}""",
    "artifact": """{
  "name": "string",
  "description": "string (2-3 paragraphs)",
  "canon_status": "canon | non_canon | alt_timeline | experimental",
  "importance_score": "integer 1-100",
  "powers_suggestion": ["string", "..."],
  "origin_suggestion": "string"
}""",
}

_ENTITY_TYPES = list(_SCHEMAS.keys())


# ----------------------------------------------------------------------
# Core generation
# ----------------------------------------------------------------------
def generate_entity(session, entity_type: str, prompt: str,
                     universe_id: Optional[int] = None,
                     related_character_id: Optional[int] = None,
                     extra_instructions: Optional[str] = None) -> dict:
    """
    Generate a single new entity of the given type.

    entity_type: one of character, faction, location, event, universe, artifact
    prompt: free-form user instruction describing what to generate
    universe_id: if given, pulls universe context to keep it consistent
    related_character_id: if given, pulls character context too
    extra_instructions: additional constraints appended to the system prompt

    Returns: dict matching the schema for entity_type (NOT yet saved to DB)
    """
    if entity_type not in _SCHEMAS:
        raise ValueError(f"Unknown entity_type '{entity_type}'. Must be one of {_ENTITY_TYPES}")

    context_parts = []
    if universe_id:
        ctx = build_universe_context(session, universe_id)
        if ctx:
            context_parts.append(ctx)
    if related_character_id:
        ctx = build_character_context(session, related_character_id)
        if ctx:
            context_parts.append(ctx)

    context_str = "\n".join(context_parts) if context_parts else "(No existing context provided.)"

    system = (
        "You are the lore engine for Zen AI, a worldbuilding tool for the Zendrix multiverse. "
        "You generate new lore entities that fit consistently with existing canon. "
        "Be creative but respect established facts in the provided context. "
        "Never contradict existing entities. "
        f"{extra_instructions or ''}"
    )

    user_prompt = (
        f"## Existing Context\n{context_str}\n\n"
        f"## Task\nGenerate a new {entity_type} based on this request:\n\"{prompt}\"\n\n"
        f"## Required JSON Schema\n{_SCHEMAS[entity_type]}\n\n"
        f"Return a single JSON object matching this schema exactly."
    )

    client = get_client()
    result = client.ask_json(user_prompt, system=system, temperature=0.9)

    if not isinstance(result, dict):
        raise ValueError(f"Expected JSON object for {entity_type}, got: {type(result)}")

    result["_entity_type"] = entity_type  # tag for UI routing, strip before CRUD insert
    return result


def generate_batch(session, entity_type: str, prompt: str, count: int = 3,
                    universe_id: Optional[int] = None) -> list[dict]:
    """
    Generate multiple entities of the same type in one call (e.g. "give me
    5 soldiers for this faction"). More efficient than calling generate_entity
    in a loop for related entities.
    """
    if entity_type not in _SCHEMAS:
        raise ValueError(f"Unknown entity_type '{entity_type}'. Must be one of {_ENTITY_TYPES}")

    context_str = ""
    if universe_id:
        context_str = build_universe_context(session, universe_id) or "(No existing context.)"

    system = (
        "You are the lore engine for Zen AI, a worldbuilding tool for the Zendrix multiverse. "
        "Generate a batch of related lore entities that fit consistently with existing canon "
        "and feel distinct from each other (avoid repetitive names/descriptions)."
    )

    user_prompt = (
        f"## Existing Context\n{context_str}\n\n"
        f"## Task\nGenerate {count} new {entity_type}s based on this request:\n\"{prompt}\"\n\n"
        f"## Required JSON Schema (per item)\n{_SCHEMAS[entity_type]}\n\n"
        f"Return a JSON array of exactly {count} objects, each matching the schema."
    )

    client = get_client()
    result = client.ask_json(user_prompt, system=system, temperature=0.9)

    if not isinstance(result, list):
        raise ValueError(f"Expected JSON array for batch {entity_type}, got: {type(result)}")

    for item in result:
        item["_entity_type"] = entity_type

    return result


def list_entity_types() -> list[str]:
    return _ENTITY_TYPES
