"""
ZenAI — CRUD Package
Import everything from here for convenience.

Usage:
    from app.database.crud import create_character, list_universes, ...
"""

# Base utilities
from app.database.crud._base import (
    save_version,
    get_version_history,
    rollback_to_version,
)

# Universes
from app.database.crud.universes import (
    create_universe,
    get_universe,
    get_universe_by_uuid,
    list_universes,
    update_universe,
    delete_universe,
    create_universe_connection,
    list_universe_connections,
    delete_universe_connection,
)

# Characters
from app.database.crud.characters import (
    create_character,
    get_character,
    get_character_by_uuid,
    list_characters,
    list_character_variants,
    update_character,
    delete_character,
    add_power_to_character,
    remove_power_from_character,
    list_character_powers,
)

# Factions
from app.database.crud.factions import (
    create_faction,
    get_faction,
    get_faction_by_uuid,
    list_factions,
    update_faction,
    delete_faction,
)

# Locations
from app.database.crud.locations import (
    create_location,
    get_location,
    get_location_by_uuid,
    list_locations,
    update_location,
    delete_location,
)

# Events
from app.database.crud.events import (
    create_event,
    get_event,
    get_event_by_uuid,
    list_events,
    update_event,
    delete_event,
    add_event_participant,
    list_event_participants,
    list_entity_events,
    remove_event_participant,
)

# Artifacts
from app.database.crud.artifacts import (
    create_artifact,
    get_artifact,
    get_artifact_by_uuid,
    list_artifacts,
    update_artifact,
    delete_artifact,
)

# Powers
from app.database.crud.powers import (
    create_power,
    get_power,
    list_powers,
    update_power,
    delete_power,
)

# Root Entities
from app.database.crud.root_entities import (
    create_root_entity,
    get_root_entity,
    get_root_entity_by_name,
    get_root_entity_by_uuid,
    list_root_entities,
    update_root_entity,
    delete_root_entity,
    create_root_entity_link,
    list_root_entity_links,
    delete_root_entity_link,
)

# Relationships
from app.database.crud.relationships import (
    create_relationship,
    get_relationship,
    list_relationships,
    list_relationships_between,
    update_relationship,
    delete_relationship,
)

# Stories & Simulations
from app.database.crud.stories import (
    create_story,
    get_story,
    get_story_by_uuid,
    list_stories,
    update_story,
    delete_story,
    create_simulation_run,
    get_simulation_run,
    list_simulation_runs,
    update_simulation_run,
    delete_simulation_run,
)

# Tags, Notes, Lore Docs
from app.database.crud.tags_notes import (
    get_or_create_tag,
    list_tags,
    delete_tag,
    tag_entity,
    list_entity_tags,
    untag_entity,
    find_entities_by_tag,
    add_entity_note,
    list_entity_notes,
    delete_entity_note,
    create_lore_document,
    get_lore_document,
    list_lore_documents,
    mark_lore_document_processed,
    delete_lore_document,
)

# CSV I/O (re-exported here for convenience)
from app.database.csv_io import (
    export_csv,
    import_csv,
    export_all_tables,
)

# Cosmic Nodes (universe hierarchy tree)
from app.database.crud.cosmic_nodes import (
    create_cosmic_node,
    get_cosmic_node,
    list_cosmic_nodes_by_universe,
    list_root_cosmic_nodes,
    list_cosmic_node_children,
    update_cosmic_node,
    delete_cosmic_node,
)

# Story Links (cross-entity story connections)
from app.database.crud.story_links import (
    create_story_link,
    get_story_link,
    list_story_links,
    delete_story_link,
    list_all_stories_enriched,
)

