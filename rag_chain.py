import networkx as nx
from typing import List, Dict, Any, Optional
from google.generativeai import types

def retrieve(graph: nx.DiGraph, query: str) -> Optional[nx.DiGraph]:
    """
    Retrieves a relevant subgraph from the main knowledge graph based on the user query.
    Finds nodes by matching query keywords against node aliases.
    The subgraph includes the matched nodes and their immediate neighbors.
    """
    query_lower = query.lower()
    relevant_nodes = set()

    # Find nodes by matching aliases
    for node_id, data in graph.nodes(data=True):
        aliases = data.get('aliases', [])
        for alias in aliases:
            if alias.lower() in query_lower:
                relevant_nodes.add(node_id)
                break # Move to the next node once one alias is matched

    if not relevant_nodes:
        return None

    # Get the neighbors of the relevant nodes
    subgraph_nodes = set(relevant_nodes)
    for node_id in relevant_nodes:
        # Add successors (e.g., V -> V_risk)
        for successor in graph.successors(node_id):
            subgraph_nodes.add(successor)
        # Add predecessors (though less common in this graph's structure)
        for predecessor in graph.predecessors(node_id):
            subgraph_nodes.add(predecessor)

    # Create the subgraph
    subgraph = graph.subgraph(subgraph_nodes)
    return subgraph

# rag_chain.py
import time

def format_subgraph_for_prompt(subgraph, max_nodes=12, max_edges=24, max_chars=4000):
    if not subgraph:
        return "No relevant information found in the knowledge graph."
    nodes = list(subgraph.nodes(data=True))[:max_nodes]
    keep = {nid for nid,_ in nodes}
    edges = [(s,t,d) for s,t,d in subgraph.edges(data=True)
             if s in keep and t in keep][:max_edges]

    parts = ["Here is the relevant information from the knowledge graph:"]
    for nid, data in nodes:
        parts.append(f"\n- Node '{nid}' (Type: {data.get('type','N/A')}):")
        for k, label in [("description","Description"),
                         ("rationale","Rationale"),
                         ("designer","Advice for Designers"),
                         ("engineer","Advice for Engineers")]:
            v = data.get(k, "")
            if v: parts.append(f"  - {label}: {v}")
    parts.append("\nRelationships:")
    for s,t,d in edges:
        parts.append(f"- '{s}' {d.get('type','related to')} '{t}'")

    txt = "\n".join(parts)
    return txt[:max_chars]


def generate_response(query: str, context: str, genai_model) -> str:
    """
    genai_model: app.py에서 주입하는 OpenAI shim (generate_content(list[str]) 지원)
    예외/빈응답을 재시도하고, 끝까지 실패하면 짧은 폴백을 반환.
    """
    if not genai_model:
        return "Model is not configured."

    system_prompt = (
        "You are a concise assistant for water treatment (EBCT, PFAS). "
        "Answer ONLY from the provided graph context. If not found, say so. English only."
    )
    user_prompt = f"--- CONTEXT ---\n{context}\n\n--- QUESTION ---\n{query}\n\nAnswer succinctly."

    for i in range(3):
        try:
            resp = genai_model.generate_content([system_prompt, user_prompt])
            text = getattr(resp, "text", "") or ""
            if text.strip():
                return text.strip()
            raise RuntimeError("empty_or_blocked")
        except Exception as e:
            print(f"[rag_chain.generate_response] attempt {i+1} failed: {e}", flush=True)
            time.sleep(0.8 * (2 ** i))

    return "I couldn’t generate an answer right now. Please try again in a moment."


def execute_rag_chain(graph: nx.DiGraph, query: str, genai_model) -> Dict[str, Any]:
    """
    Executes the full RAG pipeline: retrieve, format, and generate.
    """
    # 1. Retrieve
    subgraph = retrieve(graph, query)
    if not subgraph:
        return {
            "reply": "I couldn't find any relevant information for that. Could you try asking about 'EBCT', 'volume', or 'flow'?",
            "rationale": "No relevant nodes found in knowledge graph."
        }

    # 2. Format
    context = format_subgraph_for_prompt(subgraph)

    # 3. Generate
    reply = generate_response(query, context, genai_model)

    return {
        "reply": reply,
        "rationale": context
    }
