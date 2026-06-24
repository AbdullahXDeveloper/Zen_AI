"""
ZenAI — CRUD: Artifacts
"""

from sqlalchemy.orm import Session
from app.database.models import Artifact
from app.database.crud._base import save_version

ENTITY_TYPE = "artifact"


def create_artifact(
    session: Session,
    name: str,
    universe_id: int = None,
    faction_id: int = None,
    root_entity_id: int = None,
    description: str = None,
    owner_id: int = None,
    powers_json: list = None,
    importance_score: int = 50,
    approved_by: str = "user",
) -> Artifact:
    art = Artifact(
        universe_id=universe_id,
        faction_id=faction_id,
        root_entity_id=root_entity_id,
        name=name,
        description=description,
        owner_id=owner_id,
        powers_json=powers_json or [],
        importance_score=importance_score,
    )
    session.add(art)
    session.flush()
    save_version(session, ENTITY_TYPE, art.id, art, approved_by)
    session.commit()
    session.refresh(art)
    return art


def get_artifact(session: Session, artifact_id: int) -> Artifact | None:
    return session.query(Artifact).filter(Artifact.id == artifact_id).first()


def get_artifact_by_uuid(session: Session, uuid: str) -> Artifact | None:
    return session.query(Artifact).filter(Artifact.uuid == uuid).first()


def list_artifacts(
    session: Session,
    universe_id: int = None,
    faction_id: int = None,
    root_entity_id: int = None,
    canon_status: str = None,
    min_importance: int = None,
    name_contains: str = None,
    owner_id: int = None,
) -> list[Artifact]:
    q = session.query(Artifact)
    if universe_id is not None:
        q = q.filter(Artifact.universe_id == universe_id)
    if faction_id is not None:
        q = q.filter(Artifact.faction_id == faction_id)
    if root_entity_id is not None:
        q = q.filter(Artifact.root_entity_id == root_entity_id)
    if owner_id is not None:
        q = q.filter(Artifact.owner_id == owner_id)
    if min_importance is not None:
        q = q.filter(Artifact.importance_score >= min_importance)
    if name_contains:
        q = q.filter(Artifact.name.ilike(f"%{name_contains}%"))
    return q.order_by(Artifact.importance_score.desc()).all()


def update_artifact(
    session: Session,
    artifact_id: int,
    approved_by: str = "user",
    **kwargs,
) -> Artifact | None:
    art = get_artifact(session, artifact_id)
    if not art:
        return None

    allowed = {"universe_id", "faction_id", "root_entity_id", "name", "description", "owner_id", "powers_json", "importance_score"}
    for key, val in kwargs.items():
        if key in allowed:
            setattr(art, key, val)

    save_version(session, ENTITY_TYPE, art.id, art, approved_by)
    session.commit()
    session.refresh(art)
    return art


def delete_artifact(session: Session, artifact_id: int) -> bool:
    art = get_artifact(session, artifact_id)
    if not art:
        return False
    session.delete(art)
    session.commit()
    return True
