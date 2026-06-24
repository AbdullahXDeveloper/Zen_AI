"""
app/ui/cosmic_view.py
Zen AI — Module 9: Cosmic Zendrix Tree View
A radial tree visualization of the entire Zendrix multiverse.
- Root at center: OM_X (root entities)
- First ring: Universes
- Second ring: Characters / Factions / Locations
- Third ring: Artifacts / Events / Stories
Rendered as self-contained HTML (vis-network + inline data) in QWebEngineView.
No CDN required — vis.js served from local cache (data/cache/).
"""

import os
import json
import tempfile
import urllib.request

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QComboBox, QSizePolicy
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt, QUrl, QThread, Signal

from app.database.db_init import get_session
from app.database import crud
from app.database.models import (
    Universe, RootEntity, Character, Faction,
    Location, Artifact, Event, Story, RootEntityLink, CosmicNode
)

ACCENT     = "#00ADB5"
VIS_CDN    = "https://cdn.jsdelivr.net/npm/vis-network@9.1.2/dist/vis-network.min.js"
VIS_CACHE  = os.path.join("data", "cache", "vis-network.min.js")

# ── Color palette per entity type ────────────────────────
COLORS = {
    "root":      "#FFD700",
    "universe":  "#00ADB5",
    "character": "#9b59b6",
    "faction":   "#f39c12",
    "location":  "#2ecc71",
    "artifact":  "#00BCD4",
    "event":     "#e74c3c",
    "story":     "#8e44ad",
    "cosmic_node": "#FF5722",
}
SHAPES = {
    "root":      "star",
    "universe":  "hexagon",
    "character": "dot",
    "faction":   "triangle",
    "location":  "diamond",
    "artifact":  "square",
    "event":     "ellipse",
    "story":     "database",
    "cosmic_node": "dot",
}


# ─── Worker ─────────────────────────────────────────────
class CosmicDataWorker(QThread):
    done  = Signal(dict)
    error = Signal(str)

    def __init__(self, universe_filter: int = None):
        super().__init__()
        self.universe_filter = universe_filter

    def run(self):
        try:
            session = get_session()
            nodes = []
            edges = []

            # ── Root entities ──────────────────────────
            roots = session.query(RootEntity).all()
            if roots:
                # Invisible center node
                nodes.append({
                    "id": "center", "label": "ZENDRIX",
                    "group": "root", "size": 48,
                    "font": {"size": 16, "bold": True, "color": "#FFD700"},
                    "color": {"background": "#1A1400", "border": "#FFD700", "highlight": {"background": "#2A2000", "border": "#FFE44D"}},
                    "shape": "star",
                    "title": "Zendrix Prime — The Cosmic Root"
                })
                for r in roots:
                    nid = f"root_{r.id}"
                    nodes.append({
                        "id": nid,
                        "label": r.name,
                        "group": "root",
                        "size": 36,
                        "shape": SHAPES["root"],
                        "color": {"background": "#1A1400", "border": COLORS["root"], "highlight": {"background": "#2A2000", "border": "#FFE44D"}},
                        "font": {"color": COLORS["root"], "size": 13, "bold": True},
                        "title": f"Root Entity: {r.name}"
                    })
                    edges.append({"from": "center", "to": nid, "color": {"color": "#FFD70044", "highlight": "#FFD700"}, "width": 2, "dashes": True})

            # ── Universes ─────────────────────────────
            unis = session.query(Universe).all()
            if self.universe_filter:
                unis = [u for u in unis if u.id == self.universe_filter]

            links = session.query(RootEntityLink).filter_by(entity_type="universe").all()
            link_map = {link.entity_id: link.root_entity_id for link in links}

            for u in unis:
                nid = f"uni_{u.id}"
                c_color = {"canon": "#00ADB5", "non_canon": "#E74C3C", "alt_timeline": "#F39C12", "experimental": "#9B59B6"}.get(u.canon_status, COLORS["universe"])
                nodes.append({
                    "id": nid,
                    "label": u.name,
                    "group": "universe",
                    "size": 28,
                    "shape": SHAPES["universe"],
                    "color": {"background": "#001A1B", "border": c_color, "highlight": {"background": "#002B2D", "border": "#FFFFFF"}},
                    "font": {"color": c_color, "size": 12, "bold": True},
                    "title": f"Universe: {u.name}\nCanon: {u.canon_status}\nScore: {u.importance_score}"
                })
                # Connect to nearest root entity or center
                linked_root_id = link_map.get(u.id)
                parent_node = f"root_{linked_root_id}" if linked_root_id else "center"

                edges.append({
                    "from": parent_node, "to": nid,
                    "color": {"color": COLORS["universe"] + "BB", "highlight": COLORS["universe"]},
                    "width": 2.5
                })

                uid = u.id

                # ── Cosmic Nodes (Internal hierarchy) ────────
                c_nodes = session.query(CosmicNode).filter_by(universe_id=uid).all()
                for cn in c_nodes:
                    cnnid = f"cnode_{cn.id}"
                    nodes.append({
                        "id": cnnid, "label": cn.name, "group": "cosmic_node",
                        "size": 20, "shape": SHAPES["cosmic_node"],
                        "color": {"background": "#4D2400", "border": COLORS["cosmic_node"], "highlight": {"background": "#331A00", "border": "#FF8A65"}},
                        "font": {"color": COLORS["cosmic_node"] + "aa", "size": 11},
                        "title": f"Cosmic Node: {cn.name}\nType: {cn.node_type}\nUniverse: {u.name}"
                    })
                    
                    c_parent = f"cnode_{cn.parent_id}" if cn.parent_id else nid
                    edges.append({
                        "from": c_parent, "to": cnnid,
                        "color": {"color": COLORS["cosmic_node"] + "AA", "highlight": COLORS["cosmic_node"] + "88"},
                        "width": 2.0
                    })

            def get_parent_info(item):
                pid = "center"
                pname = "Zendrix Prime"
                if getattr(item, "universe_id", None):
                    pid = f"uni_{item.universe_id}"
                    pname = item.universe.name if hasattr(item, "universe") and item.universe else "Universe"
                elif getattr(item, "faction_id", None):
                    pid = f"fac_{item.faction_id}"
                    pname = item.faction.name if hasattr(item, "faction") and item.faction else "Faction"
                elif getattr(item, "root_entity_id", None):
                    pid = f"root_{item.root_entity_id}"
                    pname = item.root_entity.name if hasattr(item, "root_entity") and item.root_entity else "Root Entity"
                return pid, pname

            # Note: We must process Factions first since they can act as parents.
            # Then Characters, Locations, etc.
            
            def process_entities(entities, prefix, group_name, shape, base_color, font_color, title_func, size, edge_width):
                valid_parents = {n["id"] for n in nodes}
                valid_parents.add("center")
                
                unprocessed = list(entities)
                added_in_pass = True
                
                while added_in_pass and unprocessed:
                    added_in_pass = False
                    # iterate over a copy so we can remove from original list
                    for item in list(unprocessed):
                        nid = f"{prefix}_{item.id}"
                        pid, pname = get_parent_info(item)
                        if pid in valid_parents:
                            nodes.append({
                                "id": nid, "label": item.name if hasattr(item, "name") else item.title, "group": group_name,
                                "size": size, "shape": shape,
                                "color": base_color,
                                "font": {"color": font_color, "size": max(9, size-5)},
                                "title": title_func(item, pname)
                            })
                            edges.append({
                                "from": pid, "to": nid,
                                "color": {"color": COLORS[group_name] + "99", "highlight": COLORS[group_name] + "88"},
                                "width": edge_width
                            })
                            valid_parents.add(nid)
                            unprocessed.remove(item)
                            added_in_pass = True

            # ── Factions ──────────────────────────
            facs = session.query(Faction).all()
            process_entities(
                facs, "fac", "faction", SHAPES["faction"],
                {"background": "#402400", "border": COLORS["faction"], "highlight": {"background": "#2A1800", "border": "#FFCA6A"}},
                "#f39c12",
                lambda f, p: f"Faction: {f.name}\nConnected To: {p}",
                16, 1.8
            )

            # ── Locations ─────────────────────────
            locs = session.query(Location).all()
            process_entities(
                locs, "loc", "location", SHAPES["location"],
                {"background": "#004011", "border": COLORS["location"], "highlight": {"background": "#00280A", "border": "#5EFF8F"}},
                "#2ecc71",
                lambda loc, p: f"Location: {loc.name}\nType: {loc.type or '—'}\nConnected To: {p}",
                14, 2.5
            )

            # ── Artifacts ─────────────────────────
            arts = session.query(Artifact).all()
            process_entities(
                arts, "art", "artifact", SHAPES["artifact"],
                {"background": "#00333E", "border": COLORS["artifact"], "highlight": {"background": "#001E24", "border": "#80FFFF"}},
                "#00BCD4",
                lambda a, p: f"Artifact: {a.name}\nConnected To: {p}",
                12, 1.2
            )

            # ── Events ────────────────────────────
            evts = session.query(Event).all()
            process_entities(
                evts, "evt", "event", SHAPES["event"],
                {"background": "#400000", "border": COLORS["event"], "highlight": {"background": "#2A0000", "border": "#FF7A7A"}},
                "#e74c3c",
                lambda e, p: f"Event: {e.name}\nDate: {e.date_label or '—'}\nConnected To: {p}",
                12, 1.2
            )

            # ── Characters ────────────────────────
            chars = session.query(Character).all()
            process_entities(
                chars, "chr", "character", SHAPES["character"],
                {"background": "#2A0033", "border": COLORS["character"], "highlight": {"background": "#1A0020", "border": "#C77DFF"}},
                "#9b59b6",
                lambda c, p: f"Character: {c.name}\nSpecies: {c.species or '—'}\nConnected To: {p}",
                16, 1.8
            )

            # ── Stories ───────────────────────────
            stories = session.query(Story).all()
            process_entities(
                stories, "sto", "story", SHAPES["story"],
                {"background": "#29004D", "border": COLORS["story"], "highlight": {"background": "#1A0030", "border": "#C77DFF"}},
                "#8e44ad",
                lambda s, p: f"Story: {s.title}\nMode: {s.story_mode or '—'}\nConnected To: {p}",
                12, 1.2
            )
            # ── Universal Links (EntityLinks) ────────────
            from app.database.models import EntityLink
            all_links = session.query(EntityLink).all()
            prefix_map = {
                "universe": "uni", "character": "chr", "faction": "fac",
                "location": "loc", "artifact": "art", "event": "evt",
                "story": "sto", "cosmic_node": "cnode", "root_entity": "root"
            }
            valid_node_ids = set([n["id"] for n in nodes])
            valid_node_ids.add("center")

            for el in all_links:
                src_p = prefix_map.get(el.source_entity_type)
                tgt_p = prefix_map.get(el.target_entity_type)
                if not src_p or not tgt_p: continue
                
                src_id = f"{src_p}_{el.source_entity_id}"
                tgt_id = f"{tgt_p}_{el.target_entity_id}"
                
                if src_id in valid_node_ids and tgt_id in valid_node_ids:
                    edges.append({
                        "from": src_id, "to": tgt_id,
                        "label": el.link_name or "Linked",
                        "color": {"color": "#00ADB544", "highlight": "#00E5FF"},
                        "width": 1.2,
                        "dashes": True,
                        "font": {"color": "#00ADB5", "size": 9, "background": "rgba(0,0,0,0.5)"}
                    })

            session.close()
            self.done.emit({"nodes": nodes, "edges": edges})
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if 'session' in locals() and session: session.close()


# ─── HTML Generator ──────────────────────────────────────
def _build_cosmic_html(vis_js: str, data: dict) -> str:
    nodes_json = json.dumps(data["nodes"], ensure_ascii=False, indent=2)
    edges_json = json.dumps(data["edges"], ensure_ascii=False, indent=2)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Zen AI — Cosmic Zendrix View</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html, body {{
    width: 100%; height: 100%;
    background: #050505;
    overflow: hidden;
    font-family: 'Segoe UI', sans-serif;
  }}
  #cosmos {{
    width: 100%;
    height: 100vh;
  }}
  /* HUD overlay */
  #hud {{
    position: fixed; top: 14px; right: 14px;
    display: flex; flex-direction: column; gap: 6px;
    z-index: 100;
  }}
  .hud-btn {{
    background: #111; border: 1px solid #222;
    color: #555; padding: 6px 14px;
    border-radius: 6px; cursor: pointer;
    font-size: 11px; font-weight: 600;
    transition: all .2s;
  }}
  .hud-btn:hover {{ background: #1A1A1A; border-color: #00ADB5; color: #00ADB5; }}
  /* Legend */
  #legend {{
    position: fixed; bottom: 20px; left: 20px;
    background: #08080Aee; border: 1px solid #141414;
    border-radius: 10px; padding: 14px 18px;
    z-index: 100;
  }}
  #legend h4 {{ color: #222; font-size: 9px; letter-spacing: 2px; margin-bottom: 8px; }}
  .leg-row {{
    display: flex; align-items: center; gap: 8px;
    margin-bottom: 4px;
  }}
  .leg-dot {{ width: 10px; height: 10px; border-radius: 2px; flex-shrink: 0; }}
  .leg-label {{ color: #333; font-size: 10px; }}
  /* Tooltip override */
  div.vis-tooltip {{
    background: #0D0D0D !important; border: 1px solid #222 !important;
    color: #888 !important; border-radius: 6px !important;
    font-size: 11px !important; padding: 8px 12px !important;
    max-width: 260px !important; white-space: pre-line !important;
  }}
  /* Node info panel */
  #info-panel {{
    position: fixed; top: 14px; left: 14px;
    background: #08080Aee; border: 1px solid #1A1A1A;
    border-radius: 10px; padding: 16px 20px;
    min-width: 220px; max-width: 300px;
    z-index: 100; display: none;
  }}
  #info-title {{ color: #EEE; font-size: 14px; font-weight: 700; margin-bottom: 6px; }}
  #info-body  {{ color: #444; font-size: 11px; line-height: 1.6; white-space: pre-line; }}
  #info-close {{
    position: absolute; top: 8px; right: 12px;
    color: #333; cursor: pointer; font-size: 14px;
  }}
  #info-close:hover {{ color: #EEE; }}
</style>
</head>
<body>

<div id="cosmos"></div>

<!-- HUD Buttons -->
<div id="hud">
  <button class="hud-btn" onclick="resetView()">⟳  Reset View</button>
  <button class="hud-btn" onclick="togglePhysics()">⚡  Physics</button>
  <button class="hud-btn" onclick="fitAll()">⊞  Fit All</button>
</div>

<!-- Legend -->
<div id="legend">
  <h4>ENTITY TYPES</h4>
  {''.join(f'<div class="leg-row"><div class="leg-dot" style="background:{color}"></div><span class="leg-label">{name.title()}</span></div>' for name, color in COLORS.items())}
</div>

<!-- Node info panel -->
<div id="info-panel">
  <div id="info-close" onclick="closeInfo()">✕</div>
  <div id="info-title">Node</div>
  <div id="info-body"></div>
</div>

<script type="text/javascript">
{vis_js}
</script>
<script>
var NODES = {nodes_json};
var EDGES = {edges_json};

var container = document.getElementById('cosmos');

var nodesDS = new vis.DataSet(NODES);
var edgesDS = new vis.DataSet(EDGES);

var options = {{
  nodes: {{
    borderWidth: 1.5,
    shadow: {{ enabled: true, size: 12, color: 'rgba(0,0,0,0.8)' }},
    scaling: {{ min: 8, max: 50 }},
    font: {{ face: 'Segoe UI' }}
  }},
  edges: {{
    smooth: {{ type: 'continuous', roundness: 0.3 }},
    selectionWidth: 2,
    hoverWidth: 1.5,
    arrows: {{ to: {{ enabled: false }} }}
  }},
  physics: {{
    enabled: true,
    solver: 'forceAtlas2Based',
    forceAtlas2Based: {{
      gravitationalConstant: -120,
      centralGravity: 0.015,
      springLength: 90,
      springConstant: 0.08,
      damping: 0.4,
      avoidOverlap: 0.8
    }},
    stabilization: {{
      enabled: true,
      iterations: 800,
      updateInterval: 50,
      fit: true
    }}
  }},
  interaction: {{
    hover: true,
    tooltipDelay: 200,
    hideEdgesOnDrag: true,
    navigationButtons: false,
    keyboard: {{ enabled: true, bindToWindow: false }}
  }},
  layout: {{
    improvedLayout: false
  }}
}};

var network = new vis.Network(container, {{ nodes: nodesDS, edges: edgesDS }}, options);
var physicsOn = true;

// Click handler — show info panel
network.on('click', function(params) {{
  if (params.nodes.length > 0) {{
    var nid  = params.nodes[0];
    var node = nodesDS.get(nid);
    document.getElementById('info-title').textContent = node.label || nid;
    document.getElementById('info-body').textContent  = (node.title || '').replace(/<br>/g, '\\n');
    document.getElementById('info-panel').style.display = 'block';
  }} else {{
    closeInfo();
  }}
}});

// Double-click — focus + zoom
network.on('doubleClick', function(params) {{
  if (params.nodes.length > 0) {{
    network.focus(params.nodes[0], {{
      scale: 1.8,
      animation: {{ duration: 600, easingFunction: 'easeInOutQuad' }}
    }});
  }}
}});

// Stabilize callback — dim the center node pulse
network.on('stabilizationIterationsDone', function() {{
  network.setOptions({{ physics: {{ stabilization: {{ enabled: false }} }} }});
}});

function resetView() {{
  network.fit({{ animation: {{ duration: 800, easingFunction: 'easeInOutQuad' }} }});
}}
function fitAll() {{
  network.fit({{ animation: true }});
}}
function togglePhysics() {{
  physicsOn = !physicsOn;
  network.setOptions({{ physics: {{ enabled: physicsOn }} }});
}}
function closeInfo() {{
  document.getElementById('info-panel').style.display = 'none';
}}
</script>
</body>
</html>
"""


# ─── Main Cosmic View Widget ─────────────────────────────
class CosmicViewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._worker       = None
        self._last_tmp     = None
        self._vis_js_cache = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.setStyleSheet("background: #050505;")

        # ── Top bar ──
        top_bar = QFrame()
        top_bar.setFixedHeight(60)
        top_bar.setStyleSheet("background: #0A0A0A; border-bottom: 1px solid #111;")
        bar_lay = QHBoxLayout(top_bar)
        bar_lay.setContentsMargins(24, 0, 24, 0)
        bar_lay.setSpacing(16)

        title = QLabel("⬡  Cosmic Zendrix View")
        title.setStyleSheet(f"color: {ACCENT}; font-size: 18px; font-weight: 900; letter-spacing: 2px; background: transparent; border: none;")

        self._uni_combo = QComboBox()
        self._uni_combo.setFixedWidth(220)
        self._uni_combo.setStyleSheet(f"""
            QComboBox {{
                background: #111; color: #888;
                border: 1px solid #1E1E1E; border-radius: 7px;
                padding: 0 12px; font-size: 12px; height: 34px;
            }}
            QComboBox:focus {{ border-color: {ACCENT}; }}
            QComboBox QAbstractItemView {{ background: #111; color: #CCC; selection-background-color: {ACCENT}; }}
        """)

        self._gen_btn = QPushButton("⬡  Render Cosmos")
        self._gen_btn.setFixedHeight(34)
        self._gen_btn.setStyleSheet(f"""
            QPushButton {{
                background: {ACCENT}; color: #000;
                border: none; border-radius: 7px;
                padding: 0 20px; font-size: 13px; font-weight: 700;
            }}
            QPushButton:hover {{ background: #00C9D4; }}
            QPushButton:disabled {{ background: #001A1B; color: #333; }}
        """)
        self._gen_btn.clicked.connect(self._render)

        self._status = QLabel("Select filter and render")
        self._status.setStyleSheet("color: #222; font-size: 11px; background: transparent; border: none;")

        bar_lay.addWidget(title)
        bar_lay.addStretch()
        bar_lay.addWidget(self._status)
        bar_lay.addWidget(self._uni_combo)
        bar_lay.addWidget(self._gen_btn)
        root.addWidget(top_bar)

        # ── WebEngine ──
        self._web = QWebEngineView()
        self._web.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._web.setStyleSheet("background: #050505;")
        self._show_placeholder()
        root.addWidget(self._web)

        # Load universes for combo
        self._load_universes()

    def _load_universes(self):
        class _UWorker(QThread):
            done = Signal(list)
            def run(self_):
                s = get_session()
                unis = [{"id": u.id, "name": u.name} for u in s.query(Universe).all()]
                s.close()
                self_.done.emit(unis)
        w = _UWorker(self)
        w.done.connect(self._on_unis)
        w.start()
        self._uni_loader = w

    def _on_unis(self, unis: list):
        current_data = self._uni_combo.currentData()
        self._uni_combo.blockSignals(True)
        self._uni_combo.clear()
        self._uni_combo.addItem("🌌  All Universes", None)
        for u in unis:
            self._uni_combo.addItem(f"🌐  {u['name']}", u["id"])
        
        idx = self._uni_combo.findData(current_data)
        if idx >= 0:
            self._uni_combo.setCurrentIndex(idx)
        self._uni_combo.blockSignals(False)

    def showEvent(self, event):
        super().showEvent(event)
        self._load_universes()

    def _show_placeholder(self):
        html = f"""<html><body style="background:#050505; color:#111;
            display:flex; align-items:center; justify-content:center;
            height:100vh; margin:0; font-family:'Segoe UI',sans-serif;">
          <div style="text-align:center;">
            <div style="font-size:80px; opacity:0.05; animation: pulse 2s infinite;">⬡</div>
            <p style="font-size:15px; margin-top:20px; color:#1A1A1A; letter-spacing:2px;">
              RENDER COSMOS DABAIN
            </p>
            <p style="font-size:11px; margin-top:8px; color:#111;">
              Zendrix Prime · Universes · Characters · Factions · Locations · Artifacts · Events · Stories
            </p>
          </div>
        </body></html>"""
        self._web.setHtml(html)

    def _show_loading(self):
        html = f"""<html><head>
        <style>
          @keyframes spin {{ from {{ transform: rotate(0deg); }} to {{ transform: rotate(360deg); }} }}
          @keyframes pulse {{ 0%,100% {{ opacity:.1; }} 50% {{ opacity:.3; }} }}
        </style></head>
        <body style="background:#050505; display:flex; align-items:center; justify-content:center; height:100vh; margin:0; font-family:'Segoe UI',sans-serif;">
          <div style="text-align:center;">
            <div style="font-size:60px; animation:spin 3s linear infinite; color:{ACCENT}; opacity:.5;">⬡</div>
            <p style="font-size:13px; margin-top:24px; color:{ACCENT}88; letter-spacing:3px;">BUILDING COSMOS...</p>
            <p style="font-size:10px; margin-top:8px; color:#1A1A1A;">Fetching entities from the multiverse database</p>
          </div>
        </body></html>"""
        self._web.setHtml(html)

    def _render(self):
        self._gen_btn.setEnabled(False)
        self._status.setText("Fetching multiverse data...")
        self._show_loading()

        uid = self._uni_combo.currentData()
        self._worker = CosmicDataWorker(universe_filter=uid)
        self._worker.done.connect(self._on_data)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_data(self, data: dict):
        n = len(data["nodes"])
        e = len(data["edges"])
        self._status.setText(f"Rendering {n} nodes, {e} edges...")

        # Load/cache vis.js
        if self._vis_js_cache is None:
            self._vis_js_cache = self._get_vis_js()

        html = _build_cosmic_html(self._vis_js_cache, data)

        # Write to temp file (avoids setHtml 2MB limit)
        if self._last_tmp and os.path.exists(self._last_tmp):
            try:
                os.unlink(self._last_tmp)
            except Exception:
                pass

        tmp = tempfile.NamedTemporaryFile(
            suffix=".html", delete=False,
            prefix="zenai_cosmic_", mode="w", encoding="utf-8"
        )
        tmp.write(html)
        tmp.close()
        self._last_tmp = tmp.name

        self._web.load(QUrl.fromLocalFile(tmp.name))
        self._status.setText(f"✓  {n} nodes  ·  {e} connections")
        self._gen_btn.setEnabled(True)

    def _on_error(self, msg: str):
        self._gen_btn.setEnabled(True)
        self._status.setText(f"Error: {msg[:80]}")
        self._web.setHtml(f"""<html><body style="background:#050505;color:#e74c3c;display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;">
          <div style="text-align:center;"><div style="font-size:40px;">⚠</div><p style="margin-top:16px;font-size:14px;">{msg}</p></div>
        </body></html>""")

    @staticmethod
    def _get_vis_js() -> str:
        """Return vis-network JS — from local cache, download if missing."""
        os.makedirs(os.path.dirname(VIS_CACHE), exist_ok=True)
        if not os.path.exists(VIS_CACHE):
            try:
                urllib.request.urlretrieve(VIS_CDN, VIS_CACHE)
            except Exception:
                return ""   # offline fallback — graph won't render but app won't crash
        with open(VIS_CACHE, "r", encoding="utf-8") as f:
            return f.read()
