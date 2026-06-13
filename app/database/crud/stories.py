"""
ZenAI — CRUD: Stories & Simulation Runs
"""

from sqlalchemy.orm import Session
from app.database.models import Story, SimulationRun
from app.database.crud._base import save_version

# ─────────────────────────────────────────────
# STORIES
# ─────────────────────────────────────────────

ENTITY_TYPE_STORY = "story"


def create_story(
    session: Session,
    title: str,
    summary: str = None,
    raw_text: str = None,
    story_mode: str = "canon",
    canon_status: str = "canon",
    universe_id: int = None,
    approved_by: str = "user",
) -> Story:
    """
    story_mode: canon | non_canon | what_if | alt_timeline | rpg_sim
    """
    story = Story(
        title=title,
        summary=summary,
        raw_text=raw_text,
        story_mode=story_mode,
        canon_status=canon_status,
        universe_id=universe_id,
    )
    session.add(story)
    session.flush()
    save_version(session, ENTITY_TYPE_STORY, story.id, story, approved_by)
    session.commit()
    session.refresh(story)
    return story


def get_story(session: Session, story_id: int) -> Story | None:
    return session.query(Story).filter(Story.id == story_id).first()


def get_story_by_uuid(session: Session, uuid: str) -> Story | None:
    return session.query(Story).filter(Story.uuid == uuid).first()


def list_stories(
    session: Session,
    universe_id: int = None,
    story_mode: str = None,
    canon_status: str = None,
    title_contains: str = None,
) -> list[Story]:
    q = session.query(Story)
    if universe_id is not None:
        q = q.filter(Story.universe_id == universe_id)
    if story_mode:
        q = q.filter(Story.story_mode == story_mode)
    if canon_status:
        q = q.filter(Story.canon_status == canon_status)
    if title_contains:
        q = q.filter(Story.title.ilike(f"%{title_contains}%"))
    return q.order_by(Story.created_at.desc()).all()


def update_story(
    session: Session,
    story_id: int,
    approved_by: str = "user",
    **kwargs,
) -> Story | None:
    story = get_story(session, story_id)
    if not story:
        return None

    allowed = {"title", "summary", "raw_text", "story_mode", "canon_status", "universe_id"}
    for key, val in kwargs.items():
        if key in allowed:
            setattr(story, key, val)

    save_version(session, ENTITY_TYPE_STORY, story.id, story, approved_by)
    session.commit()
    session.refresh(story)
    return story


def delete_story(session: Session, story_id: int) -> bool:
    story = get_story(session, story_id)
    if not story:
        return False
    session.delete(story)
    session.commit()
    return True


# ─────────────────────────────────────────────
# SIMULATION RUNS
# ─────────────────────────────────────────────

def create_simulation_run(
    session: Session,
    title: str,
    premise: str,
    universe_id: int = None,
    affected_entities_json: list = None,
    generated_outcomes_json: list = None,
    reasoning_text: str = None,
) -> SimulationRun:
    run = SimulationRun(
        title=title,
        premise=premise,
        universe_id=universe_id,
        affected_entities_json=affected_entities_json or [],
        generated_outcomes_json=generated_outcomes_json or [],
        reasoning_text=reasoning_text,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def get_simulation_run(session: Session, run_id: int) -> SimulationRun | None:
    return session.query(SimulationRun).filter(SimulationRun.id == run_id).first()


def list_simulation_runs(
    session: Session,
    universe_id: int = None,
    title_contains: str = None,
) -> list[SimulationRun]:
    q = session.query(SimulationRun)
    if universe_id is not None:
        q = q.filter(SimulationRun.universe_id == universe_id)
    if title_contains:
        q = q.filter(SimulationRun.title.ilike(f"%{title_contains}%"))
    return q.order_by(SimulationRun.created_at.desc()).all()


def update_simulation_run(
    session: Session,
    run_id: int,
    **kwargs,
) -> SimulationRun | None:
    run = get_simulation_run(session, run_id)
    if not run:
        return None

    allowed = {
        "title", "premise", "universe_id",
        "affected_entities_json", "generated_outcomes_json", "reasoning_text",
    }
    for key, val in kwargs.items():
        if key in allowed:
            setattr(run, key, val)

    session.commit()
    session.refresh(run)
    return run


def delete_simulation_run(session: Session, run_id: int) -> bool:
    run = get_simulation_run(session, run_id)
    if not run:
        return False
    session.delete(run)
    session.commit()
    return True
