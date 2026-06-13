"""
Utility CRUD helpers for ZenAI database operations.
"""

from typing import Dict, Iterable, Optional

from sqlalchemy.orm import Session

from app.database.models import Character, LoreDocument, RootEntity, Universe


def create_universe(session: Session, name: str, description: str = "", canon_status: str = "canon") -> Universe:
    """Create a new universe record."""
    universe = Universe(name=name, description=description, canon_status=canon_status)
    session.add(universe)
    session.commit()
    session.refresh(universe)
    return universe


def list_universes(session: Session) -> Iterable[Universe]:
    """Return all universes in the database."""
    return session.query(Universe).order_by(Universe.id).all()


def get_universe(session: Session, universe_id: Optional[int] = None, uuid: Optional[str] = None) -> Optional[Universe]:
    """Fetch one universe by id or uuid."""
    query = session.query(Universe)
    if universe_id is not None:
        return query.filter(Universe.id == universe_id).first()
    if uuid is not None:
        return query.filter(Universe.uuid == uuid).first()
    return None


def create_root_entity(session: Session, name: str, type_: str = "Root Entity", description: str = "") -> RootEntity:
    """Create a root entity entry."""
    entity = RootEntity(name=name, type=type_, description=description)
    session.add(entity)
    session.commit()
    session.refresh(entity)
    return entity


def list_root_entities(session: Session) -> Iterable[RootEntity]:
    """Return all root entities."""
    return session.query(RootEntity).order_by(RootEntity.id).all()


def create_character(session: Session, universe_id: int, name: str, **kwargs) -> Character:
    """Create a character under a universe."""
    character = Character(universe_id=universe_id, name=name, **kwargs)
    session.add(character)
    session.commit()
    session.refresh(character)
    return character


def add_lore_document(session: Session, filename: str, raw_text: str = "", processed: bool = False) -> LoreDocument:
    """Store an uploaded lore document in the database."""
    doc = LoreDocument(filename=filename, raw_text=raw_text, processed=processed)
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return doc


def get_stats(session: Session) -> Dict[str, int]:
    """Return lightweight database counts used by the UI/CLI."""
    return {
        "universes": session.query(Universe).count(),
        "characters": session.query(Character).count(),
        "root_entities": session.query(RootEntity).count(),
        "lore_documents": session.query(LoreDocument).count(),
    }
