"""
app/graph/queries.py
====================
Module 3 — Graph Query Utilities
Analytical queries on NetworkX graphs. No DB access — operates on
pre-built Graph objects returned by builder.py.

Functions:
  - get_neighbors(G, node_id)                → direct neighbors
  - get_neighbors_by_edge_type(G, node_id, edge_type)
  - find_path(G, source_id, target_id)       → shortest path
  - find_all_paths(G, source, target, cutoff)→ all simple paths up to cutoff length
  - get_subgraph(G, node_id, depth)          → ego subgraph at depth
  - get_most_connected(G, top_n)             → top N nodes by degree
  - get_centrality(G)                        → betweenness centrality dict
  - get_clusters(G)                          → connected components
  - get_nodes_by_type(G, entity_type)        → filter nodes by entity_type
  - get_edges_by_type(G, edge_type)          → filter edges by type
  - graph_summary(G)                         → stats dict
"""

from typing import List, Dict, Any, Optional, Tuple
import networkx as nx


# ─────────────────────────────────────────────
# Neighbor queries
# ─────────────────────────────────────────────

def get_neighbors(G: nx.Graph, node_id: str) -> List[Dict[str, Any]]:
    """
    Return all immediate neighbors of a node.
    Result: [{"node_id", "label", "entity_type", "edge_type"}]
    """
    results = []
    if node_id not in G:
        return results

    if isinstance(G, nx.DiGraph):
        # outgoing + incoming
        successors = [(nbr, G[node_id][nbr]) for nbr in G.successors(node_id)]
        predecessors = [(nbr, G[nbr][node_id]) for nbr in G.predecessors(node_id)]
        all_edges = successors + predecessors
    else:
        all_edges = [(nbr, G[node_id][nbr]) for nbr in G.neighbors(node_id)]

    seen = set()
    for nbr_id, edge_attrs in all_edges:
        if nbr_id in seen:
            continue
        seen.add(nbr_id)
        node_attrs = G.nodes[nbr_id]
        results.append({
            "node_id":    nbr_id,
            "label":      node_attrs.get("label", nbr_id),
            "entity_type":node_attrs.get("entity_type", "unknown"),
            "importance_score": node_attrs.get("importance_score", 50),
            "edge_type":  edge_attrs.get("edge_type", "related"),
        })

    results.sort(key=lambda x: x["importance_score"], reverse=True)
    return results


def get_neighbors_by_edge_type(
    G: nx.Graph, node_id: str, edge_type: str
) -> List[Dict[str, Any]]:
    """
    Filter neighbors by a specific edge_type.
    Useful for: "who are the enemies of this character?"
    """
    all_nbrs = get_neighbors(G, node_id)
    return [n for n in all_nbrs if n["edge_type"] == edge_type]


# ─────────────────────────────────────────────
# Path queries
# ─────────────────────────────────────────────

def find_path(
    G: nx.Graph, source_id: str, target_id: str
) -> Optional[List[str]]:
    """
    Find shortest path between two nodes.
    Returns list of node_ids, or None if no path exists.
    """
    try:
        undirected = G.to_undirected() if isinstance(G, nx.DiGraph) else G
        return nx.shortest_path(undirected, source=source_id, target=target_id)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None


def find_all_paths(
    G: nx.Graph, source_id: str, target_id: str, cutoff: int = 4
) -> List[List[str]]:
    """
    All simple paths up to `cutoff` hops (default 4).
    Returns list of paths (each path = list of node_ids).
    Expensive on large graphs — use cutoff wisely.
    """
    undirected = G.to_undirected() if isinstance(G, nx.DiGraph) else G
    try:
        return list(nx.all_simple_paths(undirected, source_id, target_id, cutoff=cutoff))
    except (nx.NodeNotFound, nx.NetworkXNoPath):
        return []


def path_to_labels(G: nx.Graph, path: List[str]) -> List[Dict[str, str]]:
    """
    Convert a path (list of node_ids) to human-readable label list.
    Returns [{"node_id", "label", "entity_type"}]
    """
    result = []
    for nid in path:
        attrs = G.nodes.get(nid, {})
        result.append({
            "node_id":    nid,
            "label":      attrs.get("label", nid),
            "entity_type":attrs.get("entity_type", "unknown"),
        })
    return result


# ─────────────────────────────────────────────
# Subgraph extraction
# ─────────────────────────────────────────────

def get_subgraph(G: nx.Graph, node_id: str, depth: int = 2) -> nx.Graph:
    """
    Extract an ego subgraph: all nodes within `depth` hops of node_id.
    Returns a new Graph (copy). depth=1 = immediate neighbors only.
    """
    undirected = G.to_undirected() if isinstance(G, nx.DiGraph) else G
    if node_id not in undirected:
        return type(G)()
    ego = nx.ego_graph(undirected, node_id, radius=depth)
    # Re-apply original node attributes
    for n in ego.nodes():
        ego.nodes[n].update(G.nodes.get(n, {}))
    return ego


# ─────────────────────────────────────────────
# Importance / centrality
# ─────────────────────────────────────────────

def get_most_connected(G: nx.Graph, top_n: int = 10) -> List[Dict[str, Any]]:
    """
    Return top N nodes by degree (most connections).
    Result: [{"node_id", "label", "entity_type", "degree", "importance_score"}]
    """
    undirected = G.to_undirected() if isinstance(G, nx.DiGraph) else G
    degree_map = dict(undirected.degree())

    results = []
    for nid, deg in sorted(degree_map.items(), key=lambda x: x[1], reverse=True)[:top_n]:
        attrs = G.nodes.get(nid, {})
        results.append({
            "node_id":      nid,
            "label":        attrs.get("label", nid),
            "entity_type":  attrs.get("entity_type", "unknown"),
            "degree":       deg,
            "importance_score": attrs.get("importance_score", 50),
        })
    return results


def get_centrality(G: nx.Graph) -> Dict[str, float]:
    """
    Betweenness centrality for all nodes.
    Higher = more "bridge" role in the graph.
    Returns {node_id: centrality_float}
    """
    undirected = G.to_undirected() if isinstance(G, nx.DiGraph) else G
    if len(undirected) == 0:
        return {}
    return nx.betweenness_centrality(undirected, normalized=True)


def get_centrality_ranked(G: nx.Graph, top_n: int = 10) -> List[Dict[str, Any]]:
    """
    Centrality as ranked list with node labels.
    """
    centrality = get_centrality(G)
    ranked = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:top_n]
    results = []
    for nid, score in ranked:
        attrs = G.nodes.get(nid, {})
        results.append({
            "node_id":     nid,
            "label":       attrs.get("label", nid),
            "entity_type": attrs.get("entity_type", "unknown"),
            "centrality":  round(score, 4),
        })
    return results


# ─────────────────────────────────────────────
# Clustering / components
# ─────────────────────────────────────────────

def get_clusters(G: nx.Graph) -> List[List[str]]:
    """
    Return connected components as list of node_id lists.
    Sorted by size descending (largest cluster first).
    """
    undirected = G.to_undirected() if isinstance(G, nx.DiGraph) else G
    components = list(nx.connected_components(undirected))
    return sorted([list(c) for c in components], key=len, reverse=True)


def get_isolated_nodes(G: nx.Graph) -> List[Dict[str, Any]]:
    """
    Nodes with zero connections (potential lore orphans / missing links).
    """
    isolated = list(nx.isolates(G.to_undirected() if isinstance(G, nx.DiGraph) else G))
    results = []
    for nid in isolated:
        attrs = G.nodes.get(nid, {})
        results.append({
            "node_id":     nid,
            "label":       attrs.get("label", nid),
            "entity_type": attrs.get("entity_type", "unknown"),
        })
    return results


# ─────────────────────────────────────────────
# Type-based filters
# ─────────────────────────────────────────────

def get_nodes_by_type(G: nx.Graph, entity_type: str) -> List[Dict[str, Any]]:
    """
    Return all nodes of a given entity_type.
    entity_type ∈ {character, faction, location, event, artifact, universe, root_entity}
    """
    return [
        {"node_id": nid, **attrs}
        for nid, attrs in G.nodes(data=True)
        if attrs.get("entity_type") == entity_type
    ]


def get_edges_by_type(G: nx.Graph, edge_type: str) -> List[Dict[str, Any]]:
    """
    Return all edges of a given edge_type.
    """
    return [
        {
            "source": u,
            "target": v,
            "edge_type": edge_type,
            **{k: val for k, val in attrs.items() if k != "edge_type"},
        }
        for u, v, attrs in G.edges(data=True)
        if attrs.get("edge_type") == edge_type
    ]


# ─────────────────────────────────────────────
# Summary stats
# ─────────────────────────────────────────────

def graph_summary(G: nx.Graph) -> Dict[str, Any]:
    """
    Return a summary dict with counts, density, component info.
    Used by UI dashboard / logging.
    """
    undirected = G.to_undirected() if isinstance(G, nx.DiGraph) else G

    type_counts: Dict[str, int] = {}
    edge_type_counts: Dict[str, int] = {}

    for _, attrs in G.nodes(data=True):
        etype = attrs.get("entity_type", "unknown")
        type_counts[etype] = type_counts.get(etype, 0) + 1

    for _, _, attrs in G.edges(data=True):
        etype = attrs.get("edge_type", "unknown")
        edge_type_counts[etype] = edge_type_counts.get(etype, 0) + 1

    components = list(nx.connected_components(undirected))
    density = nx.density(undirected)
    isolated = len(list(nx.isolates(undirected)))

    return {
        "node_count":       G.number_of_nodes(),
        "edge_count":       G.number_of_edges(),
        "graph_type":       G.graph.get("graph_type", "unknown"),
        "directed":         isinstance(G, nx.DiGraph),
        "density":          round(density, 4),
        "component_count":  len(components),
        "isolated_nodes":   isolated,
        "node_type_counts": type_counts,
        "edge_type_counts": edge_type_counts,
    }
