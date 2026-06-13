"""
ZenAI — CSV I/O
Export any table to CSV, and bulk-import CSV data into any table.

Usage:
    from app.database.csv_io import export_csv, import_csv

    session = get_session()
    export_csv(session, "characters", "/path/to/export/characters.csv")
    import_csv(session, "characters", "/path/to/import/characters.csv")
"""

import csv
import os
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import inspect

from app.database.models import (
    Universe, UniverseConnection,
    RootEntity, RootEntityLink,
    Character, CharacterPower,
    Faction, Location, Power,
    Event, EventParticipant,
    RelationshipEdge, Artifact,
    Story, SimulationRun,
    LoreDocument, Tag, EntityTag,
    EntityNote,
)

# ─────────────────────────────────────────────
# TABLE REGISTRY
# Maps table name string → SQLAlchemy model class
# ─────────────────────────────────────────────

TABLE_MAP: dict[str, type] = {
    "universes": Universe,
    "universes_connections": UniverseConnection,
    "root_entities": RootEntity,
    "root_entity_links": RootEntityLink,
    "characters": Character,
    "character_powers": CharacterPower,
    "factions": Faction,
    "locations": Location,
    "powers": Power,
    "events": Event,
    "event_participants": EventParticipant,
    "relationships": RelationshipEdge,
    "artifacts": Artifact,
    "stories": Story,
    "simulation_runs": SimulationRun,
    "lore_documents": LoreDocument,
    "tags": Tag,
    "entity_tags": EntityTag,
    "entity_notes": EntityNote,
}

# Columns that should NOT be overwritten during import (auto-managed)
SKIP_ON_IMPORT = {"id", "uuid"}

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _get_columns(model_class) -> list[str]:
    """Return column names for a SQLAlchemy model."""
    mapper = inspect(model_class)
    return [col.key for col in mapper.columns]


def _cast_value(value: str, col_type: str):
    """
    Cast a CSV string value to the appropriate Python type
    based on a rough type name check.
    """
    if value == "" or value is None:
        return None
    col_type_lower = col_type.lower()

    if "integer" in col_type_lower or "int" in col_type_lower:
        return int(value)
    if "boolean" in col_type_lower or "bool" in col_type_lower:
        return value.lower() in ("true", "1", "yes")
    if "json" in col_type_lower:
        import json
        try:
            return json.loads(value)
        except Exception:
            return value
    if "datetime" in col_type_lower:
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return value
    # Default: string
    return value


def _validate_row(row: dict, model_class, row_num: int) -> list[str]:
    """
    Basic validation: check required columns are present and non-empty.
    Returns list of warning strings (empty = passed).
    """
    warnings = []
    mapper = inspect(model_class)

    for col in mapper.columns:
        if col.key in SKIP_ON_IMPORT:
            continue
        if not col.nullable and col.default is None and col.server_default is None:
            val = row.get(col.key, "")
            if val == "" or val is None:
                warnings.append(f"Row {row_num}: required column '{col.key}' is empty.")

    return warnings


# ─────────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────────

def export_csv(
    session: Session,
    table_name: str,
    output_path: str,
) -> int:
    """
    Export all rows from a table to a CSV file.

    Args:
        session:     SQLAlchemy session
        table_name:  One of the keys in TABLE_MAP (e.g. "characters")
        output_path: Full file path to write the CSV

    Returns:
        Number of rows exported.

    Raises:
        ValueError: if table_name is not in TABLE_MAP
    """
    if table_name not in TABLE_MAP:
        raise ValueError(
            f"Unknown table '{table_name}'. "
            f"Valid tables: {sorted(TABLE_MAP.keys())}"
        )

    model_class = TABLE_MAP[table_name]
    columns = _get_columns(model_class)
    rows = session.query(model_class).all()

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()

        count = 0
        for row in rows:
            row_dict = {}
            for col in columns:
                val = getattr(row, col)
                # Serialize datetime and complex types
                if isinstance(val, datetime):
                    val = val.isoformat()
                elif isinstance(val, (dict, list)):
                    import json
                    val = json.dumps(val)
                row_dict[col] = val if val is not None else ""
            writer.writerow(row_dict)
            count += 1

    print(f"[ZenAI CSV] Exported {count} rows from '{table_name}' → {output_path}")
    return count


# ─────────────────────────────────────────────
# IMPORT
# ─────────────────────────────────────────────

def import_csv(
    session: Session,
    table_name: str,
    file_path: str,
    skip_errors: bool = True,
) -> dict:
    """
    Bulk import rows from a CSV into a table.

    - Skips 'id' and 'uuid' columns (auto-generated by DB).
    - Validates required fields before insert.
    - On error: if skip_errors=True, logs and continues; else raises.

    Args:
        session:      SQLAlchemy session
        table_name:   One of the keys in TABLE_MAP
        file_path:    Path to the CSV file to import
        skip_errors:  If True, bad rows are skipped and reported; if False, raises on first error.

    Returns:
        dict with keys: imported (int), skipped (int), warnings (list of str)

    Raises:
        ValueError: if table_name is invalid or file not found
    """
    if table_name not in TABLE_MAP:
        raise ValueError(
            f"Unknown table '{table_name}'. "
            f"Valid tables: {sorted(TABLE_MAP.keys())}"
        )
    if not os.path.isfile(file_path):
        raise ValueError(f"File not found: {file_path}")

    model_class = TABLE_MAP[table_name]
    mapper = inspect(model_class)
    col_type_map = {col.key: str(col.type) for col in mapper.columns}

    imported = 0
    skipped = 0
    all_warnings = []

    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row_num, raw_row in enumerate(reader, start=2):  # row 1 = header

            # Validate
            warnings = _validate_row(raw_row, model_class, row_num)
            if warnings:
                all_warnings.extend(warnings)
                if not skip_errors:
                    raise ValueError("\n".join(warnings))
                skipped += 1
                continue

            # Build kwargs, skip id/uuid
            kwargs = {}
            for key, raw_val in raw_row.items():
                if key in SKIP_ON_IMPORT:
                    continue
                if key not in col_type_map:
                    continue  # ignore extra CSV columns
                kwargs[key] = _cast_value(raw_val, col_type_map[key])

            try:
                obj = model_class(**kwargs)
                session.add(obj)
                session.flush()
                imported += 1
            except Exception as e:
                session.rollback()
                msg = f"Row {row_num}: Insert failed — {e}"
                all_warnings.append(msg)
                if not skip_errors:
                    raise RuntimeError(msg) from e
                skipped += 1
                continue

    try:
        session.commit()
    except Exception as e:
        session.rollback()
        raise RuntimeError(f"[ZenAI CSV] Commit failed during import: {e}") from e

    print(
        f"[ZenAI CSV] Import '{table_name}' complete — "
        f"imported: {imported}, skipped: {skipped}"
    )
    if all_warnings:
        print(f"[ZenAI CSV] Warnings ({len(all_warnings)}):")
        for w in all_warnings:
            print(f"  ⚠ {w}")

    return {"imported": imported, "skipped": skipped, "warnings": all_warnings}


# ─────────────────────────────────────────────
# CONVENIENCE: export all tables at once
# ─────────────────────────────────────────────

def export_all_tables(session: Session, output_dir: str) -> dict[str, int]:
    """
    Export every table to CSV files in output_dir.
    Files are named: {table_name}.csv

    Returns dict of {table_name: row_count}.
    """
    os.makedirs(output_dir, exist_ok=True)
    results = {}
    for table_name in TABLE_MAP:
        path = os.path.join(output_dir, f"{table_name}.csv")
        try:
            count = export_csv(session, table_name, path)
            results[table_name] = count
        except Exception as e:
            print(f"[ZenAI CSV] Failed to export '{table_name}': {e}")
            results[table_name] = -1
    return results
