"""
app/ai/consistency_checker.py

Detects contradictions and continuity issues in the lore database.
Two layers:
1. Local heuristic checks (no API call) — structural/missing-field issues
2. Claude-based checks — semantic contradictions (e.g. "Character X is
   described as dead in Event A but alive in Event B")

Returns a list of "issue" dicts:
{
  "severity": "low | medium | high",
  "entity_type": "...",
  "entity_id": int,
  "entity_name": "...",
  "issue": "description of the problem",
  "suggestion": "optional fix suggestion"
}
"""
from typing import Optional

from app.ai.claude_client import get_client
from app.database import crud


# ----------------------------------------------------------------------
# Layer 1: Local heuristic / "missing lore" checks (no API call)
# ----------------------------------------------------------------------
def check_missing_fields(session, entity_type: Optional[str] = None) -> list[dict]:
    """
    Cheap structural checks across entity types:
    - Faction with no founder / no members
    - Character with empty description or no traits
    - Event with no participants
    - Universe with no characters at all
    """
    issues = []

    types_to_check = [entity_type] if entity_type else [
        "character", "faction", "location", "event", "universe"
    ]

    if "character" in types_to_check:
        for char in crud.list_characters(session):
            desc = getattr(char, "description", "") or ""
            if len(desc.strip()) < 20:
                issues.append({
                    "severity": "medium",
                    "entity_type": "character",
                    "entity_id": char.id,
                    "entity_name": getattr(char, "name", "?"),
                    "issue": "Character has little or no description.",
                    "suggestion": "Use lore_generator or trait_analyzer to flesh out this character.",
                })
            traits = getattr(char, "traits_json", None)
            if not traits:
                issues.append({
                    "severity": "low",
                    "entity_type": "character",
                    "entity_id": char.id,
                    "entity_name": getattr(char, "name", "?"),
                    "issue": "Character has no traits_json (personality/goals/appearance).",
                    "suggestion": "Run trait_analyzer on this character's description.",
                })

    if "faction" in types_to_check:
        for fac in crud.list_factions(session):
            founder_id = getattr(fac, "founder_character_id", None)
            if founder_id is None:
                issues.append({
                    "severity": "medium",
                    "entity_type": "faction",
                    "entity_id": fac.id,
                    "entity_name": getattr(fac, "name", "?"),
                    "issue": "Faction has no founder assigned.",
                    "suggestion": "Assign a founder or generate one with lore_generator.",
                })

    if "event" in types_to_check:
        for evt in crud.list_events(session):
            participants = []
            if hasattr(crud, "list_event_participants"):
                participants = crud.list_event_participants(session, evt.id)
            if not participants:
                issues.append({
                    "severity": "low",
                    "entity_type": "event",
                    "entity_id": evt.id,
                    "entity_name": getattr(evt, "name", "?"),
                    "issue": "Event has no participants linked.",
                    "suggestion": "Link relevant characters/factions via add_event_participant.",
                })

    if "universe" in types_to_check:
        for uni in crud.list_universes(session):
            chars = crud.list_characters(session, universe_id=uni.id)
            if not chars:
                issues.append({
                    "severity": "high",
                    "entity_type": "universe",
                    "entity_id": uni.id,
                    "entity_name": getattr(uni, "name", "?"),
                    "issue": "Universe has zero characters.",
                    "suggestion": "Generate initial characters with lore_generator.generate_batch.",
                })

    return issues


# ----------------------------------------------------------------------
# Layer 2: Claude-based semantic contradiction check
# ----------------------------------------------------------------------
def check_character_consistency(session, character_id: int) -> list[dict]:
    """
    Asks Claude to review a character's description plus their event
    history and relationships for internal contradictions
    (e.g. timeline issues, contradictory traits, death/alive conflicts).
    """
    char = crud.get_character(session, character_id)
    if not char:
        return []

    desc = getattr(char, "description", "") or ""
    name = getattr(char, "name", "?")

    events = []
    if hasattr(crud, "list_entity_events"):
        events = crud.list_entity_events(session, character_id, entity_type="character")

    event_lines = []
    for evt in events:
        e_name = getattr(evt, "name", "?")
        e_type = getattr(evt, "event_type", "?")
        e_date = getattr(evt, "date_value", "?")
        e_desc = (getattr(evt, "description", "") or "")[:200]
        event_lines.append(f"- [{e_type}] {e_name} ({e_date}): {e_desc}")

    events_str = "\n".join(event_lines) if event_lines else "(No events linked)"

    system = (
        "You are a continuity editor for a worldbuilding database. "
        "Review the provided character description and their event history "
        "for internal contradictions: timeline issues, contradictory traits, "
        "death/alive conflicts, location conflicts, etc. "
        "Be conservative — only flag genuine contradictions, not stylistic choices."
    )

    user_prompt = (
        f"## Character: {name}\n\n"
        f"### Description\n{desc}\n\n"
        f"### Linked Events\n{events_str}\n\n"
        "Return a JSON array of issue objects, each with fields: "
        '"severity" (low|medium|high), "issue" (description), "suggestion" (fix). '
        "If no issues found, return an empty array []."
    )

    client = get_client()
    result = client.ask_json(user_prompt, system=system, temperature=0.3)

    if not isinstance(result, list):
        return []

    for item in result:
        item["entity_type"] = "character"
        item["entity_id"] = character_id
        item["entity_name"] = name

    return result


def check_universe_consistency(session, universe_id: int) -> list[dict]:
    """
    Asks Claude to review a universe's overall lore (description + top
    entities) for thematic/logical contradictions.
    """
    from app.ai.context_builder import build_universe_context

    universe = crud.get_universe(session, universe_id)
    if not universe:
        return []

    context = build_universe_context(session, universe_id)
    name = getattr(universe, "name", "?")

    system = (
        "You are a continuity editor for a worldbuilding database. "
        "Review the provided universe overview for contradictions between "
        "entities — e.g. a faction whose ideology conflicts with its founder's "
        "described values, or characters who couldn't logically coexist. "
        "Be conservative — only flag genuine contradictions."
    )

    user_prompt = (
        f"## Universe: {name}\n\n{context}\n\n"
        "Return a JSON array of issue objects, each with fields: "
        '"severity" (low|medium|high), "entity_name", "issue", "suggestion". '
        "If no issues found, return an empty array []."
    )

    client = get_client()
    result = client.ask_json(user_prompt, system=system, temperature=0.3)

    if not isinstance(result, list):
        return []

    for item in result:
        item["entity_type"] = "universe"
        item["entity_id"] = universe_id

    return result


# ----------------------------------------------------------------------
# Combined entry point
# ----------------------------------------------------------------------
def run_full_check(session, universe_id: Optional[int] = None,
                    include_ai_checks: bool = True) -> list[dict]:
    """
    Run heuristic checks (always) plus optional AI-based checks for a
    given universe. Returns combined, sorted-by-severity issue list.
    """
    issues = check_missing_fields(session)

    if include_ai_checks and universe_id:
        issues.extend(check_universe_consistency(session, universe_id))
        for char in crud.list_characters(session, universe_id=universe_id):
            issues.extend(check_character_consistency(session, char.id))

    severity_order = {"high": 0, "medium": 1, "low": 2}
    issues.sort(key=lambda i: severity_order.get(i.get("severity", "low"), 3))
    return issues
