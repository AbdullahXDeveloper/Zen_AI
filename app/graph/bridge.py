import json
from PySide6.QtCore import QObject, Slot
from app.database.db_init import get_session
from app.database.models import (
    RelationshipEdge, UniverseConnection, EventParticipant,
    RootEntityLink, Faction, Character, Location, Artifact
)

class GraphBridge(QObject):
    """
    QWebChannel Bridge to handle graph manipulation callbacks from Javascript.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    @Slot(str, str, str)
    def add_edge(self, from_id: str, to_id: str, label: str):
        """
        Called when the user drags a line between two nodes.
        Node IDs are prefixed, e.g., 'chr_1', 'fac_2', 'uni_3'.
        """
        print(f"[GraphBridge] add_edge called: {from_id} -> {to_id} (label: {label})")
        session = get_session()
        try:
            # Parse prefixes
            if "_" not in from_id or "_" not in to_id:
                return
            
            f_parts = from_id.split("_")
            t_parts = to_id.split("_")
            
            f_prefix, f_val = f_parts[0], int(f_parts[1])
            t_prefix, t_val = t_parts[0], int(t_parts[1])

            # 1. Character -> Character (RelationshipEdge)
            if f_prefix == "chr" and t_prefix == "chr":
                edge = RelationshipEdge(
                    character_a_id=f_val,
                    character_b_id=t_val,
                    edge_type=label or "Connected",
                    description="Added visually via Knowledge Graph"
                )
                session.add(edge)
            
            # 2. Universe -> Universe (UniverseConnection)
            elif f_prefix == "uni" and t_prefix == "uni":
                conn = UniverseConnection(
                    source_universe_id=f_val,
                    target_universe_id=t_val,
                    connection_type=label or "Connected",
                    description="Added visually via Knowledge Graph"
                )
                session.add(conn)

            # 3. Entity -> Event (EventParticipant)
            elif t_prefix == "evt":
                # Ensure we only map valid entities to events
                map_prefix = {'chr': 'character', 'fac': 'faction', 'loc': 'location', 'art': 'artifact'}
                if f_prefix in map_prefix:
                    ep = EventParticipant(
                        event_id=t_val,
                        entity_type=map_prefix[f_prefix],
                        entity_id=f_val,
                        role=label or "Participant"
                    )
                    session.add(ep)

            # 4. Entity -> Root Entity (RootEntityLink)
            elif t_prefix == "root" or f_prefix == "root":
                root_id = t_val if t_prefix == "root" else f_val
                other_prefix = f_prefix if t_prefix == "root" else t_prefix
                other_id = f_val if t_prefix == "root" else t_val
                
                map_prefix = {'chr': 'character', 'fac': 'faction', 'loc': 'location', 'art': 'artifact', 'uni': 'universe', 'evt': 'event'}
                if other_prefix in map_prefix:
                    link = RootEntityLink(
                        root_entity_id=root_id,
                        entity_type=map_prefix[other_prefix],
                        entity_id=other_id,
                        description=label or "Linked"
                    )
                    session.add(link)

            # 5. Entity -> Faction (Set faction_id)
            elif t_prefix == "fac":
                if f_prefix == "chr":
                    c = session.query(Character).get(f_val)
                    if c: c.faction_id = t_val
                elif f_prefix == "fac":
                    f = session.query(Faction).get(f_val)
                    if f: f.faction_id = t_val
                elif f_prefix == "loc":
                    l = session.query(Location).get(f_val)
                    if l: l.faction_id = t_val
                elif f_prefix == "art":
                    a = session.query(Artifact).get(f_val)
                    if a: a.faction_id = t_val

            session.commit()
            print("[GraphBridge] Edge successfully inserted into database.")
        except Exception as e:
            session.rollback()
            print(f"[GraphBridge] Error adding edge: {e}")
        finally:
            session.close()

    @Slot(str)
    def delete_edge(self, edge_id: str):
        """
        Called when the user selects an edge and deletes it.
        Vis.js generates a UUID for edges by default if not provided.
        Since we don't pass DB edge IDs to PyVis easily right now, deleting might be tricky 
        if we only get the Vis.js edge ID.
        We will rely on 'from' and 'to' instead.
        """
        pass
    
    @Slot(str, str)
    def delete_edge_by_nodes(self, from_id: str, to_id: str):
        print(f"[GraphBridge] delete_edge_by_nodes called: {from_id} -> {to_id}")
        session = get_session()
        try:
            if "_" not in from_id or "_" not in to_id:
                return
            
            f_parts = from_id.split("_")
            t_parts = to_id.split("_")
            f_prefix, f_val = f_parts[0], int(f_parts[1])
            t_prefix, t_val = t_parts[0], int(t_parts[1])

            if f_prefix == "chr" and t_prefix == "chr":
                # Delete RelationshipEdge
                session.query(RelationshipEdge).filter(
                    ((RelationshipEdge.character_a_id == f_val) & (RelationshipEdge.character_b_id == t_val)) |
                    ((RelationshipEdge.character_a_id == t_val) & (RelationshipEdge.character_b_id == f_val))
                ).delete()

            elif f_prefix == "uni" and t_prefix == "uni":
                session.query(UniverseConnection).filter(
                    ((UniverseConnection.source_universe_id == f_val) & (UniverseConnection.target_universe_id == t_val)) |
                    ((UniverseConnection.source_universe_id == t_val) & (UniverseConnection.target_universe_id == f_val))
                ).delete()

            elif t_prefix == "evt":
                map_prefix = {'chr': 'character', 'fac': 'faction', 'loc': 'location', 'art': 'artifact'}
                if f_prefix in map_prefix:
                    session.query(EventParticipant).filter_by(
                        event_id=t_val, entity_type=map_prefix[f_prefix], entity_id=f_val
                    ).delete()

            elif t_prefix == "root" or f_prefix == "root":
                root_id = t_val if t_prefix == "root" else f_val
                other_prefix = f_prefix if t_prefix == "root" else t_prefix
                other_id = f_val if t_prefix == "root" else t_val
                map_prefix = {'chr': 'character', 'fac': 'faction', 'loc': 'location', 'art': 'artifact', 'uni': 'universe', 'evt': 'event'}
                if other_prefix in map_prefix:
                    session.query(RootEntityLink).filter_by(
                        root_entity_id=root_id, entity_type=map_prefix[other_prefix], entity_id=other_id
                    ).delete()

            elif t_prefix == "fac":
                if f_prefix == "chr":
                    c = session.query(Character).get(f_val)
                    if c and c.faction_id == t_val: c.faction_id = None
                elif f_prefix == "fac":
                    f = session.query(Faction).get(f_val)
                    if f and f.faction_id == t_val: f.faction_id = None
                elif f_prefix == "loc":
                    l = session.query(Location).get(f_val)
                    if l and l.faction_id == t_val: l.faction_id = None
                elif f_prefix == "art":
                    a = session.query(Artifact).get(f_val)
                    if a and a.faction_id == t_val: a.faction_id = None

            session.commit()
            print("[GraphBridge] Edge successfully deleted from database.")
        except Exception as e:
            session.rollback()
            print(f"[GraphBridge] Error deleting edge: {e}")
        finally:
            session.close()

