"""
app/graph/builder.py
====================
Module 3 — Knowledge Graph Builder
Builds NetworkX graphs from DB data. 4 graph types supported:
  1. universe_graph(session, universe_id)     → all entities inside one universe
  2. character_graph(session, character_id)   → one character + all connections
  3. multiverse_graph(session)                → universes as nodes, connections as edges
  4. root_entity_graph(session, root_id)      → root entity + all root_entity_links

Edge types (from spec): friend, enemy, family, mentor, student,
                        created, destroyed, owns, located_in, participated_in

Node attributes stored:
  - label, entity_type, uuid, importance_score, canon_status
Edge attributes stored:
  - edge_type, label, universe_id (where relevant)
"""

import networkx as nx
from sqlalchemy.orm import Session

from app.database.models import (
    Character, Faction, Location, Event, Artifact,
    Relationship, EventParticipant,
    Universe, UniverseConnection,
    RootEntity, RootEntityLink,
)


# ─────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────

def _char_node_id(char_id: int) -> str:
    return f"chr_{char_id}"

def _fac_node_id(fid: int) -> str:
    return f"fac_{fid}"

def _loc_node_id(lid: int) -> str:
    return f"loc_{lid}"

def _evt_node_id(eid: int) -> str:
    return f"evt_{eid}"

def _art_node_id(aid: int) -> str:
    return f"art_{aid}"

def _uni_node_id(uid: int) -> str:
    return f"uni_{uid}"

def _root_node_id(rid: int) -> str:
    return f"root_{rid}"


def _add_character_node(G: nx.Graph, char: Character):
    G.add_node(
        _char_node_id(char.id),
        label=char.name,
        entity_type="character",
        uuid=char.uuid or "",
        importance_score=char.importance_score or 50,
        canon_status=char.canon_status or "canon",
        subtitle=char.title or "",
    )


def _add_faction_node(G: nx.Graph, fac: Faction):
    G.add_node(
        _fac_node_id(fac.id),
        label=fac.name,
        entity_type="faction",
        uuid=fac.uuid or "",
        importance_score=fac.importance_score or 50,
        canon_status=fac.canon_status or "canon",
        subtitle=fac.faction_type or "",
    )


def _add_location_node(G: nx.Graph, loc: Location):
    G.add_node(
        _loc_node_id(loc.id),
        label=loc.name,
        entity_type="location",
        uuid=loc.uuid or "",
        importance_score=loc.importance_score or 50,
        canon_status=loc.canon_status or "canon",
        subtitle=loc.location_type or "",
    )


def _add_event_node(G: nx.Graph, evt: Event):
    G.add_node(
        _evt_node_id(evt.id),
        label=evt.name,
        entity_type="event",
        uuid=evt.uuid or "",
        importance_score=evt.importance_score or 50,
        canon_status=evt.canon_status or "canon",
        subtitle=evt.event_type or "",
    )


def _add_artifact_node(G: nx.Graph, art: Artifact):
    G.add_node(
        _art_node_id(art.id),
        label=art.name,
        entity_type="artifact",
        uuid=art.uuid or "",
        importance_score=art.importance_score or 50,
        canon_status=art.canon_status or "canon",
        subtitle=art.artifact_type or "",
    )


# ─────────────────────────────────────────────
# 1. Universe Graph
# ─────────────────────────────────────────────

def universe_graph(session: Session, universe_id: int) -> nx.Graph:
    """
    Build a graph of ALL entities that belong to a given universe.
    Nodes: characters, factions, locations, events, artifacts in that universe.
    Edges: relationships + event_participants + location memberships.
    Returns a NetworkX undirected Graph.
    """
    G = nx.Graph(graph_type="universe", universe_id=universe_id)

    # --- Nodes ---
    characters = session.query(Character).filter_by(universe_id=universe_id).all()
    factions   = session.query(Faction).filter_by(universe_id=universe_id).all()
    locations  = session.query(Location).filter_by(universe_id=universe_id).all()
    events     = session.query(Event).filter_by(universe_id=universe_id).all()
    artifacts  = session.query(Artifact).filter_by(universe_id=universe_id).all()

    for c in characters:  _add_character_node(G, c)
    for f in factions:    _add_faction_node(G, f)
    for l in locations:   _add_location_node(G, l)
    for e in events:      _add_event_node(G, e)
    for a in artifacts:   _add_artifact_node(G, a)

    char_ids = {c.id for c in characters}
    evt_ids  = {e.id for e in events}

    # --- Edges: character ↔ character relationships ---
    rels = (
        session.query(Relationship)
        .filter(
            Relationship.entity_a_type == "character",
            Relationship.entity_b_type == "character",
        )
        .all()
    )
    for r in rels:
        if r.entity_a_id in char_ids and r.entity_b_id in char_ids:
            G.add_edge(
                _char_node_id(r.entity_a_id),
                _char_node_id(r.entity_b_id),
                edge_type=r.relationship_type or "related",
                label=r.relationship_type or "",
                rel_id=r.id,
            )

    # --- Edges: event participants ---
    for ep in session.query(EventParticipant).all():
        if ep.event_id in evt_ids and ep.character_id in char_ids:
            G.add_edge(
                _evt_node_id(ep.event_id),
                _char_node_id(ep.character_id),
                edge_type="participated_in",
                label=ep.role or "participated_in",
            )

    # --- Edges: character → faction (via faction_id on character) ---
    for c in characters:
        if c.faction_id:
            fac_nid = _fac_node_id(c.faction_id)
            if fac_nid in G:
                G.add_edge(
                    _char_node_id(c.id),
                    fac_nid,
                    edge_type="member_of",
                    label="member_of",
                )

    # --- Edges: character → home location ---
    for c in characters:
        if hasattr(c, "home_location_id") and c.home_location_id:
            loc_nid = _loc_node_id(c.home_location_id)
            if loc_nid in G:
                G.add_edge(
                    _char_node_id(c.id),
                    loc_nid,
                    edge_type="located_in",
                    label="located_in",
                )

    # --- Edges: artifact → owner character ---
    for a in artifacts:
        if a.owner_character_id:
            char_nid = _char_node_id(a.owner_character_id)
            if char_nid in G:
                G.add_edge(
                    char_nid,
                    _art_node_id(a.id),
                    edge_type="owns",
                    label="owns",
                )

    return G


# ─────────────────────────────────────────────
# 2. Character Graph
# ─────────────────────────────────────────────

def character_graph(session: Session, character_id: int) -> nx.Graph:
    """
    Build a graph centered on one character.
    Includes: all relationships, faction, events participated in,
              owned artifacts, home location, variants (alt versions).
    Returns a NetworkX graph (directed, to show who connects to whom).
    """
    G = nx.DiGraph(graph_type="character", center_id=character_id)

    char = session.query(Character).get(character_id)
    if not char:
        return G

    _add_character_node(G, char)
    center_nid = _char_node_id(character_id)

    # --- Relationships (both directions) ---
    rels = (
        session.query(Relationship)
        .filter(
            (
                (Relationship.entity_a_type == "character") &
                (Relationship.entity_a_id == character_id)
            ) |
            (
                (Relationship.entity_b_type == "character") &
                (Relationship.entity_b_id == character_id)
            )
        )
        .all()
    )

    for r in rels:
        if r.entity_a_type == "character" and r.entity_a_id == character_id:
            other = session.query(Character).get(r.entity_b_id)
            if other:
                _add_character_node(G, other)
                G.add_edge(
                    center_nid, _char_node_id(other.id),
                    edge_type=r.relationship_type or "related",
                    label=r.relationship_type or "",
                )
        else:
            other = session.query(Character).get(r.entity_a_id)
            if other:
                _add_character_node(G, other)
                G.add_edge(
                    _char_node_id(other.id), center_nid,
                    edge_type=r.relationship_type or "related",
                    label=r.relationship_type or "",
                )

    # --- Faction ---
    if char.faction_id:
        fac = session.query(Faction).get(char.faction_id)
        if fac:
            _add_faction_node(G, fac)
            G.add_edge(center_nid, _fac_node_id(fac.id), edge_type="member_of", label="member_of")

    # --- Events ---
    eps = session.query(EventParticipant).filter_by(character_id=character_id).all()
    for ep in eps:
        evt = session.query(Event).get(ep.event_id)
        if evt:
            _add_event_node(G, evt)
            G.add_edge(
                center_nid, _evt_node_id(evt.id),
                edge_type="participated_in",
                label=ep.role or "participated_in",
            )

    # --- Artifacts owned ---
    arts = session.query(Artifact).filter_by(owner_character_id=character_id).all()
    for a in arts:
        _add_artifact_node(G, a)
        G.add_edge(center_nid, _art_node_id(a.id), edge_type="owns", label="owns")

    # --- Home location ---
    if hasattr(char, "home_location_id") and char.home_location_id:
        loc = session.query(Location).get(char.home_location_id)
        if loc:
            _add_location_node(G, loc)
            G.add_edge(center_nid, _loc_node_id(loc.id), edge_type="located_in", label="located_in")

    # --- Variants (alt-universe versions of same character) ---
    if char.parent_character_id:
        parent = session.query(Character).get(char.parent_character_id)
        if parent:
            _add_character_node(G, parent)
            G.add_edge(center_nid, _char_node_id(parent.id), edge_type="variant_of", label="variant_of")
    else:
        variants = session.query(Character).filter_by(parent_character_id=character_id).all()
        for v in variants:
            _add_character_node(G, v)
            G.add_edge(_char_node_id(v.id), center_nid, edge_type="variant_of", label="variant_of")

    return G


# ─────────────────────────────────────────────
# 3. Multiverse Graph
# ─────────────────────────────────────────────

def multiverse_graph(session: Session) -> nx.Graph:
    """
    High-level graph: each Universe is a node, UniverseConnections are edges.
    Node size = number of characters in that universe (pulled live).
    Returns undirected Graph.
    """
    G = nx.Graph(graph_type="multiverse")

    universes = session.query(Universe).all()
    for u in universes:
        char_count = session.query(Character).filter_by(universe_id=u.id).count()
        G.add_node(
            _uni_node_id(u.id),
            label=u.name,
            entity_type="universe",
            uuid=u.uuid or "",
            importance_score=u.importance_score or 50,
            canon_status=u.canon_status or "canon",
            subtitle=u.universe_type or "",
            char_count=char_count,
        )

    connections = session.query(UniverseConnection).all()
    for conn in connections:
        u1 = _uni_node_id(conn.universe_a_id)
        u2 = _uni_node_id(conn.universe_b_id)
        if u1 in G and u2 in G:
            G.add_edge(
                u1, u2,
                edge_type=conn.connection_type or "linked",
                label=conn.connection_type or "",
                conn_id=conn.id,
            )

    return G


# ─────────────────────────────────────────────
# 4. Root Entity Graph
# ─────────────────────────────────────────────

def root_entity_graph(session: Session, root_entity_id: int) -> nx.Graph:
    """
    Graph centered on one Root Entity (e.g. OM_X, K, _LA, Zendrix Tree).
    Edges come from root_entity_links — which connect root entities to
    characters/factions/locations/events/artifacts across any universe.
    Returns directed Graph (root → linked entity).
    """
    G = nx.DiGraph(graph_type="root_entity", center_id=root_entity_id)

    root = session.query(RootEntity).get(root_entity_id)
    if not root:
        return G

    root_nid = _root_node_id(root_entity_id)
    G.add_node(
        root_nid,
        label=root.name,
        entity_type="root_entity",
        uuid=root.uuid or "",
        importance_score=root.importance_score or 100,
        canon_status="canon",
        subtitle="Root Entity",
    )

    links = session.query(RootEntityLink).filter_by(root_entity_id=root_entity_id).all()

    entity_loaders = {
        "character": (Character, _add_character_node, _char_node_id),
        "faction":   (Faction,   _add_faction_node,   _fac_node_id),
        "location":  (Location,  _add_location_node,  _loc_node_id),
        "event":     (Event,     _add_event_node,     _evt_node_id),
        "artifact":  (Artifact,  _add_artifact_node,  _art_node_id),
    }

    for link in links:
        etype = link.linked_entity_type
        if etype not in entity_loaders:
            continue
        model_class, add_fn, nid_fn = entity_loaders[etype]
        entity = session.query(model_class).get(link.linked_entity_id)
        if not entity:
            continue
        add_fn(G, entity)
        G.add_edge(
            root_nid, nid_fn(entity.id),
            edge_type=link.link_type or "connected",
            label=link.link_type or "",
            universe_id=link.universe_id,
        )

    return G


# ─────────────────────────────────────────────
# Public dispatcher
# ─────────────────────────────────────────────

def build_graph(
    session: Session,
    graph_type: str,
    entity_id: int = None,
) -> nx.Graph:
    """
    Unified entry point.
    graph_type ∈ {"universe", "character", "multiverse", "root_entity"}
    entity_id required for universe / character / root_entity.
    """
    if graph_type == "universe":
        if entity_id is None:
            raise ValueError("entity_id required for universe graph")
        return universe_graph(session, entity_id)

    elif graph_type == "character":
        if entity_id is None:
            raise ValueError("entity_id required for character graph")
        return character_graph(session, entity_id)

    elif graph_type == "multiverse":
        return multiverse_graph(session)

    elif graph_type == "root_entity":
        if entity_id is None:
            raise ValueError("entity_id required for root_entity graph")
        return root_entity_graph(session, entity_id)

    else:
        raise ValueError(
            f"Unknown graph_type '{graph_type}'. "
            "Choose: universe | character | multiverse | root_entity"
        )
