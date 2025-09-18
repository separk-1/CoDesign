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
               description="EBCT(Empty Bed Contact Time)는 **층(bed)의 비어있는 체적을 유량으로 나눈 시간**이에요. 값이 클수록 접촉시간이 길어져 제거 효율이 좋아질 가능성이 큽니다.",
               rationale="공식: EBCT = V/Q (V=bed volume, Q=flow; gpm=gal/min).",
               aliases=["ebct", "empty bed contact time"])
    G.add_node("V", type="concept",
               description="**V**는 bed volume(층 체적, gal)**입니다.** 직접 체적을 주거나, 지름(D)·층높이(H)를 주면 V=π·(D/2)²·H로 계산한 뒤 gal로 변환해요.",
               rationale="V(ft³)=π(D/2)²H, V(gal)=V(ft³)×7.48052.",
               aliases=["v", "volume", "bed volume", "볼륨", "체적"])
    G.add_node("Q", type="concept",
               description="**Q**는 유량(flow rate)**입니다.** 기본 단위는 gpm이고, L/min이나 m³/h로 입력해도 자동 변환돼요. EBCT는 V/Q라서 Q가 커지면 EBCT는 줄어듭니다.",
               rationale="1 gpm = 3.785 L/min ≈ 0.2271 m³/h.",
               aliases=["q", "flow", "flow rate", "유량"])
    G.add_node("D", type="concept", aliases=["d", "diameter", "지름"])
    G.add_node("H", type="concept", aliases=["h", "height", "bed height", "높이"])

    # --- Nodes: Risks & Advice ---
    G.add_node("V_risk", type="risk",
               description=("**Volume을 늘리면** EBCT는 선형으로 증가하지만:\n"
                            "• 비용/공간 ↑ (장비·매질·기초)\n"
                            "• 압력손실/유압: D↑는 ΔP↓ 경향, H↑는 ΔP↑ 경향\n"
                            "• 세척수·시간 ↑, 배수 용량 확인\n"
                            "• 응답시간(스타트업/전환) ↑, 핸들링/교체 주기 검토"),
               rationale="효과: EBCT↑(선형). 부작용: Capex/footprint↑, backwash demand↑, ΔP는 D/H 확장 방식에 좌우.")
    G.add_node("Q_risk", type="risk",
               description=("**Flow를 늘리면** 처리량은 ↑, EBCT는 ↓. 또한:\n"
                            "• 제거효율 저하 가능(접촉시간 감소)\n"
                            "• ΔP↑, 펌프 부하/소음↑\n"
                            "• 분포 불균일/채널링 위험↑\n"
                            "• 세척 주기 단축 가능"),
               rationale="효과: EBCT↓(역비례), superficial velocity↑ → ΔP↑.")

    G.add_node("V_advice", type="advice",
               designer="볼륨을 키우면 접촉시간은 늘지만 설비 크기·비용·세척수도 늘어요. 대신 지름을 조금 키우거나 병렬 Vessel 추가도 고려해보세요.",
               engineer="EBCT↑(선형). Capex/footprint↑, backwash demand↑. D 확장 시 U_s↓로 ΔP 완화, H 확장 시 ΔP↑. 병렬/단차 검토.")
    G.add_node("Q_advice", type="advice",
               designer="유량을 올리면 접촉시간이 줄어 제거율이 떨어질 수 있어요. 대신 매질을 늘리거나 병렬 라인을 고려해보세요.",
               engineer="Q↑ → EBCT↓, U_s↑ → ΔP↑, 채널링 위험↑. 대안: V↑, D↑, 병렬 증설, 단계 흡착.")
    G.add_node("D_advice", type="advice",
               designer="지름을 키우면 접촉시간이 꽤 늘면서 압력손실도 완화되는 편이에요. 설치 공간만 허용되면 좋은 방향입니다.",
               engineer="D↑ ⇒ V∝D²·H, U_s↓, ΔP↓ 경향. 기초/노즐 레이아웃 확인.")
    G.add_node("H_advice", type="advice",
               designer="층 높이를 키우면 접촉시간은 늘지만 압력손실도 같이 늘 수 있어요. 펌프/세척 조건을 함께 확인하세요.",
               engineer="H↑ ⇒ V↑, ΔP↑. backwash expansion, pump head margin 확인.")

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
