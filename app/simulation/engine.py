"""
app/simulation/engine.py
Zen AI — Module 12: World Simulation Engine

Given a premise and a list of affected entities, uses Ollama (via claude_client)
to simulate what would happen in the Zendrix multiverse and returns structured outcomes.

Returns:
{
  "title":     str,
  "reasoning": str,          # AI's step-by-step reasoning
  "outcomes":  [             # list of entity-level outcomes
    {
      "entity_type": "character|faction|location|event|artifact|universe",
      "entity_id":   int,
      "entity_name": str,
      "impact":      "major|moderate|minor|none",
      "outcome_text": str,   # what happens to this entity
    }, ...
  ],
  "global_outcome": str,     # overall world-level summary
  "new_events":   [str],     # list of new events that would emerge
  "timeline_shift": str,     # how the timeline changes (or "No shift")
}
"""
from __future__ import annotations
from typing import Optional

from app.ai.claude_client import get_client
from app.ai.context_builder import build_universe_context, build_character_context
from app.database import crud
from app.database.models import (
    Character, Faction, Location, Artifact, Event, Universe
)


_IMPACT_LEVELS = ("major", "moderate", "minor", "none")

_ENTITY_MODEL_MAP = {
    "character": Character,
    "faction":   Faction,
    "location":  Location,
    "artifact":  Artifact,
    "event":     Event,
    "universe":  Universe,
}


def _resolve_entity_name(session, entity_type: str, entity_id: int) -> str:
    """Get display name of any entity."""
    model = _ENTITY_MODEL_MAP.get(entity_type)
    if not model:
        return f"{entity_type}#{entity_id}"
    obj = session.query(model).filter(model.id == entity_id).first()
    if not obj:
        return f"{entity_type}#{entity_id}"
    return getattr(obj, "name", None) or getattr(obj, "title", f"{entity_type}#{entity_id}")


def run_simulation(
    session,
    premise: str,
    affected_entities: list[dict],       # [{entity_type, entity_id}, ...]
    universe_id: Optional[int] = None,
    simulation_depth: str = "standard",  # "quick" | "standard" | "deep"
) -> dict:
    """
    Run a world simulation.

    premise: what-if scenario or event description
    affected_entities: list of {entity_type, entity_id} dicts
    universe_id: grounds the simulation in universe lore
    simulation_depth: controls AI detail level

    Returns the structured result dict (see module docstring).
    """
    depth_tokens = {"quick": 1024, "standard": 2048, "deep": 4096}
    max_tok = depth_tokens.get(simulation_depth, 2048)

    # ── Build context ─────────────────────────────────────
    context_parts: list[str] = []

    if universe_id:
        ctx = build_universe_context(session, universe_id)
        if ctx:
            context_parts.append(f"## Universe Context\n{ctx}")

    entity_names: list[dict] = []
    for ae in affected_entities:
        etype = ae.get("entity_type", "unknown")
        eid   = ae.get("entity_id", 0)
        name  = _resolve_entity_name(session, etype, eid)
        entity_names.append({"entity_type": etype, "entity_id": eid, "entity_name": name})

        if etype == "character":
            ctx = build_character_context(session, eid)
            if ctx:
                context_parts.append(f"## Character: {name}\n{ctx}")

    entity_list_str = "\n".join(
        f"  - {e['entity_type'].title()}: {e['entity_name']} (id={e['entity_id']})"
        for e in entity_names
    ) or "  (No specific entities selected — simulate universe-wide)"

    context_str = "\n\n".join(context_parts) if context_parts else "(No additional lore context.)"

    # ── Build prompt ──────────────────────────────────────
    system = (
        "You are the World Simulation Engine for Zen AI, a worldbuilding tool "
        "for the Zendrix multiverse. Given a what-if premise, simulate the "
        "realistic consequences across the affected entities and the world at large. "
        "Be specific, grounded in lore, and think through cause-and-effect carefully. "
        "Your output must be a single valid JSON object."
    )

    user_prompt = f"""## Lore Context
{context_str}

## Simulation Premise
{premise}

## Affected Entities
{entity_list_str}

## Task
Simulate what would happen if the above premise occurred. For each affected entity,
describe the specific outcome. Then give an overall world-level summary.

Return a JSON object with EXACTLY these fields:
{{
  "title": "A short title for this simulation run (≤10 words)",
  "reasoning": "Step-by-step logical reasoning (2-4 paragraphs)",
  "outcomes": [
    {{
      "entity_type": "<character|faction|location|event|artifact|universe>",
      "entity_id": <int>,
      "entity_name": "<name>",
      "impact": "<major|moderate|minor|none>",
      "outcome_text": "<1-3 sentences describing what happens to this entity>"
    }}
    ... (one entry per affected entity)
  ],
  "global_outcome": "Overall world-level summary paragraph",
  "new_events": ["<event that would emerge>", ...],
  "timeline_shift": "Description of how the timeline changes, or 'No significant shift'"
}}

Depth: {simulation_depth}. {'Keep it concise.' if simulation_depth == 'quick' else 'Be thorough and detailed.'}
"""

    client = get_client()
    result = client.ask_json(user_prompt, system=system, temperature=0.85,
                             max_tokens=max_tok)

    if not isinstance(result, dict):
        raise ValueError(f"Expected JSON dict from AI, got {type(result)}")

    # Merge entity_names into outcomes (ensure entity_id is present)
    outcomes = result.get("outcomes", [])
    # If AI didn't return outcomes per entity, generate stubs
    if not outcomes and entity_names:
        outcomes = [
            {
                "entity_type": e["entity_type"],
                "entity_id":   e["entity_id"],
                "entity_name": e["entity_name"],
                "impact":      "moderate",
                "outcome_text": "(AI did not specify — see global outcome)"
            }
            for e in entity_names
        ]

    return {
        "title":          result.get("title", "Simulation Run"),
        "reasoning":      result.get("reasoning", ""),
        "outcomes":       outcomes,
        "global_outcome": result.get("global_outcome", ""),
        "new_events":     result.get("new_events", []),
        "timeline_shift": result.get("timeline_shift", "No significant shift"),
    }
