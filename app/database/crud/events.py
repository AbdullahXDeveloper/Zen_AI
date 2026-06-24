"""
ZenAI — CRUD: Events & EventParticipants
"""

from sqlalchemy.orm import Session
from app.database.models import Event, EventParticipant
from app.database.crud._base import save_version

ENTITY_TYPE = "event"


# ─────────────────────────────────────────────
# EVENTS
# ─────────────────────────────────────────────

def create_event(
    session: Session,
    name: str,
    universe_id: int = None,
    faction_id: int = None,
    root_entity_id: int = None,
    description: str = None,
    date_value: str = None,
    date_label: str = None,
    event_type: str = "other",
    canon_status: str = "canon",
    importance_score: int = 50,
    approved_by: str = "user",
) -> Event:
    evt = Event(
        universe_id=universe_id,
        faction_id=faction_id,
        root_entity_id=root_entity_id,
        name=name,
        description=description,
        date_value=date_value,
        date_label=date_label,
        event_type=event_type,
        canon_status=canon_status,
        importance_score=importance_score,
    )
    session.add(evt)
    session.flush()
    save_version(session, ENTITY_TYPE, evt.id, evt, approved_by)
    session.commit()
    session.refresh(evt)
    return evt


def get_event(session: Session, event_id: int) -> Event | None:
    return session.query(Event).filter(Event.id == event_id).first()


def get_event_by_uuid(session: Session, uuid: str) -> Event | None:
    return session.query(Event).filter(Event.uuid == uuid).first()


def list_events(
    session: Session,
    universe_id: int = None,
    faction_id: int = None,
    root_entity_id: int = None,
    canon_status: str = None,
    event_type: str = None,
    min_importance: int = None,
    name_contains: str = None,
) -> list[Event]:
    q = session.query(Event)
    if universe_id is not None:
        q = q.filter(Event.universe_id == universe_id)
    if faction_id is not None:
        q = q.filter(Event.faction_id == faction_id)
    if root_entity_id is not None:
        q = q.filter(Event.root_entity_id == root_entity_id)
    if event_type:
        q = q.filter(Event.event_type == event_type)
    if canon_status:
        q = q.filter(Event.canon_status == canon_status)
    if min_importance is not None:
        q = q.filter(Event.importance_score >= min_importance)
    if name_contains:
        q = q.filter(Event.name.ilike(f"%{name_contains}%"))
    # Sort chronologically by date_value (stored as sortable string)
    return q.order_by(Event.date_value.asc()).all()


def update_event(
    session: Session,
    event_id: int,
    approved_by: str = "user",
    **kwargs,
) -> Event | None:
    evt = get_event(session, event_id)
    if not evt:
        return None

    allowed = {
        "universe_id", "faction_id", "root_entity_id", "name", "description", "date_value", "date_label",
        "event_type", "canon_status", "importance_score"
    }
    for key, val in kwargs.items():
        if key in allowed:
            setattr(evt, key, val)

    save_version(session, ENTITY_TYPE, evt.id, evt, approved_by)
    session.commit()
    session.refresh(evt)
    return evt


def delete_event(session: Session, event_id: int) -> bool:
    evt = get_event(session, event_id)
    if not evt:
        return False
    session.delete(evt)
    session.commit()
    return True


# ─────────────────────────────────────────────
# EVENT PARTICIPANTS
# ─────────────────────────────────────────────

def add_event_participant(
    session: Session,
    event_id: int,
    entity_type: str,
    entity_id: int,
    role: str = None,
) -> EventParticipant:
    """
    entity_type: 'character' | 'faction' | 'location' | 'artifact'
    role: e.g. 'attacker', 'victim', 'witness', 'location'
    """
    ep = EventParticipant(
        event_id=event_id,
        entity_type=entity_type,
        entity_id=entity_id,
        role=role,
    )
    session.add(ep)
    session.commit()
    session.refresh(ep)
    return ep


def list_event_participants(session: Session, event_id: int) -> list[EventParticipant]:
    return (
        session.query(EventParticipant)
        .filter(EventParticipant.event_id == event_id)
        .all()
    )


def list_entity_events(
    session: Session,
    entity_type: str,
    entity_id: int,
) -> list[EventParticipant]:
    """Return all event_participant rows for a given entity (e.g. all events a character was in)."""
    return (
        session.query(EventParticipant)
        .filter(
            EventParticipant.entity_type == entity_type,
            EventParticipant.entity_id == entity_id,
        )
        .all()
    )


def remove_event_participant(session: Session, participant_id: int) -> bool:
    ep = session.query(EventParticipant).filter(EventParticipant.id == participant_id).first()
    if not ep:
        return False
    session.delete(ep)
    session.commit()
    return True
