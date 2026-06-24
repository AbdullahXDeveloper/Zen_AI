"""
ZenAI — CRUD: Locations
"""

from sqlalchemy.orm import Session
from app.database.models import Location
from app.database.crud._base import save_version

ENTITY_TYPE = "location"


def create_location(
    session: Session,
    name: str,
    universe_id: int = None,
    faction_id: int = None,
    root_entity_id: int = None,
    description: str = None,
    type: str = None,
    canon_status: str = "canon",
    importance_score: int = 50,
    approved_by: str = "user",
) -> Location:
    loc = Location(
        universe_id=universe_id,
        faction_id=faction_id,
        root_entity_id=root_entity_id,
        name=name,
        description=description,
        type=type,
        canon_status=canon_status,
        importance_score=importance_score,
    )
    session.add(loc)
    session.flush()
    save_version(session, ENTITY_TYPE, loc.id, loc, approved_by)
    session.commit()
    session.refresh(loc)
    return loc


def get_location(session: Session, location_id: int) -> Location | None:
    return session.query(Location).filter(Location.id == location_id).first()


def get_location_by_uuid(session: Session, uuid: str) -> Location | None:
    return session.query(Location).filter(Location.uuid == uuid).first()


def list_locations(
    session: Session,
    universe_id: int = None,
    faction_id: int = None,
    root_entity_id: int = None,
    canon_status: str = None,
    min_importance: int = None,
    name_contains: str = None,
    loc_type: str = None,
) -> list[Location]:
    q = session.query(Location)
    if universe_id is not None:
        q = q.filter(Location.universe_id == universe_id)
    if faction_id is not None:
        q = q.filter(Location.faction_id == faction_id)
    if root_entity_id is not None:
        q = q.filter(Location.root_entity_id == root_entity_id)
    if canon_status:
        q = q.filter(Location.canon_status == canon_status)
    if loc_type:
        q = q.filter(Location.type.ilike(f"%{loc_type}%"))
    if min_importance is not None:
        q = q.filter(Location.importance_score >= min_importance)
    if name_contains:
        q = q.filter(Location.name.ilike(f"%{name_contains}%"))
    return q.order_by(Location.importance_score.desc()).all()


def update_location(
    session: Session,
    location_id: int,
    approved_by: str = "user",
    **kwargs,
) -> Location | None:
    loc = get_location(session, location_id)
    if not loc:
        return None

    allowed = {"universe_id", "faction_id", "root_entity_id", "name", "description", "type", "canon_status", "importance_score"}
    for key, val in kwargs.items():
        if key in allowed:
            setattr(loc, key, val)

    save_version(session, ENTITY_TYPE, loc.id, loc, approved_by)
    session.commit()
    session.refresh(loc)
    return loc


def delete_location(session: Session, location_id: int) -> bool:
    loc = get_location(session, location_id)
    if not loc:
        return False
    session.delete(loc)
    session.commit()
    return True
