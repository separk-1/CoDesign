import networkx as nx
import json
import os
from typing import Optional, Dict, Any, List

GRAPH_FILE_PATH = "knowledge_graph.json"
_G = None

def get_graph():
    """Singleton accessor for the knowledge graph."""
    global _G
    if _G is None:
        _G = load_graph()
    return _G

def load_graph() -> nx.DiGraph:
    """Loads the graph from the JSON file, or creates a default one if the file doesn't exist."""
    if os.path.exists(GRAPH_FILE_PATH):
        try:
            with open(GRAPH_FILE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return nx.node_link_graph(data)
        except (json.JSONDecodeError, nx.NetworkXError) as e:
            print(f"Error loading graph from {GRAPH_FILE_PATH}: {e}. Creating a new default graph.", flush=True)
            return create_default_knowledge_graph()
    else:
        print(f"Graph file not found at {GRAPH_FILE_PATH}. Creating a new default graph.", flush=True)
        return create_default_knowledge_graph()

def save_graph(graph: nx.DiGraph):
    """Saves the graph to the JSON file."""
    try:
        data = nx.node_link_data(graph)
        with open(GRAPH_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving graph to {GRAPH_FILE_PATH}: {e}", flush=True)

def add_node(graph: nx.DiGraph, node_id: str, attributes: Dict[str, Any]) -> bool:
    """Adds a new node to the graph and saves the graph."""
    if graph.has_node(node_id):
        return False  # Node already exists
    graph.add_node(node_id, **attributes)
    save_graph(graph)
    return True

def update_node(graph: nx.DiGraph, node_id: str, attributes: Dict[str, Any]) -> bool:
    """Updates an existing node's attributes and saves the graph."""
    if not graph.has_node(node_id):
        return False # Node does not exist
    for key, value in attributes.items():
        graph.nodes[node_id][key] = value
    save_graph(graph)
    return True

def delete_node(graph: nx.DiGraph, node_id: str) -> bool:
    """Deletes a node from the graph and saves the graph."""
    if not graph.has_node(node_id):
        return False # Node does not exist
    graph.remove_node(node_id)
    save_graph(graph)
    return True

def add_edge(graph: nx.DiGraph, source: str, target: str, attributes: Dict[str, Any]) -> bool:
    """Adds a new edge to the graph and saves the graph."""
    if not graph.has_node(source) or not graph.has_node(target):
        return False # Source or target node does not exist
    if graph.has_edge(source, target):
        return False # Edge already exists
    graph.add_edge(source, target, **attributes)
    save_graph(graph)
    return True

def delete_edge(graph: nx.DiGraph, source: str, target: str) -> bool:
    """Deletes an edge from the graph and saves the graph."""
    if not graph.has_edge(source, target):
        return False # Edge does not exist
    graph.remove_edge(source, target)
    save_graph(graph)
    return True

def create_default_knowledge_graph() -> nx.DiGraph:
    """
    Creates and populates the default knowledge graph with concepts, risks, and advice.
    This is used if no existing graph file is found.
    """
    G = nx.DiGraph()

    # --- Nodes: Concepts ---
    G.add_node("EBCT", type="concept",
               description="EBCT (Empty Bed Contact Time) is the time calculated by dividing the empty volume of the bed by the flow rate. A higher value generally leads to better removal efficiency due to longer contact time.",
               rationale="Formula: EBCT = V/Q (V=bed volume, Q=flow rate; gpm=gal/min).",
               aliases=["ebct", "empty bed contact time"])
    G.add_node("V", type="concept",
               description="**V** represents the bed volume in gallons (gal). It can be provided directly or calculated from the diameter (D) and height (H) of the bed using the formula V = π·(D/2)²·H, which is then converted to gallons.",
               rationale="V(ft³) = π(D/2)²H; V(gal) = V(ft³) × 7.48052.",
               aliases=["v", "volume", "bed volume", "gal", "gallon"])
    G.add_node("Q", type="concept",
               description="**Q** represents the flow rate. The default unit is gallons per minute (gpm), but it can be automatically converted from L/min or m³/h. Since EBCT = V/Q, increasing Q will decrease EBCT.",
               rationale="1 gpm = 3.785 L/min ≈ 0.2271 m³/h.",
               aliases=["q", "flow", "flow rate", "gpm", "l/min", "m3/h"])
    G.add_node("D", type="concept", aliases=["d", "diameter", "ft", "in", "m"])
    G.add_node("H", type="concept", aliases=["h", "height", "bed height"])

    # --- Nodes: Risks & Advice ---
    G.add_node("V_risk", type="risk",
               description=("Increasing **Volume** linearly increases EBCT, but it also has downsides:\n"
                            "• Increased cost/footprint (equipment, media, foundation)\n"
                            "• Pressure drop/hydraulics: Increasing D tends to decrease ΔP, while increasing H tends to increase ΔP\n"
                            "• Increased backwash water volume and time; requires verification of drainage capacity\n"
                            "• Longer response time (startup/transition); requires review of handling/replacement cycles"),
               rationale="Effect: EBCT↑ (linear). Side effects: Capex/footprint↑, backwash demand↑, ΔP depends on the D/H expansion method.")
    G.add_node("Q_risk", type="risk",
               description=("Increasing **Flow** increases throughput but decreases EBCT. Additionally:\n"
                            "• Potential for reduced removal efficiency (less contact time)\n"
                            "• Increased ΔP, leading to higher pump load and noise\n"
                            "• Higher risk of uneven distribution and channeling\n"
                            "• May shorten the backwash cycle"),
               rationale="Effect: EBCT↓ (inverse). Superficial velocity↑ → ΔP↑.")

    G.add_node("V_advice", type="advice",
               designer="Increasing volume extends contact time but also increases equipment size, cost, and backwash water. Consider slightly increasing the diameter or adding parallel vessels as alternatives.",
               engineer="EBCT↑ (linear). Capex/footprint↑, backwash demand↑. Expanding D can mitigate ΔP by lowering U_s, while expanding H increases ΔP. Review parallel/staged options.")
    G.add_node("Q_advice", type="advice",
               designer="Raising the flow rate can reduce contact time and lower removal efficiency. Consider increasing the media volume or adding parallel lines instead.",
               engineer="Q↑ → EBCT↓, U_s↑ → ΔP↑, channeling risk↑. Alternatives: V↑, D↑, add parallel units, staged adsorption.")
    G.add_node("D_advice", type="advice",
               designer="Increasing the diameter significantly raises contact time while also tending to reduce pressure loss. This is a good approach if the installation space allows.",
               engineer="D↑ ⇒ V∝D²·H, U_s↓, ΔP↓ tendency. Verify foundation/nozzle layout.")
    G.add_node("H_advice", type="advice",
               designer="Increasing the bed height raises contact time but can also increase pressure loss. Be sure to check the pump and backwash conditions simultaneously.",
               engineer="H↑ ⇒ V↑, ΔP↑. Verify backwash expansion and pump head margin.")

    # --- Edges ---
    G.add_edge("V", "V_risk", type="has_risk")
    G.add_edge("Q", "Q_risk", type="has_risk")
    G.add_edge("V", "V_advice", type="has_advice")
    G.add_edge("Q", "Q_advice", type="has_advice")
    G.add_edge("D", "D_advice", type="has_advice")
    G.add_edge("H", "H_advice", type="has_advice")

    # Save the newly created default graph so it can be loaded next time
    save_graph(G)
    return G
