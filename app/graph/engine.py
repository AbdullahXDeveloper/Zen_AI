import networkx as nx
from pyvis.network import Network
from app.database.models import (
    Universe, UniverseConnection, Character, Faction, Location, 
    Event, EventParticipant, Artifact, RelationshipEdge, RootEntity, RootEntityLink
)

def build_multiverse_graph(session):
    """Generates a graph where nodes are Universes and edges are their connections."""
    G = nx.Graph()
    
    universes = session.query(Universe).all()
    for u in universes:
        G.add_node(f"uni_{u.id}", label=u.name, group="universe", title=f"Canon: {u.canon_status}\nScore: {u.importance_score}")
        
    connections = session.query(UniverseConnection).all()
    for c in connections:
        G.add_edge(f"uni_{c.source_universe_id}", f"uni_{c.target_universe_id}", label=c.connection_type, title=c.description)
        
    return G

def build_universe_graph(session, universe_id):
    """Generates a graph of all entities and relationships within a single universe."""
    G = nx.Graph()
    
    # 1. Add Characters & Relationships
    characters = session.query(Character).filter_by(universe_id=universe_id).all()
    char_ids = [c.id for c in characters]
    for c in characters:
        G.add_node(f"chr_{c.id}", label=c.name, group="character", title=c.species)
        
    relationships = session.query(RelationshipEdge).filter(
        RelationshipEdge.character_a_id.in_(char_ids)
    ).all()
    for r in relationships:
        if G.has_node(f"chr_{r.character_a_id}") and G.has_node(f"chr_{r.character_b_id}"):
            G.add_edge(f"chr_{r.character_a_id}", f"chr_{r.character_b_id}", label=r.edge_type, title=r.description)

    # 2. Add Factions
    factions = session.query(Faction).filter_by(universe_id=universe_id).all()
    for f in factions:
        G.add_node(f"fac_{f.id}", label=f.name, group="faction", title=f.ideology)
        if f.founder_id and G.has_node(f"chr_{f.founder_id}"):
            G.add_edge(f"chr_{f.founder_id}", f"fac_{f.id}", label="founded", title="Founder")

    # 3. Add Artifacts
    artifacts = session.query(Artifact).filter_by(universe_id=universe_id).all()
    for a in artifacts:
        G.add_node(f"art_{a.id}", label=a.name, group="artifact")
        if a.owner_id and G.has_node(f"chr_{a.owner_id}"):
            G.add_edge(f"chr_{a.owner_id}", f"art_{a.id}", label="owns", title="Owner")

    # 4. Add Locations (Yeh block Events se UPAR aana chahiye)
    locations = session.query(Location).filter_by(universe_id=universe_id).all()
    for loc in locations:
        G.add_node(f"loc_{loc.id}", label=loc.name, group="location", title=loc.type)

    # 5. Add Events (Ab jab Event add hoga, toh Locations graph mein majood hongi)
    events = session.query(Event).filter_by(universe_id=universe_id).all()
    for e in events:
        G.add_node(f"evt_{e.id}", label=e.name, group="event", title=e.date_label)
        for p in e.participants:
            # Map entity_type to prefix (e.g., character -> chr)
            prefix_map = {'character': 'chr', 'faction': 'fac', 'location': 'loc', 'artifact': 'art'}
            prefix = prefix_map.get(p.entity_type, 'unknown')
            node_id = f"{prefix}_{p.entity_id}"
            
            if G.has_node(node_id):
                G.add_edge(node_id, f"evt_{e.id}", label="participated_in", title=p.role)

    return G


def build_character_graph(session, character_id):
    """Generates a graph centered on a specific character and their direct connections."""
    G = nx.Graph()
    
    char = session.query(Character).get(character_id)
    if not char:
        return G
        
    G.add_node(f"chr_{char.id}", label=char.name, group="character_main", size=30)
    
    # Get relationships where this character is A or B
    edges_a = session.query(RelationshipEdge).filter_by(character_a_id=character_id).all()
    edges_b = session.query(RelationshipEdge).filter_by(character_b_id=character_id).all()
    
    for r in edges_a + edges_b:
        other_id = r.character_b_id if r.character_a_id == character_id else r.character_a_id
        other_char = session.query(Character).get(other_id)
        
        if other_char and not G.has_node(f"chr_{other_char.id}"):
            G.add_node(f"chr_{other_char.id}", label=other_char.name, group="character")
            
        G.add_edge(f"chr_{r.character_a_id}", f"chr_{r.character_b_id}", label=r.edge_type, title=r.description)
        
    return G


def build_root_entity_graph(session, root_entity_id):
    """Generates a graph for a Root Entity spanning across all linked multiversal elements.
    
    Fetches real entity names and skips stale links (deleted entities).
    """
    G = nx.Graph()
    
    root = session.query(RootEntity).get(root_entity_id)
    if not root:
        return G
        
    G.add_node(f"root_{root.id}", label=root.name, group="root_entity", size=40, color="#FFD700")
    
    for link in root.links:
        prefix_map = {
            'character': 'chr', 'faction': 'fac', 'location': 'loc',
            'event': 'evt', 'universe': 'uni', 'artifact': 'art'
        }
        prefix = prefix_map.get(link.entity_type, 'unknown')
        node_id = f"{prefix}_{link.entity_id}"
        
        # Fetch actual entity name and verify it still exists in DB
        entity_name = None
        try:
            if link.entity_type == 'universe':
                obj = session.query(Universe).get(link.entity_id)
                entity_name = obj.name if obj else None
            elif link.entity_type == 'character':
                obj = session.query(Character).get(link.entity_id)
                entity_name = obj.name if obj else None
            elif link.entity_type == 'faction':
                obj = session.query(Faction).get(link.entity_id)
                entity_name = obj.name if obj else None
            elif link.entity_type == 'location':
                obj = session.query(Location).get(link.entity_id)
                entity_name = obj.name if obj else None
            elif link.entity_type == 'artifact':
                obj = session.query(Artifact).get(link.entity_id)
                entity_name = obj.name if obj else None
            elif link.entity_type == 'event':
                obj = session.query(Event).get(link.entity_id)
                entity_name = obj.name if obj else None
        except Exception:
            entity_name = None
        
        # Skip stale links pointing to entities that no longer exist
        if entity_name is None:
            continue
            
        if not G.has_node(node_id):
            G.add_node(node_id, label=entity_name, group=link.entity_type)
            
        G.add_edge(f"root_{root.id}", node_id, label="linked_to", title=link.description or "")

    return G


def export_graph_to_html(nx_graph, output_path):
    """Converts a NetworkX graph to a PyVis interactive HTML file."""
    net = Network(height='800px', width='100%', bgcolor='#1E1E1E', font_color='white', directed=False)
    
    # Configure Physics / Layout
    net.force_atlas_2based()
    
    # Optional: Customize colors based on groups
    group_colors = {
        "character": "#3498db", "character_main": "#e74c3c", 
        "faction": "#9b59b6", "event": "#e67e22", 
        "artifact": "#f1c40f", "location": "#2ecc71", 
        "universe": "#1abc9c", "root_entity": "#FFD700"
    }
    
    for node in nx_graph.nodes(data=True):
        node_data = node[1]
        group = node_data.get('group', 'default')
        if group in group_colors:
            node_data['color'] = group_colors[group]
            
    net.from_nx(nx_graph)
    net.show_buttons(filter_=['physics'])
    net.save_graph(output_path)
    return output_path