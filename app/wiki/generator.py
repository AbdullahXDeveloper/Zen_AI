import os
from app.database.models import (
    Universe, Character, Faction, Location, Event, Artifact, RootEntity
)

# Wiki pages save karne ka default rasta
WIKI_DIR = os.path.join("data", "lore", "wiki")

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def _get_entity(session, entity_type, entity_id):
    """Database se correct table fetch karta hai based on entity_type."""
    model_map = {
        "universe": Universe,
        "character": Character,
        "faction": Faction,
        "location": Location,
        "event": Event,
        "artifact": Artifact,
        "root_entity": RootEntity
    }
    model = model_map.get(entity_type.lower())
    if not model:
        return None
    return session.query(model).get(entity_id)

def generate_wiki_page(session, entity_type, entity_id, output_dir=WIKI_DIR):
    """Kisi bhi entity ka ek detailed Markdown wiki page generate karta hai."""
    entity = _get_entity(session, entity_type, entity_id)
    if not entity:
        raise ValueError(f"{entity_type} with ID {entity_id} not found.")

    # Specific folders for each type (e.g., data/lore/wiki/character/)
    type_dir = os.path.join(output_dir, entity_type.lower())
    ensure_dir(type_dir)

    md_content = []
    
    # --- HEADER ---
    md_content.append(f"# {entity.name}")
    md_content.append(f"**Entity Type:** {entity_type.capitalize()} | **ID:** `{entity.uuid}`")
    
    if hasattr(entity, "canon_status"):
        md_content.append(f"**Canon Status:** {entity.canon_status.capitalize()}")
    if hasattr(entity, "importance_score"):
        md_content.append(f"**Importance Score:** {entity.importance_score}/100")
        
    md_content.append("\n---\n")

    # --- DESCRIPTION ---
    if hasattr(entity, "description") and entity.description:
        md_content.append("## Description")
        md_content.append(entity.description)
        md_content.append("\n")

    # --- CHARACTER SPECIFIC ---
    if entity_type == "character":
        md_content.append("## Profile")
        if entity.species: md_content.append(f"- **Species:** {entity.species}")
        if entity.titles: md_content.append(f"- **Titles:** {entity.titles}")
        if entity.personality: md_content.append(f"- **Personality:** {entity.personality}")
        if entity.motivations: md_content.append(f"- **Motivations:** {entity.motivations}")
        
        # Character Relationships
        if entity.relationships_a or entity.relationships_b:
            md_content.append("\n## Relationships")
            for r in entity.relationships_a:
                md_content.append(f"- **{r.character_b.name}** ({r.edge_type}): {r.description}")
            for r in entity.relationships_b:
                md_content.append(f"- **{r.character_a.name}** ({r.edge_type}): {r.description}")

    # --- UNIVERSE SPECIFIC ---
    elif entity_type == "universe":
        if entity.characters:
            md_content.append("## Notable Characters")
            for c in sorted(entity.characters, key=lambda x: x.importance_score, reverse=True)[:10]:
                md_content.append(f"- [[{c.name}]]")

    # --- EVENT SPECIFIC ---
    elif entity_type == "event":
        md_content.append("## Event Details")
        if entity.date_label: md_content.append(f"- **Date:** {entity.date_label}")
        if entity.event_type: md_content.append(f"- **Type:** {entity.event_type.capitalize()}")
        
        if entity.participants:
            md_content.append("\n## Participants")
            for p in entity.participants:
                # Basic representation, ideally you'd fetch the actual entity name here
                md_content.append(f"- {p.entity_type.capitalize()} ID `{p.entity_id}` as **{p.role}**")

    # File save karna
    safe_name = "".join([c for c in entity.name if c.isalpha() or c.isdigit() or c==' ']).rstrip().replace(" ", "_").lower()
    file_path = os.path.join(type_dir, f"{safe_name}.md")
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_content))
        
    return file_path

def generate_all_wikis(session):
    """Database mein majood har entity ka wiki page generate karta hai."""
    entities_generated = 0
    
    for uni in session.query(Universe).all():
        generate_wiki_page(session, "universe", uni.id)
        entities_generated += 1
        
    for char in session.query(Character).all():
        generate_wiki_page(session, "character", char.id)
        entities_generated += 1
        
    for loc in session.query(Location).all():
        generate_wiki_page(session, "location", loc.id)
        entities_generated += 1
        
    for evt in session.query(Event).all():
        generate_wiki_page(session, "event", evt.id)
        entities_generated += 1
        
    return entities_generated