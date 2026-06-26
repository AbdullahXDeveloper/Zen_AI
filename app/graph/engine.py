"""
app/graph/engine.py
Knowledge Graph Engine — builds NetworkX DiGraphs and exports rich HTML.
Uses directed edges so relationships like 'owns', 'founded', 'member_of' have direction.
"""

import os
import json
import networkx as nx
from pyvis.network import Network

from app.database.models import (
    Universe, UniverseConnection, Character, Faction, Location,
    Event, EventParticipant, Artifact, RelationshipEdge, RootEntity, RootEntityLink,
    Story, EntityLink
)

# ─────────────────────────────────────────────────────────────
# Node style config (group → color, shape, icon char)
# ─────────────────────────────────────────────────────────────
GROUP_STYLES = {
    "universe":       {"color": "#1abc9c", "shape": "diamond",       "icon": "🌐"},
    "character":      {"color": "#3498db", "shape": "dot",            "icon": "👤"},
    "character_main": {"color": "#e74c3c", "shape": "star",           "icon": "⭐"},
    "faction":        {"color": "#9b59b6", "shape": "triangle",       "icon": "⚔"},
    "location":       {"color": "#2ecc71", "shape": "square",         "icon": "📍"},
    "artifact":       {"color": "#f1c40f", "shape": "dot",            "icon": "💎"},
    "event":          {"color": "#e67e22", "shape": "triangleDown",   "icon": "📅"},
    "story":          {"color": "#8e44ad", "shape": "dot",            "icon": "📖"},
    "root_entity":    {"color": "#FFD700", "shape": "star",           "icon": "★"},
    "default":        {"color": "#607d8b", "shape": "dot",            "icon": "○"},
}

PREFIX_MAP = {
    "universe": "uni", "character": "chr", "faction": "fac",
    "location": "loc", "artifact": "art", "event": "evt",
    "story": "sto", "cosmic_node": "cnode", "root_entity": "root"
}

REVERSE_PREFIX = {v: k for k, v in PREFIX_MAP.items()}


def _node_size(importance: int | None, base: int = 12) -> int:
    """Scale node size by importance_score (0–100)."""
    score = importance or 50
    return base + int(score * 0.2)


def _add_node(G: nx.DiGraph, node_id: str, label: str, group: str,
              title: str = "", importance: int = 50, extra: dict = None):
    style = GROUP_STYLES.get(group, GROUP_STYLES["default"])
    data = {
        "label": label,
        "group": group,
        "title": title or label,
        "color": style["color"],
        "shape": style["shape"],
        "size": _node_size(importance),
    }
    if extra:
        data.update(extra)
    G.add_node(node_id, **data)


# ─────────────────────────────────────────────────────────────
# Graph builders
# ─────────────────────────────────────────────────────────────

def build_multiverse_graph(session) -> nx.DiGraph:
    """Nodes = Universes, Edges = UniverseConnections."""
    G = nx.DiGraph()

    universes = session.query(Universe).all()
    for u in universes:
        tip = f"Canon: {u.canon_status}\nImportance: {u.importance_score}"
        if u.description:
            tip += f"\n{u.description[:120]}"
        _add_node(G, f"uni_{u.id}", u.name, "universe", tip, u.importance_score or 50)

    connections = session.query(UniverseConnection).all()
    for c in connections:
        src, tgt = f"uni_{c.source_universe_id}", f"uni_{c.target_universe_id}"
        if G.has_node(src) and G.has_node(tgt):
            G.add_edge(src, tgt,
                       label=c.connection_type or "Connected",
                       title=c.description or "",
                       arrows="to")

    return G


def build_universe_graph(session, universe_id: int) -> nx.DiGraph:
    """Full entity graph inside one universe."""
    G = nx.DiGraph()

    # ── Factions ──
    factions = session.query(Faction).filter_by(universe_id=universe_id).all()
    faction_ids = [f.id for f in factions]

    for f in factions:
        tip = f"Ideology: {f.ideology or 'Unknown'}"
        _add_node(G, f"fac_{f.id}", f.name, "faction", tip, f.importance_score or 50)
        if getattr(f, "founder_id", None):
            # Edge will be added once character node exists
            pass

    # ── Characters ──
    if faction_ids:
        chars = session.query(Character).filter(
            (Character.universe_id == universe_id) |
            Character.faction_id.in_(faction_ids)
        ).all()
    else:
        chars = session.query(Character).filter_by(universe_id=universe_id).all()

    char_ids = [c.id for c in chars]
    for c in chars:
        tip = f"Species: {c.species or 'Unknown'}"
        if c.personality:
            tip += f"\n{c.personality[:100]}"
        _add_node(G, f"chr_{c.id}", c.name, "character", tip, c.importance_score or 50)

    # Character relationships
    rels = session.query(RelationshipEdge).filter(
        RelationshipEdge.character_a_id.in_(char_ids)
    ).all()
    for r in rels:
        a, b = f"chr_{r.character_a_id}", f"chr_{r.character_b_id}"
        if G.has_node(a) and G.has_node(b):
            G.add_edge(a, b, label=r.edge_type or "related", title=r.description or "", arrows="to")

    # Faction membership & founder
    for f in factions:
        if getattr(f, "founder_id", None) and G.has_node(f"chr_{f.founder_id}"):
            G.add_edge(f"chr_{f.founder_id}", f"fac_{f.id}", label="founded", title="Founder", arrows="to")
    for c in chars:
        if getattr(c, "faction_id", None) and G.has_node(f"fac_{c.faction_id}"):
            G.add_edge(f"chr_{c.id}", f"fac_{c.faction_id}", label="member_of", title="Member", arrows="to")

    # ── Artifacts ──
    art_filter = [Artifact.universe_id == universe_id]
    if faction_ids:
        art_filter.append(Artifact.faction_id.in_(faction_ids))
    artifacts = session.query(Artifact).filter(*art_filter if len(art_filter) == 1
                                               else [art_filter[0] | art_filter[1]]).all()
    for a in artifacts:
        _add_node(G, f"art_{a.id}", a.name, "artifact", a.description or "", a.importance_score or 50)
        if getattr(a, "owner_id", None) and G.has_node(f"chr_{a.owner_id}"):
            G.add_edge(f"chr_{a.owner_id}", f"art_{a.id}", label="owns", title="Owner", arrows="to")

    # ── Locations ──
    loc_filter = [Location.universe_id == universe_id]
    if faction_ids:
        loc_filter.append(Location.faction_id.in_(faction_ids))
    locations = session.query(Location).filter(*loc_filter if len(loc_filter) == 1
                                               else [loc_filter[0] | loc_filter[1]]).all()
    for loc in locations:
        tip = f"Type: {loc.type or 'Unknown'}\n{loc.description or ''}"
        _add_node(G, f"loc_{loc.id}", loc.name, "location", tip, loc.importance_score or 50)

    # ── Events ──
    evt_filter = [Event.universe_id == universe_id]
    if faction_ids:
        evt_filter.append(Event.faction_id.in_(faction_ids))
    events = session.query(Event).filter(*evt_filter if len(evt_filter) == 1
                                         else [evt_filter[0] | evt_filter[1]]).all()
    for e in events:
        tip = f"Date: {e.date_label or 'Unknown'}\nType: {e.event_type or ''}"
        _add_node(G, f"evt_{e.id}", e.name, "event", tip, e.importance_score or 50)
        _prefix_map = {'character': 'chr', 'faction': 'fac', 'location': 'loc', 'artifact': 'art'}
        for p in e.participants:
            pfx = _prefix_map.get(p.entity_type)
            if pfx:
                n_id = f"{pfx}_{p.entity_id}"
                if G.has_node(n_id):
                    G.add_edge(n_id, f"evt_{e.id}", label=p.role or "participated_in",
                               title=p.role or "", arrows="to")

    # ── Stories ──
    sto_filter = [Story.universe_id == universe_id]
    if faction_ids:
        sto_filter.append(Story.faction_id.in_(faction_ids))
    stories = session.query(Story).filter(*sto_filter if len(sto_filter) == 1
                                          else [sto_filter[0] | sto_filter[1]]).all()
    for s in stories:
        _add_node(G, f"sto_{s.id}", s.title, "story", s.summary or "", 50)

    # ── Entity Links ──
    _apply_entity_links(G, session)

    return G


def build_character_graph(session, character_id: int) -> nx.DiGraph:
    """Ego-graph centered on one character and their direct connections."""
    G = nx.DiGraph()

    char = session.get(Character, character_id)
    if not char:
        return G

    _add_node(G, f"chr_{char.id}", char.name, "character_main",
              f"Species: {char.species or 'Unknown'}\n{char.personality or ''}",
              char.importance_score or 80, {"size": 35})

    edges_a = session.query(RelationshipEdge).filter_by(character_a_id=character_id).all()
    edges_b = session.query(RelationshipEdge).filter_by(character_b_id=character_id).all()

    for r in edges_a + edges_b:
        other_id = r.character_b_id if r.character_a_id == character_id else r.character_a_id
        other = session.get(Character, other_id)
        if other and not G.has_node(f"chr_{other.id}"):
            _add_node(G, f"chr_{other.id}", other.name, "character",
                      f"Species: {other.species or 'Unknown'}", other.importance_score or 50)
        if G.has_node(f"chr_{r.character_a_id}") and G.has_node(f"chr_{r.character_b_id}"):
            G.add_edge(f"chr_{r.character_a_id}", f"chr_{r.character_b_id}",
                       label=r.edge_type or "related", title=r.description or "", arrows="to")

    # Faction
    if char.faction_id:
        fac = session.get(Faction, char.faction_id)
        if fac:
            _add_node(G, f"fac_{fac.id}", fac.name, "faction",
                      f"Ideology: {fac.ideology or ''}", fac.importance_score or 50)
            G.add_edge(f"chr_{char.id}", f"fac_{fac.id}", label="member_of", title="Member", arrows="to")

    return G


def build_root_entity_graph(session, root_entity_id: int) -> nx.DiGraph:
    """Multiversal graph for one Root Entity spanning all linked elements."""
    G = nx.DiGraph()

    root = session.get(RootEntity, root_entity_id)
    if not root:
        return G

    _add_node(G, f"root_{root.id}", root.name, "root_entity",
              f"Type: {root.type or 'Unknown'}\n{root.description or ''}",
              root.importance_score or 100, {"size": 40})

    _fetch_map = {
        'universe': (Universe, 'name'),
        'character': (Character, 'name'),
        'faction': (Faction, 'name'),
        'location': (Location, 'name'),
        'artifact': (Artifact, 'name'),
        'event': (Event, 'name'),
        'story': (Story, 'title'),
    }

    for link in root.links:
        entry = _fetch_map.get(link.entity_type)
        if not entry:
            continue
        model, name_attr = entry
        obj = session.get(model, link.entity_id)
        if not obj:
            continue
        entity_name = getattr(obj, name_attr, None) or "Unknown"
        pfx = PREFIX_MAP.get(link.entity_type, "unk")
        node_id = f"{pfx}_{link.entity_id}"
        if not G.has_node(node_id):
            _add_node(G, node_id, entity_name, link.entity_type,
                      link.description or "", getattr(obj, "importance_score", 50) or 50)
        G.add_edge(f"root_{root.id}", node_id,
                   label=link.description or "linked_to", title=link.description or "", arrows="to")

    # Also add entities with direct root_entity_id FK
    direct_map = [
        (Character, "chr", "name"), (Faction, "fac", "name"), (Location, "loc", "name"),
        (Artifact, "art", "name"), (Event, "evt", "name"), (Story, "sto", "title"),
    ]
    for model, pfx, name_attr in direct_map:
        items = session.query(model).filter_by(root_entity_id=root.id).all()
        for item in items:
            node_id = f"{pfx}_{item.id}"
            grp = REVERSE_PREFIX.get(pfx, pfx)
            if not G.has_node(node_id):
                _add_node(G, node_id, getattr(item, name_attr, "Unknown"), grp,
                          "", getattr(item, "importance_score", 50) or 50)
            if not G.has_edge(f"root_{root.id}", node_id):
                G.add_edge(f"root_{root.id}", node_id, label="linked_to",
                           title="Direct Connection", arrows="to")

    _apply_entity_links(G, session)
    return G


def _apply_entity_links(G: nx.DiGraph, session):
    """Apply cross-entity EntityLinks to any existing nodes in G."""
    all_links = session.query(EntityLink).all()
    for el in all_links:
        src_p = PREFIX_MAP.get(el.source_entity_type)
        tgt_p = PREFIX_MAP.get(el.target_entity_type)
        if not src_p or not tgt_p:
            continue
        src_id = f"{src_p}_{el.source_entity_id}"
        tgt_id = f"{tgt_p}_{el.target_entity_id}"
        if G.has_node(src_id) and G.has_node(tgt_id):
            G.add_edge(src_id, tgt_id,
                       label=el.link_name or "Linked",
                       title=el.link_name or "",
                       arrows="to")


# ─────────────────────────────────────────────────────────────
# HTML Export
# ─────────────────────────────────────────────────────────────

def _get_vis_js() -> str:
    """Return vis-network.min.js content, downloading + caching if needed."""
    cache_path = os.path.join("data", "cache", "vis-network.min.js")
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            return f.read()

    import urllib.request
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    url = "https://cdn.jsdelivr.net/npm/vis-network@9.1.2/dist/vis-network.min.js"
    try:
        urllib.request.urlretrieve(url, cache_path)
        with open(cache_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"[engine] Could not download vis.js: {e}")
        return ""


def export_graph_to_html(nx_graph: nx.DiGraph, output_path: str) -> str:
    """
    Export a NetworkX DiGraph to a self-contained interactive HTML file.
    Uses PyVis for layout, then post-processes the HTML to:
    - Embed vis.js locally (no CDN)
    - Inject dark theme
    - Inject node-click bridge (ZEN_NODE_CLICK)
    - Inject edge add/delete bridge (ZEN_BRIDGE)
    - Inject setZenEditMode()
    """
    directed = isinstance(nx_graph, nx.DiGraph)
    net = Network(
        height="100%", width="100%",
        bgcolor="#141414", font_color="#EEEEEE",
        directed=directed,
        notebook=False
    )

    import json
    options = {
        "nodes": {
            "font": {
                "size": 14,
                "color": "#FFFFFF",
                "strokeWidth": 3,
                "strokeColor": "#141414",
                "face": "Inter, Segoe UI, Arial, sans-serif"
            },
            "borderWidth": 2,
            "borderWidthSelected": 4,
            "shadow": {"enabled": True, "color": "rgba(0,0,0,0.5)", "size": 8, "x": 1, "y": 1}
        },
        "edges": {
            "font": {
                "size": 11,
                "color": "#DDDDDD",
                "strokeWidth": 4,
                "strokeColor": "#141414",
                "face": "Inter, Segoe UI, Arial, sans-serif",
                "align": "horizontal"
            },
            "color": {"color": "#666666", "highlight": "#00ADB5", "hover": "#00ADB5"},
            "width": 1.5,
            "selectionWidth": 2,
            "smooth": {"type": "continuous", "roundness": 0.5},
            "arrows": {"to": {"enabled": True, "scaleFactor": 0.6}}
        },
        "physics": {
            "forceAtlas2Based": {
                "gravity": -120,
                "centralGravity": 0.005,
                "springLength": 150,
                "springConstant": 0.04,
                "damping": 0.4,
                "avoidOverlap": 0.5
            },
            "solver": "forceAtlas2Based"
        },
        "interaction": {
            "hover": True,
            "hideEdgesOnDrag": True,
            "hideEdgesOnPan": True
        }
    }
    net.set_options(json.dumps(options))
    net.from_nx(nx_graph)
    net.save_graph(output_path)

    # ── Post-process HTML ──────────────────────────────────────────────────
    with open(output_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Embed vis.js locally
    vis_js = _get_vis_js()
    if vis_js:
        import re
        match = re.search(r'<script[^>]+src=["\']([^"\']*vis[^"\']*)["\'][^>]*></script>', html)
        if match:
            html = html.replace(match.group(0), f'<script type="text/javascript">{vis_js}</script>')

    # Fix height
    html = html.replace("height: 800px", "height: 100%")
    html = html.replace('style="height:800px', 'style="height:100%')

    # Build node metadata JSON for inspector
    node_meta = {}
    for n_id, n_data in nx_graph.nodes(data=True):
        node_meta[str(n_id)] = {
            "label": n_data.get("label", str(n_id)),
            "group": n_data.get("group", ""),
            "title": n_data.get("title", ""),
        }

    # Build serialized nodes/edges for export info
    nodes_json = json.dumps(node_meta)

    dark_css = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
  *, html, body {
    box-sizing: border-box;
    margin: 0; padding: 0;
    background-color: #141414 !important;
    font-family: 'Inter', sans-serif;
  }
  #mynetwork {
    background-color: #141414 !important;
    background-image: radial-gradient(circle at 1px 1px, rgba(255,255,255,0.03) 1px, transparent 0) !important;
    background-size: 32px 32px !important;
    width: 100% !important;
    height: 100% !important;
    position: absolute !important;
    top: 0; left: 0;
  }
  body { overflow: hidden; }

  /* Node inspector overlay */
  #zen-inspector {
    display: none;
    position: fixed;
    top: 12px; right: 12px;
    width: 260px;
    background: rgba(20, 20, 20, 0.95);
    border: 1px solid #2a2a2a;
    border-radius: 12px;
    padding: 16px;
    z-index: 9999;
    color: #EEE;
    backdrop-filter: blur(12px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.6);
  }
  #zen-inspector h3 {
    margin: 0 0 8px 0;
    font-size: 15px;
    font-weight: 700;
    color: #00ADB5;
    border-bottom: 1px solid #2a2a2a;
    padding-bottom: 8px;
  }
  #zen-inspector .zen-field { margin: 6px 0; font-size: 12px; }
  #zen-inspector .zen-label { color: #888; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
  #zen-inspector .zen-value { color: #EEE; font-size: 13px; margin-top: 2px; }
  #zen-inspector .zen-group-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 700;
    margin-top: 4px;
  }
  #zen-close-btn {
    position: absolute;
    top: 10px; right: 12px;
    background: none;
    border: none;
    color: #555;
    font-size: 18px;
    cursor: pointer;
    line-height: 1;
    padding: 0;
  }
  #zen-close-btn:hover { color: #EEE; }
</style>
"""

    inspector_html = """
<div id="zen-inspector">
  <button id="zen-close-btn" onclick="document.getElementById('zen-inspector').style.display='none'">✕</button>
  <h3 id="zen-ins-label">Node Info</h3>
  <div class="zen-field">
    <div class="zen-label">Type</div>
    <div class="zen-value"><span id="zen-ins-group" class="zen-group-badge"></span></div>
  </div>
  <div class="zen-field">
    <div class="zen-label">Details</div>
    <div class="zen-value" id="zen-ins-title" style="white-space: pre-wrap; max-height:140px; overflow-y:auto;"></div>
  </div>
  <div class="zen-field">
    <div class="zen-label">Node ID</div>
    <div class="zen-value" id="zen-ins-id" style="color:#555; font-size:11px;"></div>
  </div>
</div>
"""

    group_colors = {
        "universe": "#1abc9c", "character": "#3498db", "character_main": "#e74c3c",
        "faction": "#9b59b6", "location": "#2ecc71", "artifact": "#f1c40f",
        "event": "#e67e22", "story": "#8e44ad", "root_entity": "#FFD700", "default": "#607d8b",
    }

    zen_js = f"""
<script>
// ── ZenAI Knowledge Graph Bridge ──────────────────────────────────────────
var ZEN_NODE_META = {nodes_json};
var ZEN_GROUP_COLORS = {json.dumps(group_colors)};
var ZEN_EDIT_MODE = false;

// Wait for network to be ready
function zenInit() {{
  if (typeof network === "undefined") {{
    setTimeout(zenInit, 200);
    return;
  }}

  // Node click → inspector
  network.on("click", function(params) {{
    if (params.nodes.length > 0) {{
      var nodeId = String(params.nodes[0]);
      var meta = ZEN_NODE_META[nodeId] || {{}};
      var label = meta.label || nodeId;
      var group = meta.group || "unknown";
      var title = (meta.title || "").replace(/<[^>]+>/g, "");

      document.getElementById("zen-ins-label").innerText = label;
      document.getElementById("zen-ins-title").innerText = title || "(no details)";
      document.getElementById("zen-ins-id").innerText = nodeId;

      var badge = document.getElementById("zen-ins-group");
      badge.innerText = group.replace("_", " ").toUpperCase();
      badge.style.background = (ZEN_GROUP_COLORS[group] || "#607d8b") + "33";
      badge.style.color = ZEN_GROUP_COLORS[group] || "#607d8b";
      badge.style.border = "1px solid " + (ZEN_GROUP_COLORS[group] || "#607d8b");

      document.getElementById("zen-inspector").style.display = "block";

      // Send to Python bridge
      console.log("ZEN_NODE_CLICK:" + nodeId + ":" + label + ":" + group);
    }} else {{
      document.getElementById("zen-inspector").style.display = "none";
    }}
  }});
}}
zenInit();

// ── Edit mode ────────────────────────────────────────────────────────────
window.setZenEditMode = function(enable) {{
  ZEN_EDIT_MODE = enable;
  if (typeof network === "undefined") return;
  network.setOptions({{
    manipulation: {{
      enabled: enable,
      addNode: false,
      addEdge: function(data, callback) {{
        if (data.from === data.to) {{
          var r = confirm("Connect node to itself?");
          if (!r) return;
        }}
        var label = prompt("Connection label (optional):", "Connected");
        if (label === null) return;
        console.log("ZEN_BRIDGE:ADD_EDGE:" + data.from + ":" + data.to + ":" + label);
        data.label = label;
        data.arrows = "to";
        callback(data);
      }},
      deleteEdge: function(data, callback) {{
        var edgeId = data.edges[0];
        if (edgeId !== undefined) {{
          var edge = network.body.data.edges.get(edgeId);
          if (edge) {{
            console.log("ZEN_BRIDGE:DEL_EDGE:" + edge.from + ":" + edge.to + ":");
          }}
        }}
        callback(data);
      }},
      deleteNode: false
    }}
  }});
}};

// ── Search/highlight ─────────────────────────────────────────────────────
window.zenHighlight = function(query) {{
  if (typeof network === "undefined") return;
  var allNodes = network.body.data.nodes.get();
  var updates = [];
  query = (query || "").toLowerCase().trim();
  allNodes.forEach(function(n) {{
    var label = (n.label || "").toLowerCase();
    var match = query.length > 0 && label.includes(query);
    var dim   = query.length > 0 && !match;
    updates.push({{
      id: n.id,
      opacity: dim ? 0.15 : 1.0,
      font: {{ color: dim ? "#333" : "#EEE" }}
    }});
  }});
  network.body.data.nodes.update(updates);
}};

// ── Layout switch ────────────────────────────────────────────────────────
window.zenSetLayout = function(mode) {{
  if (typeof network === "undefined") return;
  if (mode === "hierarchical") {{
    network.setOptions({{
      layout: {{ hierarchical: {{ enabled: true, direction: "UD", sortMethod: "directed" }} }},
      physics: {{ enabled: false }}
    }});
  }} else if (mode === "circular") {{
    network.setOptions({{
      layout: {{ hierarchical: {{ enabled: false }} }},
      physics: {{ enabled: false }}
    }});
    var allNodes = network.body.data.nodes.get();
    var n = allNodes.length;
    var r = Math.max(200, n * 40);
    var updates = allNodes.map(function(node, i) {{
      var angle = (2 * Math.PI * i) / n;
      return {{ id: node.id, x: r * Math.cos(angle), y: r * Math.sin(angle), fixed: true }};
    }});
    network.body.data.nodes.update(updates);
    network.fit();
  }} else {{
    network.setOptions({{
      layout: {{ hierarchical: {{ enabled: false }} }},
      physics: {{ enabled: true }}
    }});
  }}
}};
</script>
"""

    # Inject into HTML
    html = html.replace("</head>", dark_css + "\n</head>", 1)
    html = html.replace("</body>", inspector_html + zen_js + "\n</body>", 1)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path