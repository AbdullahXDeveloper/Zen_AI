"""
ZenAI — CRUD: Entity Links
"""
from sqlalchemy.orm import Session
from app.database.models import (
    EntityLink, Character, Faction, Location, Event, Artifact, Story, CosmicNode, Universe, RootEntity
)

def create_entity_link(
    session: Session,
    source_entity_type: str,
    source_entity_id: int,
    target_entity_type: str,
    target_entity_id: int,
    link_name: str | None = None
) -> EntityLink:
    link = EntityLink(
        source_entity_type=source_entity_type,
        source_entity_id=source_entity_id,
        target_entity_type=target_entity_type,
        target_entity_id=target_entity_id,
        link_name=link_name
    )
    session.add(link)
    session.commit()
    session.refresh(link)
    return link


def upsert_single_entity_link(
    session: Session,
    source_entity_type: str,
    source_entity_id: int,
    target_entity_type: str,
    target_entity_id: int | None,
) -> EntityLink | None:
    """
    Ensures at most ONE link of a given target_entity_type for a source entity.
    - If target_entity_id is None  → deletes existing link (if any).
    - If target_entity_id is set   → creates/replaces with the new target.
    """
    existing = session.query(EntityLink).filter(
        EntityLink.source_entity_type == source_entity_type,
        EntityLink.source_entity_id  == source_entity_id,
        EntityLink.target_entity_type == target_entity_type,
    ).first()

    if target_entity_id is None:
        if existing:
            session.delete(existing)
            session.commit()
        return None

    if existing:
        existing.target_entity_id = target_entity_id
        session.commit()
        session.refresh(existing)
        return existing

    return create_entity_link(
        session, source_entity_type, source_entity_id,
        target_entity_type, target_entity_id,
    )


def get_single_entity_link(
    session: Session,
    source_entity_type: str,
    source_entity_id: int,
    target_entity_type: str,
) -> int | None:
    """Returns the target_entity_id of the single link for this type, or None."""
    link = session.query(EntityLink).filter(
        EntityLink.source_entity_type == source_entity_type,
        EntityLink.source_entity_id  == source_entity_id,
        EntityLink.target_entity_type == target_entity_type,
    ).first()
    return link.target_entity_id if link else None



def delete_entity_link(session: Session, link_id: int):
    link = session.query(EntityLink).filter(EntityLink.id == link_id).first()
    if link:
        session.delete(link)
        session.commit()


def list_entity_links(session: Session, source_type: str, source_id: int) -> list[dict]:
    """
    Returns a list of link dicts for the UI.
    Dynamically fetches the target entity's name and universe name.
    """
    links = session.query(EntityLink).filter(
        EntityLink.source_entity_type == source_type,
        EntityLink.source_entity_id == source_id
    ).all()

    # Model mapping for dynamic lookups
    MODEL_MAP = {
        "character": Character,
        "faction": Faction,
        "location": Location,
        "event": Event,
        "artifact": Artifact,
        "story": Story,
        "cosmic_node": CosmicNode,
        "universe": Universe,
        "root_entity": RootEntity,
    }

    result = []
    for lnk in links:
        target_model = MODEL_MAP.get(lnk.target_entity_type)
        if not target_model:
            continue
            
        target_entity = session.query(target_model).filter(target_model.id == lnk.target_entity_id).first()
        if not target_entity:
            continue

        # Get name (stories have 'title', others have 'name')
        t_name = getattr(target_entity, "name", None) or getattr(target_entity, "title", "Unknown")
        
        # Get universe name
        uni_name = "—"
        if hasattr(target_entity, "universe") and target_entity.universe:
            uni_name = target_entity.universe.name
            
        # Specific metadata (like story mode for stories)
        extra_meta = ""
        if lnk.target_entity_type == "story" and hasattr(target_entity, "story_mode"):
            extra_meta = target_entity.story_mode
        elif lnk.target_entity_type == "cosmic_node" and hasattr(target_entity, "node_type"):
            extra_meta = target_entity.node_type

        result.append({
            "id": lnk.id,
            "target_entity_type": lnk.target_entity_type,
            "target_entity_id": lnk.target_entity_id,
            "target_name": t_name,
            "universe_name": uni_name,
            "link_name": lnk.link_name,
            "extra_meta": extra_meta
        })

    return result

def get_all_entities_for_picker(session: Session, entity_type: str) -> list[dict]:
    """
    Returns all entities of a given type so the dropdown can populate.
    Includes ID, name/title, and universe_id/universe_name for filtering.
    """
    MODEL_MAP = {
        "character": Character,
        "faction": Faction,
        "location": Location,
        "event": Event,
        "artifact": Artifact,
        "story": Story,
        "cosmic_node": CosmicNode,
        "universe": Universe,
        "root_entity": RootEntity,
    }
    target_model = MODEL_MAP.get(entity_type)
    if not target_model:
        return []

    entities = session.query(target_model).all()
    result = []
    for e in entities:
        t_name = getattr(e, "name", None) or getattr(e, "title", "Unknown")
        uid = getattr(e, "universe_id", None)
        uni_name = "—"
        if hasattr(e, "universe") and e.universe:
            uni_name = e.universe.name
        
        extra = ""
        if entity_type == "story":
            extra = getattr(e, "story_mode", "canon")
        elif entity_type == "cosmic_node":
            extra = getattr(e, "node_type", "custom")

        result.append({
            "id": e.id,
            "name": t_name,
            "universe_id": uid,
            "universe_name": uni_name,
            "extra_meta": extra
        })
    
    # Sort alphabetically by name
    result.sort(key=lambda x: str(x["name"]).lower())
    return result
