"""
ZenAI — CRUD: Factions
"""

from sqlalchemy.orm import Session
from app.database.models import Faction
from app.database.crud._base import save_version

ENTITY_TYPE = "faction"


def create_faction(
    session: Session,
    name: str,
    universe_id: int = None,
    faction_id: int = None,
    root_entity_id: int = None,
    founder_id: int = None,
    ideology: str = None,
    description: str = None,
    canon_status: str = "canon",
    importance_score: int = 50,
    approved_by: str = "user",
) -> Faction:
    fac = Faction(
        universe_id=universe_id,
        faction_id=faction_id,
        root_entity_id=root_entity_id,
        name=name,
        founder_id=founder_id,
        ideology=ideology,
        description=description,
        canon_status=canon_status,
        importance_score=importance_score,
    )
    session.add(fac)
    session.flush()
    save_version(session, ENTITY_TYPE, fac.id, fac, approved_by)
    session.commit()
    session.refresh(fac)
    return fac


def get_faction(session: Session, faction_id: int) -> Faction | None:
    return session.query(Faction).filter(Faction.id == faction_id).first()


def get_faction_by_uuid(session: Session, uuid: str) -> Faction | None:
    return session.query(Faction).filter(Faction.uuid == uuid).first()


def list_factions(
    session: Session,
    universe_id: int = None,
    faction_id: int = None,
    root_entity_id: int = None,
    canon_status: str = None,
    min_importance: int = None,
    name_contains: str = None,
    founder_id: int = None,
) -> list[Faction]:
    q = session.query(Faction)
    if universe_id is not None:
        q = q.filter(Faction.universe_id == universe_id)
    if faction_id is not None:
        q = q.filter(Faction.faction_id == faction_id)
    if root_entity_id is not None:
        q = q.filter(Faction.root_entity_id == root_entity_id)
    if canon_status:
        q = q.filter(Faction.canon_status == canon_status)
    if min_importance is not None:
        q = q.filter(Faction.importance_score >= min_importance)
    if name_contains:
        q = q.filter(Faction.name.ilike(f"%{name_contains}%"))
    if founder_id is not None:
        q = q.filter(Faction.founder_id == founder_id)
    return q.order_by(Faction.importance_score.desc()).all()


def update_faction(
    session: Session,
    target_id: int,
    approved_by: str = "user",
    **kwargs,
) -> Faction | None:
    fac = get_faction(session, target_id)
    if not fac:
        return None

    allowed = {"universe_id", "faction_id", "root_entity_id", "name", "founder_id", "ideology", "description", "canon_status", "importance_score"}
    for key, val in kwargs.items():
        if key in allowed:
            setattr(fac, key, val)

    save_version(session, ENTITY_TYPE, fac.id, fac, approved_by)
    session.commit()
    session.refresh(fac)
    return fac


def delete_faction(session: Session, faction_id: int) -> bool:
    fac = get_faction(session, faction_id)
    if not fac:
        return False
    session.delete(fac)
    session.commit()
    return True
