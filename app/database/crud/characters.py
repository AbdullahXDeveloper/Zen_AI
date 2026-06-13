"""
ZenAI — CRUD: Characters
Handles Character and CharacterPower create/read/update/delete.
"""

from datetime import datetime
from sqlalchemy.orm import Session
from app.database.models import Character, CharacterPower, Power
from app.database.crud._base import save_version

ENTITY_TYPE = "character"


# ─────────────────────────────────────────────
# CHARACTER — CREATE
# ─────────────────────────────────────────────

def create_character(
    session: Session,
    universe_id: int,
    name: str,
    titles: str = None,
    aliases: str = None,
    species: str = None,
    traits_json: dict = None,
    personality: str = None,
    motivations: str = None,
    goals: str = None,
    ideology: str = None,
    canon_status: str = "canon",
    importance_score: int = 50,
    parent_character_id: int = None,
    approved_by: str = "user",
) -> Character:
    char = Character(
        universe_id=universe_id,
        name=name,
        titles=titles,
        aliases=aliases,
        species=species,
        traits_json=traits_json or {},
        personality=personality,
        motivations=motivations,
        goals=goals,
        ideology=ideology,
        canon_status=canon_status,
        importance_score=importance_score,
        parent_character_id=parent_character_id,
        version=1,
    )
    session.add(char)
    session.flush()
    save_version(session, ENTITY_TYPE, char.id, char, approved_by)
    session.commit()
    session.refresh(char)
    return char


# ─────────────────────────────────────────────
# CHARACTER — READ
# ─────────────────────────────────────────────

def get_character(session: Session, character_id: int) -> Character | None:
    return session.query(Character).filter(Character.id == character_id).first()


def get_character_by_uuid(session: Session, uuid: str) -> Character | None:
    return session.query(Character).filter(Character.uuid == uuid).first()


def list_characters(
    session: Session,
    universe_id: int = None,
    canon_status: str = None,
    min_importance: int = None,
    name_contains: str = None,
    species: str = None,
) -> list[Character]:
    q = session.query(Character)
    if universe_id is not None:
        q = q.filter(Character.universe_id == universe_id)
    if canon_status:
        q = q.filter(Character.canon_status == canon_status)
    if min_importance is not None:
        q = q.filter(Character.importance_score >= min_importance)
    if name_contains:
        q = q.filter(Character.name.ilike(f"%{name_contains}%"))
    if species:
        q = q.filter(Character.species.ilike(f"%{species}%"))
    return q.order_by(Character.importance_score.desc()).all()


def list_character_variants(session: Session, parent_character_id: int) -> list[Character]:
    """Return all variant characters of a parent character."""
    return session.query(Character).filter(Character.parent_character_id == parent_character_id).all()


# ─────────────────────────────────────────────
# CHARACTER — UPDATE
# ─────────────────────────────────────────────

def update_character(
    session: Session,
    character_id: int,
    approved_by: str = "user",
    **kwargs,
) -> Character | None:
    char = get_character(session, character_id)
    if not char:
        return None

    allowed = {
        "name", "titles", "aliases", "species", "traits_json",
        "personality", "motivations", "goals", "ideology",
        "canon_status", "importance_score", "parent_character_id",
    }
    for key, val in kwargs.items():
        if key in allowed:
            setattr(char, key, val)

    char.version = (char.version or 1) + 1
    char.updated_at = datetime.utcnow()

    save_version(session, ENTITY_TYPE, char.id, char, approved_by)
    session.commit()
    session.refresh(char)
    return char


# ─────────────────────────────────────────────
# CHARACTER — DELETE
# ─────────────────────────────────────────────

def delete_character(session: Session, character_id: int) -> bool:
    char = get_character(session, character_id)
    if not char:
        return False
    session.delete(char)
    session.commit()
    return True


# ─────────────────────────────────────────────
# CHARACTER POWERS — ADD / REMOVE / LIST
# ─────────────────────────────────────────────

def add_power_to_character(
    session: Session,
    character_id: int,
    power_id: int,
    proficiency: int = 50,
) -> CharacterPower:
    # Upsert: if already exists, update proficiency
    existing = (
        session.query(CharacterPower)
        .filter(
            CharacterPower.character_id == character_id,
            CharacterPower.power_id == power_id,
        )
        .first()
    )
    if existing:
        existing.proficiency = proficiency
        session.commit()
        return existing

    cp = CharacterPower(
        character_id=character_id,
        power_id=power_id,
        proficiency=proficiency,
    )
    session.add(cp)
    session.commit()
    return cp


def remove_power_from_character(
    session: Session,
    character_id: int,
    power_id: int,
) -> bool:
    cp = (
        session.query(CharacterPower)
        .filter(
            CharacterPower.character_id == character_id,
            CharacterPower.power_id == power_id,
        )
        .first()
    )
    if not cp:
        return False
    session.delete(cp)
    session.commit()
    return True


def list_character_powers(session: Session, character_id: int) -> list[CharacterPower]:
    return (
        session.query(CharacterPower)
        .filter(CharacterPower.character_id == character_id)
        .all()
    )
