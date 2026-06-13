"""
app/graph/__init__.py
=====================
Module 3 — Knowledge Graph Engine
Public API exports.

Usage:
    from app.graph import build_graph, visualize_graph
    from app.graph import get_neighbors, find_path, graph_summary

Builder (NetworkX graphs from DB):
    build_graph(session, graph_type, entity_id=None)
    universe_graph(session, universe_id)
    character_graph(session, character_id)
    multiverse_graph(session)
    root_entity_graph(session, root_entity_id)

Visualizer (NetworkX → PyVis HTML):
    visualize_graph(G, output_path=None, title=..., return_html=False)
    export_html(G, output_path, title=...)
    get_html_string(G, title=...)
    export_graph_image_data(G)  → Plotly-compatible dict

Queries (analysis on Graph objects):
    get_neighbors(G, node_id)
    get_neighbors_by_edge_type(G, node_id, edge_type)
    find_path(G, source_id, target_id)
    find_all_paths(G, source_id, target_id, cutoff=4)
    path_to_labels(G, path)
    get_subgraph(G, node_id, depth=2)
    get_most_connected(G, top_n=10)
    get_centrality(G)
    get_centrality_ranked(G, top_n=10)
    get_clusters(G)
    get_isolated_nodes(G)
    get_nodes_by_type(G, entity_type)
    get_edges_by_type(G, edge_type)
    graph_summary(G)
"""

from app.graph.builder import (
    build_graph,
    universe_graph,
    character_graph,
    multiverse_graph,
    root_entity_graph,
)

from app.graph.visualizer import (
    visualize_graph,
    export_html,
    get_html_string,
    export_graph_image_data,
    graph_to_pyvis,
)

from app.graph.queries import (
    get_neighbors,
    get_neighbors_by_edge_type,
    find_path,
    find_all_paths,
    path_to_labels,
    get_subgraph,
    get_most_connected,
    get_centrality,
    get_centrality_ranked,
    get_clusters,
    get_isolated_nodes,
    get_nodes_by_type,
    get_edges_by_type,
    graph_summary,
)

__all__ = [
    # builder
    "build_graph",
    "universe_graph",
    "character_graph",
    "multiverse_graph",
    "root_entity_graph",
    # visualizer
    "visualize_graph",
    "export_html",
    "get_html_string",
    "export_graph_image_data",
    "graph_to_pyvis",
    # queries
    "get_neighbors",
    "get_neighbors_by_edge_type",
    "find_path",
    "find_all_paths",
    "path_to_labels",
    "get_subgraph",
    "get_most_connected",
    "get_centrality",
    "get_centrality_ranked",
    "get_clusters",
    "get_isolated_nodes",
    "get_nodes_by_type",
    "get_edges_by_type",
    "graph_summary",
]
