"""
ZenAI — CRUD: StoryLinks
Handles cross-entity links to Stories, with a user-defined link name.
"""

from sqlalchemy.orm import Session
from app.database.models import StoryLink, Story


# ─────────────────────────────────────────────
# CREATE
# ─────────────────────────────────────────────

def create_story_link(
    session: Session,
    source_entity_type: str,
    source_entity_id: int,
    story_id: int,
    link_name: str = None,
) -> StoryLink:
    link = StoryLink(
        source_entity_type=source_entity_type,
        source_entity_id=source_entity_id,
        story_id=story_id,
        link_name=link_name,
    )
    session.add(link)
    session.commit()
    session.refresh(link)
    return link


# ─────────────────────────────────────────────
# READ
# ─────────────────────────────────────────────

def get_story_link(session: Session, link_id: int) -> StoryLink | None:
    return session.query(StoryLink).filter(StoryLink.id == link_id).first()


def list_story_links(
    session: Session,
    source_entity_type: str,
    source_entity_id: int,
) -> list[dict]:
    """
    Returns story links for a given entity, enriched with story title and universe name.
    Each dict: {id, story_id, story_title, universe_name, universe_id, link_name}
    """
    links = (
        session.query(StoryLink)
        .filter(
            StoryLink.source_entity_type == source_entity_type,
            StoryLink.source_entity_id == source_entity_id,
        )
        .order_by(StoryLink.id)
        .all()
    )

    result = []
    for lnk in links:
        story: Story = lnk.story
        result.append({
            "id":           lnk.id,
            "story_id":     lnk.story_id,
            "story_title":  story.title if story else "—",
            "universe_id":  story.universe_id if story else None,
            "universe_name": story.universe.name if (story and story.universe) else "—",
            "link_name":    lnk.link_name or "",
        })
    return result


# ─────────────────────────────────────────────
# DELETE
# ─────────────────────────────────────────────

def delete_story_link(session: Session, link_id: int) -> bool:
    link = get_story_link(session, link_id)
    if not link:
        return False
    session.delete(link)
    session.commit()
    return True


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def list_all_stories_enriched(session: Session) -> list[dict]:
    """
    Returns all stories with universe info — used to populate the link picker.
    Each dict: {id, title, universe_id, universe_name, story_mode}
    """
    stories = session.query(Story).order_by(Story.title).all()
    return [
        {
            "id":            s.id,
            "title":         s.title,
            "universe_id":   s.universe_id,
            "universe_name": s.universe.name if s.universe else "—",
            "story_mode":    s.story_mode,
        }
        for s in stories
    ]
