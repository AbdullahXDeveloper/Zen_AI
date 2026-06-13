"""
app/lore/candidates.py

PHASE 1 of the ingestion pipeline: free, local, regex/pattern-based
candidate extraction. No API calls — this narrows down the text so
Phase 2 (Claude extraction) only runs on text chunks that actually
look like they contain new lore entities.

Detects:
- Capitalized multi-word names (potential character/faction/location names)
- Known entity names (cross-referenced against DB, to find re-mentions
  of existing entities — useful for relationship/event extraction)
- Date-like strings (potential event dates)

Output is a "candidate report" per chunk: a dict summarizing what was
found, used to decide whether Phase 2 should run on that chunk and to
give Claude a head start (reduces hallucination, focuses attention).
"""
import re
from typing import Optional

from app.database import crud


# ----------------------------------------------------------------------
# Regex patterns
# ----------------------------------------------------------------------
# Capitalized sequences of 1-4 words, e.g. "Raven", "OM_X", "The Hollow Court"
# Excludes sentence-starting words by requiring the match not be immediately
# preceded by sentence-ending punctuation + space... but that's unreliable,
# so instead we just collect candidates and let Phase 2 + dedup filter noise.
_NAME_PATTERN = re.compile(
    r"\b(?:[A-Z][a-zA-Z'_]*\s?){1,4}\b"
)

# Common English words that capitalize at sentence-start; filter these out
# as standalone single-word "candidates" (multi-word capitalized phrases are
# usually still meaningful even if they start with these).
_STOPWORDS = {
    "The", "A", "An", "He", "She", "It", "They", "We", "I", "You", "This",
    "That", "These", "Those", "His", "Her", "Their", "Its", "Our", "Your",
    "Then", "But", "And", "Or", "So", "When", "While", "After", "Before",
    "If", "As", "Because", "Although", "However", "Meanwhile", "Suddenly",
    "Chapter", "Part", "Section",
}

# Date-like patterns: "Year 4521", "Era of Ashes, Day 12", "12th Cycle", etc.
# Kept loose since Zendrix uses in-universe calendars, not real dates.
_DATE_PATTERN = re.compile(
    r"\b(?:Year|Era|Age|Cycle|Day|Epoch)\s+(?:of\s+)?[A-Za-z0-9' ]{1,30}|"
    r"\b\d{1,5}\s*(?:BC|AC|CE|BCE|ACE)\b",
    re.IGNORECASE,
)


# ----------------------------------------------------------------------
# Core extraction
# ----------------------------------------------------------------------
def extract_name_candidates(text: str, min_length: int = 2) -> list[str]:
    """
    Extract capitalized name-like phrases from text.
    Returns a deduplicated, sorted-by-frequency list of candidate names.
    """
    matches = _NAME_PATTERN.findall(text)
    counts: dict[str, int] = {}

    for m in matches:
        name = m.strip()
        if len(name) < min_length:
            continue
        # Skip if it's just a single stopword
        words = name.split()
        if len(words) == 1 and name in _STOPWORDS:
            continue
        # Skip if it's all-uppercase short acronym-like single letters (noise)
        if len(name) <= 1:
            continue
        counts[name] = counts.get(name, 0) + 1

    # Sort by frequency desc, then alphabetically
    return sorted(counts.keys(), key=lambda n: (-counts[n], n))


def extract_date_candidates(text: str) -> list[str]:
    """Extract date-like strings from text (in-universe calendar formats)."""
    matches = _DATE_PATTERN.findall(text)
    return sorted(set(m.strip() for m in matches if m.strip()))


def match_known_entities(session, name_candidates: list[str]) -> dict[str, dict]:
    """
    Cross-reference name candidates against the DB to find which ones
    correspond to existing entities (any type). Useful for:
    - Avoiding duplicate-entity generation in Phase 2
    - Identifying relationship/event mentions involving known entities

    Returns: {name: {"entity_type": str, "id": int, "uuid": str}}
    """
    known = {}

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

    candidate_set = set(name_candidates)

    for entity_type, list_fn in lookups:
        try:
            entities = list_fn(session)
        except TypeError:
            # Some list_X functions may require filters; call with no args first,
            # fall back to empty list if it errors
            entities = []
        for ent in entities:
            name = getattr(ent, "name", None)
            if name and name in candidate_set:
                known[name] = {
                    "entity_type": entity_type,
                    "id": ent.id,
                    "uuid": getattr(ent, "uuid", ""),
                }

    return known


# ----------------------------------------------------------------------
# Candidate report (per chunk)
# ----------------------------------------------------------------------
def build_candidate_report(session, chunk_text: str) -> dict:
    """
    Build a Phase 1 report for a text chunk:
    {
      "name_candidates": [...],       # new/unrecognized capitalized names
      "known_entities": {...},        # name -> existing DB entity info
      "date_candidates": [...],
      "worth_processing": bool        # heuristic: should Phase 2 run on this chunk?
    }

    "worth_processing" is True if there's at least one name candidate
    NOT already in the DB (i.e. potential new entity) OR a date
    candidate (potential new event).
    """
    names = extract_name_candidates(chunk_text)
    dates = extract_date_candidates(chunk_text)
    known = match_known_entities(session, names)

    new_names = [n for n in names if n not in known]

    worth_processing = bool(new_names) or bool(dates) or bool(known)

    return {
        "name_candidates": new_names,
        "known_entities": known,
        "date_candidates": dates,
        "worth_processing": worth_processing,
    }
