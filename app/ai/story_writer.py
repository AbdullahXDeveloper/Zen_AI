"""
app/ai/story_writer.py

Generates story content (chapters, scenes, dialogue) grounded in DB
context. Supports the story_mode values used by the `stories` table:
canon, non_canon, what_if, alt_timeline, rpg_sim.

This is the foundation Module 11 (AI Story Assistant) builds on, but
is also usable standalone.

KEY RULE: Like other generator modules, returns content for
Approve/Reject/Edit. On approval, caller persists via
crud.create_story(session, ...).
"""
from typing import Optional

from app.ai.claude_client import get_client
from app.ai.context_builder import build_context, build_universe_context, build_character_context
from app.database import crud


_VALID_MODES = {"canon", "non_canon", "what_if", "alt_timeline", "rpg_sim"}

_MODE_GUIDANCE = {
    "canon": "This must be consistent with established canon. Do not contradict any existing facts.",
    "non_canon": "This is a non-canon side story. It may explore tangents but should still feel "
                  "true to the characters and setting.",
    "what_if": "This is a 'what if' scenario — explore an alternate possibility while keeping "
               "characters recognizable. Make the divergence point clear.",
    "alt_timeline": "This is set in an alternate timeline. Established history may differ, but "
                    "note clearly what has changed and why.",
    "rpg_sim": "This is an interactive RPG-style scene. Write up to a decision point, then stop "
               "and present 2-4 possible player actions/choices.",
}


def generate_story(session, prompt: str, story_mode: str = "canon",
                    universe_id: Optional[int] = None,
                    character_ids: Optional[list[int]] = None,
                    target_length: str = "medium",
                    title: Optional[str] = None) -> dict:
    """
    Generate a story/chapter.

    prompt: free-form description of what should happen
    story_mode: one of canon, non_canon, what_if, alt_timeline, rpg_sim
    universe_id: grounds the story in this universe's lore
    character_ids: specific characters to feature/keep consistent
    target_length: "short" (~300 words), "medium" (~700), "long" (~1500)
    title: optional title override; if None, Claude proposes one

    Returns dict: {
      "title": str,
      "content": str,
      "story_mode": str,
      "canon_status": str,   # mirrors story_mode where applicable
      "universe_id": int | None,
      "character_ids": list[int],
      "choices": list[str] | None   # only for rpg_sim
    }
    """
    if story_mode not in _VALID_MODES:
        raise ValueError(f"story_mode must be one of {_VALID_MODES}, got '{story_mode}'")

    length_words = {"short": 300, "medium": 700, "long": 1500}.get(target_length, 700)

    context_parts = []
    if universe_id:
        ctx = build_universe_context(session, universe_id)
        if ctx:
            context_parts.append(ctx)

    if character_ids:
        for cid in character_ids:
            ctx = build_character_context(session, cid)
            if ctx:
                context_parts.append(ctx)

    context_str = "\n".join(context_parts) if context_parts else "(No existing context provided.)"

    mode_guidance = _MODE_GUIDANCE[story_mode]

    system = (
        "You are the story-writing engine for Zen AI, a worldbuilding tool for the "
        "Zendrix multiverse. Write vivid, character-driven prose consistent with the "
        "provided lore context. "
        f"{mode_guidance}"
    )

    title_instruction = f'Use this exact title: "{title}"' if title else "Propose a fitting title."

    rpg_instruction = ""
    if story_mode == "rpg_sim":
        rpg_instruction = (
            '\n\nAlso include a "choices" array in the JSON with 2-4 short strings '
            "describing the possible next actions the player/reader could choose."
        )

    user_prompt = (
        f"## Lore Context\n{context_str}\n\n"
        f"## Story Request\n{prompt}\n\n"
        f"## Requirements\n"
        f"- Target length: ~{length_words} words\n"
        f"- {title_instruction}\n"
        f"- Story mode: {story_mode}\n"
        f"{rpg_instruction}\n\n"
        "Return a JSON object with fields: \"title\" (string), \"content\" (string, the "
        "full story text)"
        + (', "choices" (array of strings)' if story_mode == "rpg_sim" else "")
        + "."
    )

    client = get_client()
    result = client.ask_json(user_prompt, system=system, temperature=1.0,
                              max_tokens=max(2048, length_words * 3))

    if not isinstance(result, dict):
        raise ValueError(f"Expected JSON object for story, got: {type(result)}")

    return {
        "title": result.get("title", title or "Untitled"),
        "content": result.get("content", ""),
        "story_mode": story_mode,
        "canon_status": story_mode if story_mode in ("canon", "non_canon", "alt_timeline") else "experimental",
        "universe_id": universe_id,
        "character_ids": character_ids or [],
        "choices": result.get("choices") if story_mode == "rpg_sim" else None,
    }


def continue_story(session, story_id: int, prompt: str,
                    target_length: str = "medium") -> dict:
    """
    Continue an existing story given new direction from the user.
    Pulls the existing story's content as context and the same
    universe/character grounding if available.
    """
    story = crud.get_story(session, story_id)
    if not story:
        raise ValueError(f"Story with id {story_id} not found")

    existing_content = getattr(story, "content", "") or ""
    story_mode = getattr(story, "story_mode", "canon")
    universe_id = getattr(story, "universe_id", None)
    title = getattr(story, "title", "Untitled")

    length_words = {"short": 300, "medium": 700, "long": 1500}.get(target_length, 700)

    context_str = ""
    if universe_id:
        context_str = build_universe_context(session, universe_id) or ""

    system = (
        "You are the story-writing engine for Zen AI. Continue the existing story "
        "naturally, maintaining tone, characters, and continuity. "
        f"{_MODE_GUIDANCE.get(story_mode, '')}"
    )

    # Truncate existing content if very long, keep the tail (most relevant for continuation)
    excerpt = existing_content[-4000:] if len(existing_content) > 4000 else existing_content

    user_prompt = (
        f"## Lore Context\n{context_str}\n\n"
        f"## Story So Far (\"{title}\")\n{excerpt}\n\n"
        f"## Continuation Request\n{prompt}\n\n"
        f"## Requirements\n- Target length for new section: ~{length_words} words\n"
        "Return a JSON object with field \"content\" containing ONLY the new "
        "continuation text (do not repeat the story so far)."
    )

    client = get_client()
    result = client.ask_json(user_prompt, system=system, temperature=1.0,
                              max_tokens=max(2048, length_words * 3))

    if not isinstance(result, dict):
        raise ValueError(f"Expected JSON object for continuation, got: {type(result)}")

    new_content = result.get("content", "")

    return {
        "title": title,
        "new_content": new_content,
        "full_content": existing_content + "\n\n" + new_content,
        "story_mode": story_mode,
        "universe_id": universe_id,
    }


def list_story_modes() -> list[str]:
    return sorted(_VALID_MODES)
