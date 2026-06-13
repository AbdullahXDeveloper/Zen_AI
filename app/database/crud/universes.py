"""
ZenAI — CRUD: Universes
Handles Universe and UniverseConnection create/read/update/delete.
"""

from datetime import datetime
from sqlalchemy.orm import Session
from app.database.models import Universe, UniverseConnection
from app.database.crud._base import save_version, _to_dict

ENTITY_TYPE = "universe"


# ─────────────────────────────────────────────
# UNIVERSE — CREATE
# ─────────────────────────────────────────────

def create_universe(
    session: Session,
    name: str,
    description: str = None,
    canon_status: str = "canon",
    importance_score: int = 50,
    approved_by: str = "user",
) -> Universe:
    uni = Universe(
        name=name,
        description=description,
        canon_status=canon_status,
        importance_score=importance_score,
    )
    session.add(uni)
    session.flush()  # get the auto id before commit
    save_version(session, ENTITY_TYPE, uni.id, uni, approved_by)
    session.commit()
    session.refresh(uni)
    return uni


# ─────────────────────────────────────────────
# UNIVERSE — READ
# ─────────────────────────────────────────────

def get_universe(session: Session, universe_id: int) -> Universe | None:
    return session.query(Universe).filter(Universe.id == universe_id).first()


def get_universe_by_uuid(session: Session, uuid: str) -> Universe | None:
    return session.query(Universe).filter(Universe.uuid == uuid).first()


def list_universes(
    session: Session,
    canon_status: str = None,
    min_importance: int = None,
    name_contains: str = None,
) -> list[Universe]:
    q = session.query(Universe)
    if canon_status:
        q = q.filter(Universe.canon_status == canon_status)
    if min_importance is not None:
        q = q.filter(Universe.importance_score >= min_importance)
    if name_contains:
        q = q.filter(Universe.name.ilike(f"%{name_contains}%"))
    return q.order_by(Universe.importance_score.desc()).all()


# ─────────────────────────────────────────────
# UNIVERSE — UPDATE
# ─────────────────────────────────────────────

def update_universe(
    session: Session,
    universe_id: int,
    approved_by: str = "user",
    **kwargs,
) -> Universe | None:
    uni = get_universe(session, universe_id)
    if not uni:
        return None

    allowed = {"name", "description", "canon_status", "importance_score"}
    for key, val in kwargs.items():
        if key in allowed:
            setattr(uni, key, val)
    uni.updated_at = datetime.utcnow()

    save_version(session, ENTITY_TYPE, uni.id, uni, approved_by)
    session.commit()
    session.refresh(uni)
    return uni


# ─────────────────────────────────────────────
# UNIVERSE — DELETE
# ─────────────────────────────────────────────

def delete_universe(session: Session, universe_id: int) -> bool:
    uni = get_universe(session, universe_id)
    if not uni:
        return False
    session.delete(uni)
    session.commit()
    return True


# ─────────────────────────────────────────────
# UNIVERSE CONNECTIONS — CREATE
# ─────────────────────────────────────────────

def create_universe_connection(
    session: Session,
    source_universe_id: int,
    target_universe_id: int,
    connection_type: str = None,
    description: str = None,
) -> UniverseConnection:
    conn = UniverseConnection(
        source_universe_id=source_universe_id,
        target_universe_id=target_universe_id,
        connection_type=connection_type,
        description=description,
    )
    session.add(conn)
    session.commit()
    session.refresh(conn)
    return conn


# ─────────────────────────────────────────────
# UNIVERSE CONNECTIONS — READ
# ─────────────────────────────────────────────

def list_universe_connections(
    session: Session,
    universe_id: int = None,
) -> list[UniverseConnection]:
    q = session.query(UniverseConnection)
    if universe_id:
        q = q.filter(
            (UniverseConnection.source_universe_id == universe_id)
            | (UniverseConnection.target_universe_id == universe_id)
        )
    return q.all()


def delete_universe_connection(session: Session, connection_id: int) -> bool:
    conn = session.query(UniverseConnection).filter(UniverseConnection.id == connection_id).first()
    if not conn:
        return False
    session.delete(conn)
    session.commit()
    return True
