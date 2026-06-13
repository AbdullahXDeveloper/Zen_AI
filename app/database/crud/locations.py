"""
ZenAI — CRUD: Locations
"""

from sqlalchemy.orm import Session
from app.database.models import Location
from app.database.crud._base import save_version

ENTITY_TYPE = "location"


def create_location(
    session: Session,
    universe_id: int,
    name: str,
    description: str = None,
    type: str = None,
    canon_status: str = "canon",
    importance_score: int = 50,
    approved_by: str = "user",
) -> Location:
    loc = Location(
        universe_id=universe_id,
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
    canon_status: str = None,
    type: str = None,
    min_importance: int = None,
    name_contains: str = None,
) -> list[Location]:
    q = session.query(Location)
    if universe_id is not None:
        q = q.filter(Location.universe_id == universe_id)
    if canon_status:
        q = q.filter(Location.canon_status == canon_status)
    if type:
        q = q.filter(Location.type.ilike(f"%{type}%"))
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

    allowed = {"name", "description", "type", "canon_status", "importance_score"}
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
