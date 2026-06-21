"""
ZenAI — CRUD: CosmicNodes
Handles the hierarchical cosmic entity tree inside each Universe.
"""

from sqlalchemy.orm import Session
from app.database.models import CosmicNode


# ─────────────────────────────────────────────
# CREATE
# ─────────────────────────────────────────────

def create_cosmic_node(
    session: Session,
    universe_id: int,
    name: str,
    node_type: str = "custom",
    description: str = None,
    importance_score: int = 50,
    parent_id: int = None,
) -> CosmicNode:
    node = CosmicNode(
        universe_id=universe_id,
        name=name,
        node_type=node_type,
        description=description,
        importance_score=importance_score,
        parent_id=parent_id,
    )
    session.add(node)
    session.commit()
    session.refresh(node)
    return node


# ─────────────────────────────────────────────
# READ
# ─────────────────────────────────────────────

def get_cosmic_node(session: Session, node_id: int) -> CosmicNode | None:
    return session.query(CosmicNode).filter(CosmicNode.id == node_id).first()


def list_cosmic_nodes_by_universe(
    session: Session, universe_id: int
) -> list[CosmicNode]:
    """Returns ALL nodes in a universe (all depths), ordered by id for stable display."""
    return (
        session.query(CosmicNode)
        .filter(CosmicNode.universe_id == universe_id)
        .order_by(CosmicNode.id)
        .all()
    )


def list_root_cosmic_nodes(
    session: Session, universe_id: int
) -> list[CosmicNode]:
    """Returns only top-level nodes (parent_id IS NULL) for a universe."""
    return (
        session.query(CosmicNode)
        .filter(
            CosmicNode.universe_id == universe_id,
            CosmicNode.parent_id == None,  # noqa: E711
        )
        .order_by(CosmicNode.id)
        .all()
    )


def list_cosmic_node_children(
    session: Session, parent_id: int
) -> list[CosmicNode]:
    """Returns direct children of a node."""
    return (
        session.query(CosmicNode)
        .filter(CosmicNode.parent_id == parent_id)
        .order_by(CosmicNode.id)
        .all()
    )


# ─────────────────────────────────────────────
# UPDATE
# ─────────────────────────────────────────────

def update_cosmic_node(
    session: Session,
    node_id: int,
    **kwargs,
) -> CosmicNode | None:
    node = get_cosmic_node(session, node_id)
    if not node:
        return None

    allowed = {"name", "node_type", "description", "importance_score", "parent_id"}
    for key, val in kwargs.items():
        if key in allowed:
            setattr(node, key, val)

    session.commit()
    session.refresh(node)
    return node


# ─────────────────────────────────────────────
# DELETE
# ─────────────────────────────────────────────

def delete_cosmic_node(session: Session, node_id: int) -> bool:
    """Deletes node and all its descendants (via cascade)."""
    node = get_cosmic_node(session, node_id)
    if not node:
        return False
    session.delete(node)
    session.commit()
    return True
