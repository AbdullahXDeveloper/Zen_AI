import networkx as nx
from pyvis.network import Network
from app.database.models import (
    Universe, UniverseConnection, Character, Faction, Location, 
    Event, EventParticipant, Artifact, RelationshipEdge, RootEntity, RootEntityLink,
    Story, EntityLink
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
    
    # Factions
    factions = session.query(Faction).filter_by(universe_id=universe_id).all()
    faction_ids = [f.id for f in factions] if factions else []

    # 1. Add Characters & Relationships
    if faction_ids:
        characters = session.query(Character).filter(
            (Character.universe_id == universe_id) |
            (Character.faction_id.in_(faction_ids))
        ).all()
    else:
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
    # Fetch factions recursively or just those linked to universe
    # To keep it simple, we include all factions linked to universe
    for f in factions:
        G.add_node(f"fac_{f.id}", label=f.name, group="faction", title=f.ideology)
        if getattr(f, "founder_id", None) and G.has_node(f"chr_{f.founder_id}"):
            G.add_edge(f"chr_{f.founder_id}", f"fac_{f.id}", label="founded", title="Founder")

    # Link characters to their factions
    for c in characters:
        if getattr(c, "faction_id", None) and G.has_node(f"fac_{c.faction_id}"):
            G.add_edge(f"chr_{c.id}", f"fac_{c.faction_id}", label="member_of", title="Member")

    # 3. Add Artifacts
    artifacts = session.query(Artifact).filter(
        (Artifact.universe_id == universe_id) |
        (Artifact.faction_id.in_(faction_ids) if faction_ids else False)
    ).all()
    for a in artifacts:
        G.add_node(f"art_{a.id}", label=a.name, group="artifact")
        if getattr(a, "owner_id", None) and G.has_node(f"chr_{a.owner_id}"):
            G.add_edge(f"chr_{a.owner_id}", f"art_{a.id}", label="owns", title="Owner")

    # 4. Add Locations
    locations = session.query(Location).filter(
        (Location.universe_id == universe_id) |
        (Location.faction_id.in_(faction_ids) if faction_ids else False)
    ).all()
    for loc in locations:
        G.add_node(f"loc_{loc.id}", label=loc.name, group="location", title=loc.type)

    # 5. Add Events
    events = session.query(Event).filter(
        (Event.universe_id == universe_id) |
        (Event.faction_id.in_(faction_ids) if faction_ids else False)
    ).all()
    for e in events:
        G.add_node(f"evt_{e.id}", label=e.name, group="event", title=e.date_label)
        for p in e.participants:
            prefix_map = {'character': 'chr', 'faction': 'fac', 'location': 'loc', 'artifact': 'art'}
            prefix = prefix_map.get(p.entity_type, 'unknown')
            node_id = f"{prefix}_{p.entity_id}"
            if G.has_node(node_id):
                G.add_edge(node_id, f"evt_{e.id}", label="participated_in", title=p.role)

    # 6. Add Stories
    stories = session.query(Story).filter(
        (Story.universe_id == universe_id) |
        (Story.faction_id.in_(faction_ids) if faction_ids else False)
    ).all()
    for s in stories:
        G.add_node(f"sto_{s.id}", label=s.title, group="story", title=s.story_mode)

    # 7. Add Universal Links (EntityLinks)
    all_links = session.query(EntityLink).all()
    prefix_map = {
        "universe": "uni", "character": "chr", "faction": "fac",
        "location": "loc", "artifact": "art", "event": "evt",
        "story": "sto", "cosmic_node": "cnode", "root_entity": "root"
    }
    for el in all_links:
        src_p = prefix_map.get(el.source_entity_type)
        tgt_p = prefix_map.get(el.target_entity_type)
        if src_p and tgt_p:
            src_id = f"{src_p}_{el.source_entity_id}"
            tgt_id = f"{tgt_p}_{el.target_entity_id}"
            if G.has_node(src_id) and G.has_node(tgt_id):
                G.add_edge(src_id, tgt_id, label=el.link_name or "Linked", title=el.link_name)

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
            'event': 'evt', 'universe': 'uni', 'artifact': 'art', 'story': 'sto'
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
            elif link.entity_type == 'story':
                obj = session.query(Story).get(link.entity_id)
                entity_name = obj.title if obj else None
        except Exception:
            entity_name = None
        
        # Skip stale links pointing to entities that no longer exist
        if entity_name is None:
            continue
            
        if not G.has_node(node_id):
            G.add_node(node_id, label=entity_name, group=link.entity_type)
            
        G.add_edge(f"root_{root.id}", node_id, label="linked_to", title=link.description or "")

    # Also add entities linked directly via root_entity_id
    for model, prefix in [
        (Character, "chr"), (Faction, "fac"), (Location, "loc"),
        (Artifact, "art"), (Event, "evt"), (Story, "sto")
    ]:
        direct_items = session.query(model).filter_by(root_entity_id=root.id).all()
        for item in direct_items:
            node_id = f"{prefix}_{item.id}"
            if not G.has_node(node_id):
                G.add_node(node_id, label=getattr(item, "name", getattr(item, "title", "Unknown")), group=prefix.replace('chr', 'character').replace('fac', 'faction').replace('loc', 'location').replace('art', 'artifact').replace('evt', 'event').replace('sto', 'story'))
            G.add_edge(f"root_{root.id}", node_id, label="linked_to", title="Direct Connection")

    # Add Universal Links (EntityLinks)
    all_links = session.query(EntityLink).all()
    prefix_map = {
        "universe": "uni", "character": "chr", "faction": "fac",
        "location": "loc", "artifact": "art", "event": "evt",
        "story": "sto", "cosmic_node": "cnode", "root_entity": "root"
    }
    for el in all_links:
        src_p = prefix_map.get(el.source_entity_type)
        tgt_p = prefix_map.get(el.target_entity_type)
        if src_p and tgt_p:
            src_id = f"{src_p}_{el.source_entity_id}"
            tgt_id = f"{tgt_p}_{el.target_entity_id}"
            if G.has_node(src_id) and G.has_node(tgt_id):
                G.add_edge(src_id, tgt_id, label=el.link_name or "Linked", title=el.link_name)

    return G


def export_graph_to_html(nx_graph, output_path):
    """Converts a NetworkX graph to a PyVis interactive HTML file."""
    net = Network(height='800px', width='100%', bgcolor='#1E1E1E', font_color='white', directed=False)
    
    # Configure Physics / Layout for more spaced-out nodes
    net.force_atlas_2based(spring_length=250, overlap=0.5, damping=0.09)
    
    # We will inject manipulation via string replacement in the final HTML
    # so we don't set manipulation options directly on the net object here.

    # Optional: Customize colors based on groups
    group_colors = {
        "character": "#3498db", "character_main": "#e74c3c", 
        "faction": "#9b59b6", "event": "#e67e22", 
        "artifact": "#f1c40f", "location": "#2ecc71", 
        "universe": "#1abc9c", "root_entity": "#FFD700",
        "story": "#8e44ad"
    }
    
    for node in nx_graph.nodes(data=True):
        node_data = node[1]
        group = node_data.get('group', 'default')
        if group in group_colors:
            node_data['color'] = group_colors[group]
            
    net.from_nx(nx_graph)
    net.show_buttons(filter_=['physics'])    
    # Export initial HTML
    net.save_graph(output_path)
    
    # Inject QWebChannel and manipulation script
    with open(output_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    js_injection = """
    <script>
      function configureManipulation(network) {
          network.setOptions({
              manipulation: {
                  enabled: true,
                  addNode: false, // Adding nodes visually is disabled
                  addEdge: function(data, callback) {
                      if (data.from === data.to) {
                          var r = confirm("Do you want to connect the node to itself?");
                          if (!r) return;
                      }
                      var label = prompt("Enter connection label (optional):", "Connected");
                      if (label === null) return; // Cancelled
                      
                      console.log("ZEN_BRIDGE:ADD_EDGE:" + data.from + ":" + data.to + ":" + label);
                      
                      data.label = label;
                      callback(data);
                  },
                  deleteEdge: function(data, callback) {
                      var edgeId = data.edges[0];
                      var edge = network.body.data.edges.get(edgeId);
                      if (edge) {
                          console.log("ZEN_BRIDGE:DEL_EDGE:" + edge.from + ":" + edge.to + ":");
                      }
                      callback(data);
                  },
                  deleteNode: false // Deleting nodes visually is disabled
              }
          });
      }
      
      // Hook into the draw event to ensure the network is initialized
      setTimeout(function() {
          if (typeof network !== "undefined") {
              configureManipulation(network);
          }
      }, 500);
    </script>
    """
    
    html_content = html_content.replace("</body>", js_injection + "\n</body>")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return output_path