"""
ZenAI — CRUD: Root Entities & Root Entity Links
Root entities are the unique multiversal beings: OM_X, K, _LA, Zendrix Tree.
"""

from sqlalchemy.orm import Session
from app.database.models import RootEntity, RootEntityLink
from app.database.crud._base import save_version

ENTITY_TYPE = "root_entity"


# ─────────────────────────────────────────────
# ROOT ENTITIES
# ─────────────────────────────────────────────

def create_root_entity(
    session: Session,
    name: str,
    type: str = None,
    description: str = None,
    notes: str = None,
    importance_score: int = 100,
    approved_by: str = "user",
) -> RootEntity:
    re = RootEntity(
        name=name,
        type=type,
        description=description,
        notes=notes,
        importance_score=importance_score,
    )
    session.add(re)
    session.flush()
    save_version(session, ENTITY_TYPE, re.id, re, approved_by)
    session.commit()
    session.refresh(re)
    return re


def get_root_entity(session: Session, root_entity_id: int) -> RootEntity | None:
    return session.query(RootEntity).filter(RootEntity.id == root_entity_id).first()


def get_root_entity_by_name(session: Session, name: str) -> RootEntity | None:
    return session.query(RootEntity).filter(RootEntity.name == name).first()


def get_root_entity_by_uuid(session: Session, uuid: str) -> RootEntity | None:
    return session.query(RootEntity).filter(RootEntity.uuid == uuid).first()


def list_root_entities(
    session: Session,
    type: str = None,
    min_importance: int = None,
) -> list[RootEntity]:
    q = session.query(RootEntity)
    if type:
        q = q.filter(RootEntity.type.ilike(f"%{type}%"))
    if min_importance is not None:
        q = q.filter(RootEntity.importance_score >= min_importance)
    return q.order_by(RootEntity.importance_score.desc()).all()


def update_root_entity(
    session: Session,
    root_entity_id: int,
    approved_by: str = "user",
    **kwargs,
) -> RootEntity | None:
    re = get_root_entity(session, root_entity_id)
    if not re:
        return None

    allowed = {"name", "type", "description", "notes", "importance_score"}
    for key, val in kwargs.items():
        if key in allowed:
            setattr(re, key, val)

    save_version(session, ENTITY_TYPE, re.id, re, approved_by)
    session.commit()
    session.refresh(re)
    return re


def delete_root_entity(session: Session, root_entity_id: int) -> bool:
    """WARNING: Deleting seeded root entities (OM_X, K, _LA, Zendrix Tree) is discouraged."""
    re = get_root_entity(session, root_entity_id)
    if not re:
        return False
    session.delete(re)
    session.commit()
    return True


# ─────────────────────────────────────────────
# ROOT ENTITY LINKS
# ─────────────────────────────────────────────

def create_root_entity_link(
    session: Session,
    root_entity_id: int,
    entity_type: str,
    entity_id: int,
    description: str = None,
) -> RootEntityLink:
    """
    entity_type: 'character' | 'faction' | 'location' | 'event' | 'universe' | 'artifact'
    Links a root entity to any other entity in any universe.
    """
    link = RootEntityLink(
        root_entity_id=root_entity_id,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
    )
    session.add(link)
    session.commit()
    session.refresh(link)
    return link


def list_root_entity_links(
    session: Session,
    root_entity_id: int = None,
    entity_type: str = None,
    entity_id: int = None,
) -> list[RootEntityLink]:
    q = session.query(RootEntityLink)
    if root_entity_id is not None:
        q = q.filter(RootEntityLink.root_entity_id == root_entity_id)
    if entity_type:
        q = q.filter(RootEntityLink.entity_type == entity_type)
    if entity_id is not None:
        q = q.filter(RootEntityLink.entity_id == entity_id)
    return q.all()


def delete_root_entity_link(session: Session, link_id: int) -> bool:
    link = session.query(RootEntityLink).filter(RootEntityLink.id == link_id).first()
    if not link:
        return False
    session.delete(link)
    session.commit()
    return True
