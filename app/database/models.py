"""
ZenAI - SQLAlchemy Models
The Living Archive of Zendrix
"""

import uuid as uuid_lib
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, ForeignKey, DateTime, JSON
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def gen_uuid(prefix: str):
    """Generate a prefixed UUID string, e.g. chr_8f4a1b2c..."""
    def _gen():
        return f"{prefix}_{uuid_lib.uuid4().hex}"
    return _gen


# ============================================================
# UNIVERSES
# ============================================================

class Universe(Base):
    __tablename__ = "universes"

    id = Column(Integer, primary_key=True)
    uuid = Column(String(50), unique=True, nullable=False, default=gen_uuid("uni"))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    canon_status = Column(String(50), default="canon")  # canon/non_canon/alt_timeline/experimental
    importance_score = Column(Integer, default=50)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    characters = relationship("Character", back_populates="universe", cascade="all, delete-orphan")
    factions = relationship("Faction", back_populates="universe", cascade="all, delete-orphan")
    locations = relationship("Location", back_populates="universe", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="universe", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="universe", cascade="all, delete-orphan")
    stories = relationship("Story", back_populates="universe", cascade="all, delete-orphan")
    simulation_runs = relationship("SimulationRun", back_populates="universe", cascade="all, delete-orphan")
    cosmic_nodes = relationship("CosmicNode", back_populates="universe", cascade="all, delete-orphan")


# ============================================================
# COSMIC NODES (hierarchical tree inside each universe)
# ============================================================

NODE_TYPES = ["black_hole", "galaxy", "solar_system", "planet", "star", "nebula", "custom"]

NODE_ICONS = {
    "black_hole":   "🕳️",
    "galaxy":       "🌌",
    "solar_system": "☀️",
    "planet":       "🪐",
    "star":         "⭐",
    "nebula":       "🌫️",
    "custom":       "📦",
}


class CosmicNode(Base):
    __tablename__ = "cosmic_nodes"

    id = Column(Integer, primary_key=True)
    uuid = Column(String(50), unique=True, nullable=False, default=gen_uuid("csm"))
    universe_id = Column(Integer, ForeignKey("universes.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("cosmic_nodes.id"), nullable=True)
    name = Column(String(255), nullable=False)
    node_type = Column(String(50), default="custom")  # black_hole/galaxy/solar_system/planet/star/nebula/custom
    description = Column(Text)
    importance_score = Column(Integer, default=50)
    created_at = Column(DateTime, default=datetime.utcnow)

    universe = relationship("Universe", back_populates="cosmic_nodes")
    children = relationship(
        "CosmicNode",
        foreign_keys="CosmicNode.parent_id",
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    parent = relationship(
        "CosmicNode",
        foreign_keys="CosmicNode.parent_id",
        back_populates="children",
        remote_side="CosmicNode.id",
        uselist=False,
    )


class UniverseConnection(Base):
    __tablename__ = "universes_connections"

    id = Column(Integer, primary_key=True)
    source_universe_id = Column(Integer, ForeignKey("universes.id"), nullable=False)
    target_universe_id = Column(Integer, ForeignKey("universes.id"), nullable=False)
    connection_type = Column(String(100))  # e.g. "Connected Through War"
    description = Column(Text)

    source_universe = relationship("Universe", foreign_keys=[source_universe_id])
    target_universe = relationship("Universe", foreign_keys=[target_universe_id])


# ============================================================
# ROOT ENTITIES (multiversal unique entities: OM_X, K, _LA, etc.)
# ============================================================

class RootEntity(Base):
    __tablename__ = "root_entities"

    id = Column(Integer, primary_key=True)
    uuid = Column(String(50), unique=True, nullable=False, default=gen_uuid("root"))
    name = Column(String(255), nullable=False)
    type = Column(String(100))
    description = Column(Text)
    notes = Column(Text)
    importance_score = Column(Integer, default=100)

    links = relationship("RootEntityLink", back_populates="root_entity", cascade="all, delete-orphan")


class RootEntityLink(Base):
    __tablename__ = "root_entity_links"

    id = Column(Integer, primary_key=True)
    root_entity_id = Column(Integer, ForeignKey("root_entities.id"), nullable=False)
    entity_type = Column(String(50), nullable=False)  # 'character','faction','location','event','universe','artifact'
    entity_id = Column(Integer, nullable=False)
    description = Column(Text)

    root_entity = relationship("RootEntity", back_populates="links")


# ============================================================
# CHARACTERS
# ============================================================

class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True)
    uuid = Column(String(50), unique=True, nullable=False, default=gen_uuid("chr"))
    universe_id = Column(Integer, ForeignKey("universes.id"), nullable=False)
    name = Column(String(255), nullable=False)
    titles = Column(Text)
    aliases = Column(Text)
    species = Column(String(255))
    traits_json = Column(JSON, default=dict)  # e.g. {"Strategic": 92, "Ruthless": 80}
    personality = Column(Text)
    motivations = Column(Text)
    goals = Column(Text)
    ideology = Column(Text)
    canon_status = Column(String(50), default="canon")
    importance_score = Column(Integer, default=50)
    version = Column(Integer, default=1)
    parent_character_id = Column(Integer, ForeignKey("characters.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    universe = relationship("Universe", back_populates="characters")
    variants = relationship(
        "Character",
        foreign_keys=[parent_character_id],
        back_populates="parent",
        uselist=True,
    )
    parent = relationship(
        "Character",
        foreign_keys=[parent_character_id],
        back_populates="variants",
        remote_side="Character.id",
        uselist=False,
    )
    powers = relationship("CharacterPower", back_populates="character", cascade="all, delete-orphan")

    relationships_a = relationship(
        "RelationshipEdge",
        foreign_keys="RelationshipEdge.character_a_id",
        back_populates="character_a",
        cascade="all, delete-orphan"
    )
    relationships_b = relationship(
        "RelationshipEdge",
        foreign_keys="RelationshipEdge.character_b_id",
        back_populates="character_b",
        cascade="all, delete-orphan"
    )


# ============================================================
# FACTIONS
# ============================================================

class Faction(Base):
    __tablename__ = "factions"

    id = Column(Integer, primary_key=True)
    uuid = Column(String(50), unique=True, nullable=False, default=gen_uuid("fac"))
    universe_id = Column(Integer, ForeignKey("universes.id"), nullable=False)
    name = Column(String(255), nullable=False)
    founder_id = Column(Integer, ForeignKey("characters.id"), nullable=True)
    ideology = Column(Text)
    description = Column(Text)
    canon_status = Column(String(50), default="canon")
    importance_score = Column(Integer, default=50)

    universe = relationship("Universe", back_populates="factions")
    founder = relationship("Character", foreign_keys=[founder_id])


# ============================================================
# LOCATIONS
# ============================================================

class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True)
    uuid = Column(String(50), unique=True, nullable=False, default=gen_uuid("loc"))
    universe_id = Column(Integer, ForeignKey("universes.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(String(100))
    canon_status = Column(String(50), default="canon")
    importance_score = Column(Integer, default=50)

    universe = relationship("Universe", back_populates="locations")


# ============================================================
# POWERS
# ============================================================

class Power(Base):
    __tablename__ = "powers"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    rules = Column(Text)
    scope = Column(String(50), default="local")  # 'universal' / 'local'

    character_links = relationship("CharacterPower", back_populates="power", cascade="all, delete-orphan")


class CharacterPower(Base):
    __tablename__ = "character_powers"

    character_id = Column(Integer, ForeignKey("characters.id"), primary_key=True)
    power_id = Column(Integer, ForeignKey("powers.id"), primary_key=True)
    proficiency = Column(Integer, default=50)  # 0-100

    character = relationship("Character", back_populates="powers")
    power = relationship("Power", back_populates="character_links")


# ============================================================
# EVENTS
# ============================================================

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    uuid = Column(String(50), unique=True, nullable=False, default=gen_uuid("evt"))
    universe_id = Column(Integer, ForeignKey("universes.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    date_value = Column(String(100))  # sortable string/number representation
    date_label = Column(String(255))  # human-readable, e.g. "Era of Fire, Year 302"
    event_type = Column(String(50))  # birth/death/rebirth/war/other
    canon_status = Column(String(50), default="canon")
    importance_score = Column(Integer, default=50)

    universe = relationship("Universe", back_populates="events")
    participants = relationship("EventParticipant", back_populates="event", cascade="all, delete-orphan")


class EventParticipant(Base):
    __tablename__ = "event_participants"

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    entity_type = Column(String(50), nullable=False)  # 'character','faction','location', etc.
    entity_id = Column(Integer, nullable=False)
    role = Column(String(100))  # e.g. "attacker", "victim", "witness"

    event = relationship("Event", back_populates="participants")


# ============================================================
# RELATIONSHIPS (character-to-character graph edges)
# ============================================================

class RelationshipEdge(Base):
    __tablename__ = "relationships"

    id = Column(Integer, primary_key=True)
    character_a_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    character_b_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    edge_type = Column(String(50), nullable=False)
    # friend, enemy, family, mentor, student, created, destroyed, owns, located_in, participated_in
    description = Column(Text)

    character_a = relationship("Character", foreign_keys=[character_a_id], back_populates="relationships_a")
    character_b = relationship("Character", foreign_keys=[character_b_id], back_populates="relationships_b")


# ============================================================
# ARTIFACTS
# ============================================================

class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(Integer, primary_key=True)
    uuid = Column(String(50), unique=True, nullable=False, default=gen_uuid("art"))
    universe_id = Column(Integer, ForeignKey("universes.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    owner_id = Column(Integer, ForeignKey("characters.id"), nullable=True)
    powers_json = Column(JSON, default=list)
    importance_score = Column(Integer, default=50)

    universe = relationship("Universe", back_populates="artifacts")
    owner = relationship("Character", foreign_keys=[owner_id])


# ============================================================
# STORIES
# ============================================================

class Story(Base):
    __tablename__ = "stories"

    id = Column(Integer, primary_key=True)
    uuid = Column(String(50), unique=True, nullable=False, default=gen_uuid("sty"))
    title = Column(String(255), nullable=False)
    summary = Column(Text)
    raw_text = Column(Text)
    story_mode = Column(String(50), default="canon")
    # canon / non_canon / what_if / alt_timeline / rpg_sim
    canon_status = Column(String(50), default="canon")
    universe_id = Column(Integer, ForeignKey("universes.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    universe = relationship("Universe", back_populates="stories")


# ============================================================
# SIMULATION RUNS (World Simulation Engine)
# ============================================================

class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    premise = Column(Text, nullable=False)
    affected_entities_json = Column(JSON, default=list)
    generated_outcomes_json = Column(JSON, default=list)
    reasoning_text = Column(Text)
    universe_id = Column(Integer, ForeignKey("universes.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    universe = relationship("Universe", back_populates="simulation_runs")


# ============================================================
# LORE DOCUMENTS (ingestion)
# ============================================================

class LoreDocument(Base):
    __tablename__ = "lore_documents"

    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    raw_text = Column(Text)
    processed = Column(Boolean, default=False)
    upload_date = Column(DateTime, default=datetime.utcnow)


# ============================================================
# VERSION HISTORY
# ============================================================

class VersionHistory(Base):
    __tablename__ = "version_history"

    id = Column(Integer, primary_key=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    version_number = Column(Integer, nullable=False)
    data_snapshot_json = Column(JSON, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    approved_by = Column(String(100), default="user")


# ============================================================
# TAGS
# ============================================================

class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)

    entity_links = relationship("EntityTag", back_populates="tag", cascade="all, delete-orphan")


class EntityTag(Base):
    __tablename__ = "entity_tags"

    id = Column(Integer, primary_key=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    tag_id = Column(Integer, ForeignKey("tags.id"), nullable=False)

    tag = relationship("Tag", back_populates="entity_links")


# ============================================================
# ENTITY NOTES (creator's private notes)
# ============================================================

class EntityNote(Base):
    __tablename__ = "entity_notes"

    id = Column(Integer, primary_key=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    note_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# ENTITY LINKS (cross-entity links, with custom name)
# ============================================================

class EntityLink(Base):
    """
    Links any entity (character, faction, location, event, artifact, story, cosmic_node)
    to any other entity, with a user-defined link name/label.
    """
    __tablename__ = "entity_links"

    id = Column(Integer, primary_key=True)
    # The entity being linked FROM
    source_entity_type = Column(String(50), nullable=False)
    source_entity_id = Column(Integer, nullable=False)
    # The entity being linked TO
    target_entity_type = Column(String(50), nullable=False)
    target_entity_id = Column(Integer, nullable=False)
    
    link_name = Column(String(255))  # User-defined label, e.g. "Origin Story", "Home Planet"
    created_at = Column(DateTime, default=datetime.utcnow)

