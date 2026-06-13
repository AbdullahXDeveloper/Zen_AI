"""
app/ai/trait_analyzer.py

Infers structured traits_json from a character's free-text description
(and optionally their event/relationship history). Used to backfill
traits for characters created before this field existed, or to enrich
characters generated externally (e.g. from document ingestion).

traits_json shape (matches lore_generator schema):
{
  "personality": ["trait1", "trait2", ...],
  "appearance": "string",
  "goals": ["goal1", "goal2", ...]
}

KEY RULE: Like lore_generator, this module does NOT write to the DB.
It returns the proposed traits_json for Approve/Reject/Edit, then the
caller uses update_character(session, id, traits_json=...) on approval.
"""
from typing import Optional

from app.ai.claude_client import get_client
from app.database import crud


_TRAITS_SCHEMA = """{
  "personality": ["string", "..."],
  "appearance": "string (1-2 sentences)",
  "goals": ["string", "..."]
}"""


def analyze_character_traits(session, character_id: int,
                              extra_text: Optional[str] = None) -> dict:
    """
    Analyze a character's description (plus optional extra_text, e.g.
    excerpts from ingested documents) and return proposed traits_json.

    Does not modify the database.
    """
    char = crud.get_character(session, character_id)
    if not char:
        raise ValueError(f"Character with id {character_id} not found")

    name = getattr(char, "name", "?")
    desc = getattr(char, "description", "") or ""
    existing_traits = getattr(char, "traits_json", None)

    source_text = desc
    if extra_text:
        source_text += f"\n\n{extra_text}"

    if not source_text.strip():
        raise ValueError(f"Character '{name}' has no description text to analyze")

    system = (
        "You are a character analyst for a worldbuilding database. "
        "Given a character's description, infer their personality traits, "
        "physical appearance, and goals/motivations. "
        "Base inferences strictly on what's stated or strongly implied — "
        "do not invent unrelated details."
    )

    existing_str = ""
    if existing_traits:
        existing_str = (
            f"\n\n## Existing traits_json (refine/extend, don't discard valid entries)\n"
            f"{existing_traits}"
        )

    user_prompt = (
        f"## Character: {name}\n\n"
        f"### Description / Source Text\n{source_text}{existing_str}\n\n"
        f"## Required JSON Schema\n{_TRAITS_SCHEMA}\n\n"
        "Return a single JSON object matching this schema exactly."
    )

    client = get_client()
    result = client.ask_json(user_prompt, system=system, temperature=0.5)

    if not isinstance(result, dict):
        raise ValueError(f"Expected JSON object for traits, got: {type(result)}")

    for key in ("personality", "appearance", "goals"):
        if key not in result:
            result[key] = [] if key != "appearance" else ""

    return result


def analyze_text_for_traits(name: str, source_text: str) -> dict:
    """
    Variant that doesn't require an existing DB record — useful during
    document ingestion (Module 2) when a candidate character has been
    extracted but not yet created.
    """
    if not source_text.strip():
        raise ValueError("source_text is empty")

    system = (
        "You are a character analyst for a worldbuilding database. "
        "Given a description of a character extracted from a document, "
        "infer their personality traits, physical appearance, and goals. "
        "Base inferences strictly on the provided text."
    )

    user_prompt = (
        f"## Character Name: {name}\n\n"
        f"### Source Text\n{source_text}\n\n"
        f"## Required JSON Schema\n{_TRAITS_SCHEMA}\n\n"
        "Return a single JSON object matching this schema exactly."
    )

    client = get_client()
    result = client.ask_json(user_prompt, system=system, temperature=0.5)

    if not isinstance(result, dict):
        raise ValueError(f"Expected JSON object for traits, got: {type(result)}")

    for key in ("personality", "appearance", "goals"):
        if key not in result:
            result[key] = [] if key != "appearance" else ""

    return result


def apply_traits(session, character_id: int, traits_json: dict):
    """
    Helper to persist approved traits_json via the CRUD layer.
    Call this only after user approval in the UI.
    """
    return crud.update_character(session, character_id, traits_json=traits_json)
