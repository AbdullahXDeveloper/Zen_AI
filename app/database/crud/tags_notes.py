"""
ZenAI — CRUD: Tags, EntityTags, EntityNotes, LoreDocuments
"""

from sqlalchemy.orm import Session
from app.database.models import Tag, EntityTag, EntityNote, LoreDocument

VALID_ENTITY_TYPES = {
    "character", "faction", "location", "event",
    "universe", "artifact", "story",
}


# ─────────────────────────────────────────────
# TAGS
# ─────────────────────────────────────────────

def get_or_create_tag(session: Session, name: str) -> Tag:
    """Return existing tag by name or create it."""
    tag = session.query(Tag).filter(Tag.name == name).first()
    if not tag:
        tag = Tag(name=name)
        session.add(tag)
        session.commit()
        session.refresh(tag)
    return tag


def list_tags(session: Session, name_contains: str = None) -> list[Tag]:
    q = session.query(Tag)
    if name_contains:
        q = q.filter(Tag.name.ilike(f"%{name_contains}%"))
    return q.order_by(Tag.name.asc()).all()


def delete_tag(session: Session, tag_id: int) -> bool:
    tag = session.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        return False
    session.delete(tag)
    session.commit()
    return True


# ─────────────────────────────────────────────
# ENTITY TAGS
# ─────────────────────────────────────────────

def tag_entity(
    session: Session,
    entity_type: str,
    entity_id: int,
    tag_name: str,
) -> EntityTag:
    """Attach a tag (by name) to any entity. Creates the tag if it doesn't exist."""
    if entity_type not in VALID_ENTITY_TYPES:
        raise ValueError(f"Invalid entity_type '{entity_type}'.")

    tag = get_or_create_tag(session, tag_name)

    # Avoid duplicate
    existing = (
        session.query(EntityTag)
        .filter(
            EntityTag.entity_type == entity_type,
            EntityTag.entity_id == entity_id,
            EntityTag.tag_id == tag.id,
        )
        .first()
    )
    if existing:
        return existing

    et = EntityTag(entity_type=entity_type, entity_id=entity_id, tag_id=tag.id)
    session.add(et)
    session.commit()
    session.refresh(et)
    return et


def list_entity_tags(
    session: Session,
    entity_type: str,
    entity_id: int,
) -> list[Tag]:
    """Return Tag objects attached to a specific entity."""
    rows = (
        session.query(EntityTag)
        .filter(
            EntityTag.entity_type == entity_type,
            EntityTag.entity_id == entity_id,
        )
        .all()
    )
    tag_ids = [r.tag_id for r in rows]
    if not tag_ids:
        return []
    return session.query(Tag).filter(Tag.id.in_(tag_ids)).all()


def untag_entity(
    session: Session,
    entity_type: str,
    entity_id: int,
    tag_name: str,
) -> bool:
    tag = session.query(Tag).filter(Tag.name == tag_name).first()
    if not tag:
        return False
    et = (
        session.query(EntityTag)
        .filter(
            EntityTag.entity_type == entity_type,
            EntityTag.entity_id == entity_id,
            EntityTag.tag_id == tag.id,
        )
        .first()
    )
    if not et:
        return False
    session.delete(et)
    session.commit()
    return True


def find_entities_by_tag(
    session: Session,
    tag_name: str,
    entity_type: str = None,
) -> list[EntityTag]:
    """Return all EntityTag rows for a given tag name (optionally filtered by entity type)."""
    tag = session.query(Tag).filter(Tag.name == tag_name).first()
    if not tag:
        return []
    q = session.query(EntityTag).filter(EntityTag.tag_id == tag.id)
    if entity_type:
        q = q.filter(EntityTag.entity_type == entity_type)
    return q.all()


# ─────────────────────────────────────────────
# ENTITY NOTES
# ─────────────────────────────────────────────

def add_entity_note(
    session: Session,
    entity_type: str,
    entity_id: int,
    note_text: str,
) -> EntityNote:
    if entity_type not in VALID_ENTITY_TYPES:
        raise ValueError(f"Invalid entity_type '{entity_type}'.")

    note = EntityNote(
        entity_type=entity_type,
        entity_id=entity_id,
        note_text=note_text,
    )
    session.add(note)
    session.commit()
    session.refresh(note)
    return note


def list_entity_notes(
    session: Session,
    entity_type: str,
    entity_id: int,
) -> list[EntityNote]:
    return (
        session.query(EntityNote)
        .filter(
            EntityNote.entity_type == entity_type,
            EntityNote.entity_id == entity_id,
        )
        .order_by(EntityNote.created_at.desc())
        .all()
    )


def delete_entity_note(session: Session, note_id: int) -> bool:
    note = session.query(EntityNote).filter(EntityNote.id == note_id).first()
    if not note:
        return False
    session.delete(note)
    session.commit()
    return True


# ─────────────────────────────────────────────
# LORE DOCUMENTS
# ─────────────────────────────────────────────

def create_lore_document(
    session: Session,
    filename: str,
    raw_text: str = None,
) -> LoreDocument:
    doc = LoreDocument(filename=filename, raw_text=raw_text, processed=False)
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return doc


def get_lore_document(session: Session, doc_id: int) -> LoreDocument | None:
    return session.query(LoreDocument).filter(LoreDocument.id == doc_id).first()


def list_lore_documents(
    session: Session,
    processed: bool = None,
) -> list[LoreDocument]:
    q = session.query(LoreDocument)
    if processed is not None:
        q = q.filter(LoreDocument.processed == processed)
    return q.order_by(LoreDocument.upload_date.desc()).all()


def mark_lore_document_processed(session: Session, doc_id: int) -> bool:
    doc = get_lore_document(session, doc_id)
    if not doc:
        return False
    doc.processed = True
    session.commit()
    return True


def delete_lore_document(session: Session, doc_id: int) -> bool:
    doc = get_lore_document(session, doc_id)
    if not doc:
        return False
    session.delete(doc)
    session.commit()
    return True
