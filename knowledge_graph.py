import networkx as nx
import re
from typing import Optional, Tuple

_G = None

def get_graph():
    """Singleton accessor for the knowledge graph."""
    global _G
    if _G is None:
        _G = create_knowledge_graph()
    return _G

def create_knowledge_graph():
    """
    Creates and populates the knowledge graph with concepts, risks, and advice.
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

    return G


# --- Query Functions ---

def find_node_by_alias(graph: nx.DiGraph, alias: str) -> Optional[str]:
    """Finds a node in the graph by its alias."""
    for node, data in graph.nodes(data=True):
        if 'aliases' in data and alias.lower() in data['aliases']:
            return node
    return None

def query_concept(graph: nx.DiGraph, user_msg: str) -> Optional[Tuple[str, str]]:
    """
    Queries the graph for a concept based on the user's message.
    Returns a tuple of (description, rationale) if a concept is found.
    """
    user_msg = user_msg.strip().lower()

    # Simple regex for now, can be improved with NLP
    patterns = {
        "EBCT": re.compile(r"(ebct가\s*뭐|what\s*is\s*ebct)", re.I),
        "V": re.compile(r"(\bV\b|volume|볼륨).*(뭐|what)|(V|volume|볼륨)\s*가\s*뭐", re.I),
        "Q": re.compile(r"(\bQ\b|flow|유량).*(뭐|what)|(Q|flow|유량)\s*가\s*뭐", re.I),
    }


    # '...가 뭐야', '...의 뜻' 패턴 추가
    patterns_to_add = {
        "V": [r"(bed\s*volum.*)\s*(뭐|무엇|뜻)", r"(볼륨|체적)\s*(뭐|뜻)"],
        "Q": [r"(flow|유량)\s*(뭐|뜻)"],
        "EBCT": [r"ebct\s*(뭐|뜻)"],
    }

    for concept_name, regex_list in patterns_to_add.items():
        for pattern in regex_list:
            if re.search(pattern, user_msg, re.I):
                node = graph.nodes.get(concept_name)
                if node and node.get('type') == 'concept':
                    return node.get('description'), node.get('rationale')

    for concept_name, pattern in patterns.items():
        if pattern.search(user_msg):
            node = graph.nodes.get(concept_name)
            if node and node.get('type') == 'concept':
                return node.get('description'), node.get('rationale')

    return None


def query_risk(graph: nx.DiGraph, user_msg: str) -> Optional[Tuple[str, str]]:
    """
    Queries the graph for a risk based on the user's message.
    Returns a tuple of (description, rationale) if a risk is found.
    """
    user_msg_lower = user_msg.strip().lower()

    # Check for risk-related words first for efficiency
    risk_words = ["문제", "단점", "리스크", "risk", "issue", "disadvantage"]
    if not any(word in user_msg_lower for word in risk_words):
        return None

    # Check which concept is being discussed
    concept_name = None
    if any(alias in user_msg_lower for alias in graph.nodes["V"].get("aliases", [])):
        concept_name = "V"
    elif any(alias in user_msg_lower for alias in graph.nodes["Q"].get("aliases", [])):
        concept_name = "Q"

    if not concept_name:
        return None

    # Find the risk node connected to this concept
    for u, v, data in graph.edges(data=True):
        if u == concept_name and data.get('type') == 'has_risk':
            risk_node = graph.nodes.get(v)
            if risk_node:
                return risk_node.get('description'), risk_node.get('rationale')

    return None


def query_advice(graph: nx.DiGraph, target: str, role: str) -> str:
    """
    Queries the graph for advice on a target parameter for a specific role.
    """
    target = target.lower()
    role = role.lower()

    # Map target to concept node name
    target_map = {
        "volume": "V",
        "flow": "Q",
        "diameter": "D",
        "height": "H",
    }
    concept_name = target_map.get(target)
    if not concept_name:
        return ""

    # Find the advice node connected to this concept
    for u, v, data in graph.edges(data=True):
        if u == concept_name and data.get('type') == 'has_advice':
            advice_node = graph.nodes.get(v)
            if advice_node:
                return advice_node.get(role, "") # Return advice for the role, or empty string if role not found

    return ""
