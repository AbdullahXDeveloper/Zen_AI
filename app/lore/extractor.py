"""
app/lore/extractor.py

PHASE 2 of the ingestion pipeline: Claude-based structured extraction.
Only runs on chunks flagged by Phase 1 (candidates.py) as
"worth_processing", to keep API usage focused and reduce hallucination.

For each chunk, asks Claude to extract candidate entities (characters,
factions, locations, events, artifacts) AND relationships/event
participations involving entities already known in the DB.

Output objects mirror the lore_generator.py schemas so they can flow
into the same Approve/Reject/Edit UI, but are tagged with source info
(source_document_id, source_excerpt) for traceability.

KEY RULE: This module NEVER writes to the database. Phase 3 (review.py)
handles persistence after human approval.
"""
from typing import Optional

from app.ai.claude_client import get_client
from app.lore.candidates import build_candidate_report


_EXTRACTION_SCHEMA = """{
  "characters": [
    {
      "name": "string",
      "description": "string (summarized from source text)",
      "importance_score": "integer 1-100 (estimate based on prominence in text)",
      "is_new": "boolean (true if this entity does not already exist in the DB)"
    }
  ],
  "factions": [ { "name": "string", "description": "string", "importance_score": "integer 1-100", "is_new": "boolean" } ],
  "locations": [ { "name": "string", "description": "string", "importance_score": "integer 1-100", "is_new": "boolean" } ],
  "events": [
    {
      "name": "string",
      "description": "string",
      "event_type": "birth | death | rebirth | war | other",
      "date_value": "string or null",
      "importance_score": "integer 1-100",
      "is_new": "boolean",
      "participants": ["string (character/faction names involved)"]
    }
  ],
  "artifacts": [ { "name": "string", "description": "string", "importance_score": "integer 1-100", "is_new": "boolean" } ],
  "relationships": [
    {
      "entity_a": "string (name)",
      "entity_b": "string (name)",
      "relationship_type": "friend | enemy | family | mentor | student | created | destroyed | owns | located_in | participated_in",
      "description": "string (brief, optional)"
    }
  ]
}"""


def extract_from_chunk(session, chunk_text: str, source_document_id: Optional[int] = None,
                        candidate_report: Optional[dict] = None) -> dict:
    """
    Run Claude extraction on a single text chunk.

    candidate_report: if not provided, will be computed via
    candidates.build_candidate_report(). Pass it in to avoid recomputing
    when called from pipeline.py which already has it.

    Returns a dict matching _EXTRACTION_SCHEMA, with each item additionally
    tagged with:
      "_source_document_id": int | None
      "_source_excerpt": str (the chunk text, truncated)
    """
    if candidate_report is None:
        candidate_report = build_candidate_report(session, chunk_text)

    known_str = ", ".join(
        f"{name} ({info['entity_type']})"
        for name, info in candidate_report.get("known_entities", {}).items()
    ) or "(none)"

    new_candidates_str = ", ".join(candidate_report.get("name_candidates", [])) or "(none)"
    date_candidates_str = ", ".join(candidate_report.get("date_candidates", [])) or "(none)"

    system = (
        "You are the lore extraction engine for Zen AI, a worldbuilding database for the "
        "Zendrix multiverse. Read the provided text excerpt and extract structured lore "
        "entities and relationships. "
        "Mark an entity as is_new=true only if it does NOT appear in the 'Already Known "
        "Entities' list below. If an entity in the text matches a known entity name, use "
        "is_new=false and use the EXACT existing name. "
        "Do not invent entities not supported by the text. If a category has no relevant "
        "items, return an empty array for it."
    )

    user_prompt = (
        f"## Already Known Entities (exist in DB)\n{known_str}\n\n"
        f"## Phase 1 Candidate Names (unrecognized, possibly new)\n{new_candidates_str}\n\n"
        f"## Phase 1 Candidate Dates\n{date_candidates_str}\n\n"
        f"## Text Excerpt\n{chunk_text}\n\n"
        f"## Required JSON Schema\n{_EXTRACTION_SCHEMA}\n\n"
        "Return a single JSON object matching this schema exactly."
    )

    client = get_client()
    result = client.ask_json(user_prompt, system=system, temperature=0.3, max_tokens=4096)

    if not isinstance(result, dict):
        raise ValueError(f"Expected JSON object from extraction, got: {type(result)}")

    # Ensure all expected keys exist
    for key in ("characters", "factions", "locations", "events", "artifacts", "relationships"):
        result.setdefault(key, [])

    # Tag items with source info
    excerpt = chunk_text[:500]
    for key in ("characters", "factions", "locations", "events", "artifacts"):
        for item in result[key]:
            item["_source_document_id"] = source_document_id
            item["_source_excerpt"] = excerpt
            item["_entity_type"] = key[:-1] if key != "artifacts" else "artifact"  # singularize

    for rel in result["relationships"]:
        rel["_source_document_id"] = source_document_id
        rel["_source_excerpt"] = excerpt

    return result


def merge_extraction_results(results: list[dict]) -> dict:
    """
    Merge multiple per-chunk extraction results into one combined result,
    deduplicating entities by (entity_type, name) — keeping the first
    occurrence but merging descriptions if a later chunk has more detail.
    """
    merged = {
        "characters": [], "factions": [], "locations": [],
        "events": [], "artifacts": [], "relationships": [],
    }
    seen: dict[tuple, int] = {}  # (entity_type, name) -> index in merged[list]

    for result in results:
        for key in ("characters", "factions", "locations", "events", "artifacts"):
            for item in result.get(key, []):
                dedup_key = (key, item.get("name", "").strip().lower())
                if dedup_key in seen:
                    idx = seen[dedup_key]
                    existing = merged[key][idx]
                    # Merge: keep longer description, max importance, OR is_new
                    if len(item.get("description", "")) > len(existing.get("description", "")):
                        existing["description"] = item["description"]
                    existing["importance_score"] = max(
                        existing.get("importance_score", 0), item.get("importance_score", 0)
                    )
                    existing["is_new"] = existing.get("is_new", True) and item.get("is_new", True)
                    if key == "events":
                        existing.setdefault("participants", [])
                        for p in item.get("participants", []):
                            if p not in existing["participants"]:
                                existing["participants"].append(p)
                else:
                    seen[dedup_key] = len(merged[key])
                    merged[key].append(item)

        # Relationships: dedupe by (entity_a, entity_b, relationship_type)
        for rel in result.get("relationships", []):
            rel_key = (
                rel.get("entity_a", "").strip().lower(),
                rel.get("entity_b", "").strip().lower(),
                rel.get("relationship_type", ""),
            )
            existing_keys = {
                (r.get("entity_a", "").strip().lower(), r.get("entity_b", "").strip().lower(),
                 r.get("relationship_type", ""))
                for r in merged["relationships"]
            }
            if rel_key not in existing_keys:
                merged["relationships"].append(rel)

    return merged
