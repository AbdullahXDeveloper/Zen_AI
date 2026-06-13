"""
app/graph/visualizer.py
=======================
Module 3 — Graph Visualizer
Converts a NetworkX graph → interactive PyVis HTML file.

Features:
  - Entity-type color coding
  - Node size = importance_score (scaled)
  - Edge labels from edge_type
  - Physics simulation (repulsion layout)
  - Root entities always gold + oversized
  - Returns HTML string (for embedding in UI) OR saves to file
"""

import os
from pathlib import Path
from typing import Optional

import networkx as nx

try:
    from pyvis.network import Network
    PYVIS_AVAILABLE = True
except ImportError:
    PYVIS_AVAILABLE = False


# ─────────────────────────────────────────────
# Color scheme per entity type
# ─────────────────────────────────────────────

ENTITY_COLORS = {
    "character":   "#5B8DEF",   # blue
    "faction":     "#E07B39",   # orange
    "location":    "#4CAF82",   # green
    "event":       "#C75DB6",   # purple
    "artifact":    "#E6C244",   # gold-yellow
    "universe":    "#3ABFCF",   # cyan
    "root_entity": "#FFD700",   # pure gold
}

EDGE_COLORS = {
    "friend":         "#4CAF82",
    "enemy":          "#E05252",
    "family":         "#9C7FD4",
    "mentor":         "#5B8DEF",
    "student":        "#7EB8F7",
    "created":        "#E6C244",
    "destroyed":      "#E05252",
    "owns":           "#E07B39",
    "located_in":     "#4CAF82",
    "participated_in":"#C75DB6",
    "member_of":      "#A0A0A0",
    "variant_of":     "#D0D0D0",
    "linked":         "#BBBBBB",
    "connected":      "#BBBBBB",
}

DEFAULT_NODE_COLOR = "#AAAAAA"
DEFAULT_EDGE_COLOR = "#666666"


def _scale_size(importance_score: int) -> int:
    """Map importance 1-100 → node size 10-60px."""
    score = max(1, min(100, importance_score or 50))
    return int(10 + (score / 100) * 50)


# ─────────────────────────────────────────────
# Core: NetworkX → PyVis
# ─────────────────────────────────────────────

def graph_to_pyvis(
    G: nx.Graph,
    title: str = "Zendrix Knowledge Graph",
    height: str = "750px",
    width: str = "100%",
    bgcolor: str = "#1a1a2e",
    font_color: str = "#ffffff",
    physics: bool = True,
) -> "Network":
    """
    Convert a NetworkX Graph/DiGraph into a PyVis Network object.
    Call .show() or .generate_html() on the result.
    """
    if not PYVIS_AVAILABLE:
        raise ImportError("pyvis not installed. Run: pip install pyvis")

    directed = isinstance(G, nx.DiGraph)
    net = Network(
        height=height,
        width=width,
        bgcolor=bgcolor,
        font_color=font_color,
        directed=directed,
        notebook=False,
    )

    # Physics config for nice layout
    if physics:
        net.set_options("""
        {
          "physics": {
            "enabled": true,
            "barnesHut": {
              "gravitationalConstant": -8000,
              "centralGravity": 0.3,
              "springLength": 120,
              "springConstant": 0.04,
              "damping": 0.09
            },
            "maxVelocity": 50,
            "minVelocity": 0.1,
            "solver": "barnesHut"
          },
          "edges": {
            "smooth": { "type": "continuous" },
            "font": { "size": 11, "color": "#cccccc" }
          },
          "nodes": {
            "font": { "size": 14, "bold": true }
          }
        }
        """)

    # --- Add nodes ---
    for node_id, attrs in G.nodes(data=True):
        etype   = attrs.get("entity_type", "unknown")
        label   = attrs.get("label", str(node_id))
        score   = attrs.get("importance_score", 50)
        subtitle= attrs.get("subtitle", "")
        color   = ENTITY_COLORS.get(etype, DEFAULT_NODE_COLOR)
        size    = _scale_size(score)

        # Root entities: always gold border + bigger
        if etype == "root_entity":
            color = "#FFD700"
            size  = max(size, 55)

        tooltip = f"[{etype.upper()}] {label}"
        if subtitle:
            tooltip += f"\n{subtitle}"
        tooltip += f"\nImportance: {score}"

        net.add_node(
            str(node_id),
            label=label,
            title=tooltip,
            color=color,
            size=size,
            shape="dot" if etype not in ("universe", "root_entity") else "star",
        )

    # --- Add edges ---
    for u, v, attrs in G.edges(data=True):
        etype = attrs.get("edge_type", "related")
        label = attrs.get("label", "")
        color = EDGE_COLORS.get(etype, DEFAULT_EDGE_COLOR)

        # Enemy edges = dashed red
        dash = (etype == "enemy")

        net.add_edge(
            str(u), str(v),
            title=etype,
            label=label if label else None,
            color=color,
            dashes=dash,
            arrows="to" if directed else "",
        )

    return net


# ─────────────────────────────────────────────
# Export helpers
# ─────────────────────────────────────────────

def export_html(
    G: nx.Graph,
    output_path: str,
    title: str = "Zendrix Knowledge Graph",
    **kwargs,
) -> str:
    """
    Save graph as interactive HTML file.
    Returns the output path.
    """
    net = graph_to_pyvis(G, title=title, **kwargs)
    output_path = str(output_path)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    net.show(output_path, notebook=False)
    return output_path


def get_html_string(
    G: nx.Graph,
    title: str = "Zendrix Knowledge Graph",
    **kwargs,
) -> str:
    """
    Return HTML as a string (for embedding in PySide6 QWebEngineView).
    Uses a temp file internally, reads and deletes it.
    """
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w") as f:
        tmp_path = f.name

    export_html(G, tmp_path, title=title, **kwargs)
    with open(tmp_path, "r", encoding="utf-8") as f:
        html = f.read()
    os.unlink(tmp_path)
    return html


def export_graph_image_data(G: nx.Graph) -> dict:
    """
    Return lightweight dict summary for Plotly-based rendering
    (fallback when PyVis is unavailable, or for analytics charts).
    Returns:
      {
        "nodes": [{"id", "label", "entity_type", "importance_score"}],
        "edges": [{"source", "target", "edge_type"}],
        "node_count": int,
        "edge_count": int,
      }
    """
    nodes = [
        {
            "id": str(nid),
            "label": attrs.get("label", str(nid)),
            "entity_type": attrs.get("entity_type", "unknown"),
            "importance_score": attrs.get("importance_score", 50),
        }
        for nid, attrs in G.nodes(data=True)
    ]
    edges = [
        {
            "source": str(u),
            "target": str(v),
            "edge_type": attrs.get("edge_type", "related"),
        }
        for u, v, attrs in G.edges(data=True)
    ]
    return {
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
    }


# ─────────────────────────────────────────────
# Convenience: build + export in one call
# ─────────────────────────────────────────────

def visualize_graph(
    G: nx.Graph,
    output_path: Optional[str] = None,
    title: str = "Zendrix Knowledge Graph",
    return_html: bool = False,
) -> str:
    """
    One-call helper used by the UI modules.
    - If output_path given → saves HTML file, returns path
    - If return_html=True → returns HTML string
    - Else → returns HTML string by default
    """
    if output_path:
        return export_html(G, output_path, title=title)
    return get_html_string(G, title=title)
