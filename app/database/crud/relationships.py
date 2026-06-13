"""
ZenAI — CRUD: Relationships (Character-to-Character Graph Edges)
edge_type values: friend, enemy, family, mentor, student,
                  created, destroyed, owns, located_in, participated_in
"""

from sqlalchemy.orm import Session
from app.database.models import RelationshipEdge

VALID_EDGE_TYPES = {
    "friend", "enemy", "family", "mentor", "student",
    "created", "destroyed", "owns", "located_in", "participated_in",
}


def create_relationship(
    session: Session,
    character_a_id: int,
    character_b_id: int,
    edge_type: str,
    description: str = None,
) -> RelationshipEdge:
    if edge_type not in VALID_EDGE_TYPES:
        raise ValueError(f"Invalid edge_type '{edge_type}'. Must be one of: {VALID_EDGE_TYPES}")

    rel = RelationshipEdge(
        character_a_id=character_a_id,
        character_b_id=character_b_id,
        edge_type=edge_type,
        description=description,
    )
    session.add(rel)
    session.commit()
    session.refresh(rel)
    return rel


def get_relationship(session: Session, relationship_id: int) -> RelationshipEdge | None:
    return session.query(RelationshipEdge).filter(RelationshipEdge.id == relationship_id).first()


def list_relationships(
    session: Session,
    character_id: int = None,
    edge_type: str = None,
) -> list[RelationshipEdge]:
    """
    If character_id is given, returns all relationships where
    that character is either side (A or B).
    """
    q = session.query(RelationshipEdge)
    if character_id is not None:
        q = q.filter(
            (RelationshipEdge.character_a_id == character_id)
            | (RelationshipEdge.character_b_id == character_id)
        )
    if edge_type:
        q = q.filter(RelationshipEdge.edge_type == edge_type)
    return q.all()


def list_relationships_between(
    session: Session,
    character_a_id: int,
    character_b_id: int,
) -> list[RelationshipEdge]:
    """Return all edges between two specific characters (both directions)."""
    return (
        session.query(RelationshipEdge)
        .filter(
            (
                (RelationshipEdge.character_a_id == character_a_id)
                & (RelationshipEdge.character_b_id == character_b_id)
            )
            | (
                (RelationshipEdge.character_a_id == character_b_id)
                & (RelationshipEdge.character_b_id == character_a_id)
            )
        )
        .all()
    )


def update_relationship(
    session: Session,
    relationship_id: int,
    edge_type: str = None,
    description: str = None,
) -> RelationshipEdge | None:
    rel = get_relationship(session, relationship_id)
    if not rel:
        return None

    if edge_type is not None:
        if edge_type not in VALID_EDGE_TYPES:
            raise ValueError(f"Invalid edge_type '{edge_type}'.")
        rel.edge_type = edge_type
    if description is not None:
        rel.description = description

    session.commit()
    session.refresh(rel)
    return rel


def delete_relationship(session: Session, relationship_id: int) -> bool:
    rel = get_relationship(session, relationship_id)
    if not rel:
        return False
    session.delete(rel)
    session.commit()
    return True
