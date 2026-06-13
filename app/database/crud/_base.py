"""
ZenAI — CRUD Base Helpers
Shared utilities used by all entity CRUD modules.
"""

import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.database.models import VersionHistory


def _to_dict(obj) -> dict:
    """Convert a SQLAlchemy model instance to a plain dict (for snapshots)."""
    result = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if isinstance(val, datetime):
            val = val.isoformat()
        result[col.name] = val
    return result


def save_version(session: Session, entity_type: str, entity_id: int, obj, approved_by: str = "user"):
    """
    Write a snapshot of the current entity state to version_history.
    Call this BEFORE committing any update or after a create.
    """
    # Get the latest version number for this entity
    from sqlalchemy import func
    latest = (
        session.query(func.max(VersionHistory.version_number))
        .filter(
            VersionHistory.entity_type == entity_type,
            VersionHistory.entity_id == entity_id,
        )
        .scalar()
    )
    next_version = (latest or 0) + 1

    snapshot = _to_dict(obj)

    vh = VersionHistory(
        entity_type=entity_type,
        entity_id=entity_id,
        version_number=next_version,
        data_snapshot_json=snapshot,
        approved_by=approved_by,
    )
    session.add(vh)


def get_version_history(session: Session, entity_type: str, entity_id: int) -> list[dict]:
    """Return all version snapshots for an entity, newest first."""
    rows = (
        session.query(VersionHistory)
        .filter(
            VersionHistory.entity_type == entity_type,
            VersionHistory.entity_id == entity_id,
        )
        .order_by(VersionHistory.version_number.desc())
        .all()
    )
    return [_to_dict(r) for r in rows]


def rollback_to_version(session: Session, entity_type: str, entity_id: int, version_number: int) -> dict | None:
    """
    Return the snapshot dict for a specific version.
    Caller is responsible for applying the snapshot back to the entity.
    """
    row = (
        session.query(VersionHistory)
        .filter(
            VersionHistory.entity_type == entity_type,
            VersionHistory.entity_id == entity_id,
            VersionHistory.version_number == version_number,
        )
        .first()
    )
    if not row:
        return None
    return row.data_snapshot_json
