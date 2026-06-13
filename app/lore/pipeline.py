"""
app/lore/pipeline.py

Orchestrates the full 3-phase document ingestion pipeline:

1. Read file (readers.py) -> chunk text
2. Phase 1: candidate extraction per chunk (candidates.py) -> filter chunks
3. Phase 2: Claude extraction on worth-processing chunks (extractor.py)
4. Merge results across chunks (extractor.merge_extraction_results)
5. Mark lore_document as processed (crud.mark_lore_document_processed)
6. Return merged result for Phase 3 human review (review.py, called
   separately by the UI after the user reviews)

This module does NOT perform Phase 3 persistence — that's triggered by
the UI calling review.approve_all() after the user reviews the result
returned here.
"""
from pathlib import Path
from typing import Optional

from app.database import crud
from app.lore.readers import read_file, chunk_text
from app.lore.candidates import build_candidate_report
from app.lore.extractor import extract_from_chunk, merge_extraction_results


def ingest_document(session, file_path: str | Path, universe_id: Optional[int] = None,
                     max_chars_per_chunk: int = 6000,
                     create_lore_document: bool = True) -> dict:
    """
    Run the full ingestion pipeline (Phases 1-2) on a single document.

    Returns:
    {
      "lore_document_id": int | None,
      "file_path": str,
      "chunks_total": int,
      "chunks_processed": int,
      "chunks_skipped": int,
      "merged_result": dict,   # see extractor.merge_extraction_results
    }
    """
    file_path = Path(file_path)
    text = read_file(file_path)
    chunks = chunk_text(text, max_chars=max_chars_per_chunk)

    lore_document_id = None
    if create_lore_document and hasattr(crud, "create_lore_document"):
        doc = crud.create_lore_document(
            session,
            filename=file_path.name,
            universe_id=universe_id,
            status="processing",
        )
        lore_document_id = doc.id

    extraction_results = []
    chunks_processed = 0
    chunks_skipped = 0

    for chunk in chunks:
        report = build_candidate_report(session, chunk)

        if not report["worth_processing"]:
            chunks_skipped += 1
            continue

        result = extract_from_chunk(
            session, chunk,
            source_document_id=lore_document_id,
            candidate_report=report,
        )
        extraction_results.append(result)
        chunks_processed += 1

    merged = merge_extraction_results(extraction_results) if extraction_results else {
        "characters": [], "factions": [], "locations": [],
        "events": [], "artifacts": [], "relationships": [],
    }

    if lore_document_id and hasattr(crud, "mark_lore_document_processed"):
        crud.mark_lore_document_processed(session, lore_document_id)

    return {
        "lore_document_id": lore_document_id,
        "file_path": str(file_path),
        "chunks_total": len(chunks),
        "chunks_processed": chunks_processed,
        "chunks_skipped": chunks_skipped,
        "merged_result": merged,
    }


def ingest_text(session, text: str, source_name: str = "pasted_text",
                 universe_id: Optional[int] = None,
                 max_chars_per_chunk: int = 6000) -> dict:
    """
    Same as ingest_document but for raw text (e.g. pasted into the UI
    rather than uploaded as a file). Does not create a lore_document
    record by default.
    """
    chunks = chunk_text(text, max_chars=max_chars_per_chunk)

    extraction_results = []
    chunks_processed = 0
    chunks_skipped = 0

    for chunk in chunks:
        report = build_candidate_report(session, chunk)

        if not report["worth_processing"]:
            chunks_skipped += 1
            continue

        result = extract_from_chunk(session, chunk, source_document_id=None,
                                      candidate_report=report)
        extraction_results.append(result)
        chunks_processed += 1

    merged = merge_extraction_results(extraction_results) if extraction_results else {
        "characters": [], "factions": [], "locations": [],
        "events": [], "artifacts": [], "relationships": [],
    }

    return {
        "lore_document_id": None,
        "file_path": source_name,
        "chunks_total": len(chunks),
        "chunks_processed": chunks_processed,
        "chunks_skipped": chunks_skipped,
        "merged_result": merged,
    }


def summarize_result(result: dict) -> str:
    """Human-readable one-line summary of an ingestion result, for UI/logs."""
    m = result["merged_result"]
    return (
        f"{result['file_path']}: "
        f"{result['chunks_processed']}/{result['chunks_total']} chunks processed "
        f"({result['chunks_skipped']} skipped, no candidates) — "
        f"found {len(m['characters'])} characters, {len(m['factions'])} factions, "
        f"{len(m['locations'])} locations, {len(m['events'])} events, "
        f"{len(m['artifacts'])} artifacts, {len(m['relationships'])} relationships"
    )
