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

def format_subgraph_for_prompt(subgraph: nx.DiGraph) -> str:
    """
    Formats the subgraph into a string that can be used as context in an LLM prompt.
    """
    if not subgraph:
        return "No relevant information found in the knowledge graph."

    context_parts = []
    context_parts.append("Here is the relevant information from the knowledge graph:")

    for node_id, data in subgraph.nodes(data=True):
        node_type = data.get('type', 'N/A')
        description = data.get('description', '')
        rationale = data.get('rationale', '')
        designer_advice = data.get('designer', '')
        engineer_advice = data.get('engineer', '')

        context_parts.append(f"\n- Node '{node_id}' (Type: {node_type}):")
        if description:
            context_parts.append(f"  - Description: {description}")
        if rationale:
            context_parts.append(f"  - Rationale: {rationale}")
        if designer_advice:
            context_parts.append(f"  - Advice for Designers: {designer_advice}")
        if engineer_advice:
            context_parts.append(f"  - Advice for Engineers: {engineer_advice}")

    context_parts.append("\nRelationships:")
    for source, target, data in subgraph.edges(data=True):
        edge_type = data.get('type', 'related to')
        context_parts.append(f"- '{source}' {edge_type} '{target}'")

    return "\n".join(context_parts)

def generate_response(query: str, context: str, genai_model) -> str:
    """
    Generates a conversational response using the provided genai_model object.
    """
    if not genai_model:
        return "Sorry, the AI model is not configured."

    system_prompt = (
        "You are an AI assistant for water treatment system design, specifically focusing on EBCT calculations. "
        "Your role is to be a helpful mediator between designers and engineers. "
        "Answer the user's question in a conversational and helpful manner, using only the information provided in the context from the knowledge graph. "
        "Do not make up information. If the context does not contain the answer, say that you don't have enough information. "
        "Provide your answer in English."
    )

    user_prompt = (
        f"Based on the following context, please answer my question.\n\n"
        f"--- CONTEXT ---\n{context}\n\n"
        f"--- QUESTION ---\n{query}\n\n"
        f"--- ANSWER ---\n"
    )

    try:
        resp = genai_model.generate_content(
            contents=user_prompt,
            generation_config=types.GenerateContentConfig(
                system_instruction=system_prompt
            )
        )
        return resp.text.strip()
    except Exception as e:
        print(f"[rag_chain.generate_response] error: {e}", flush=True)
        return "Sorry, an error occurred while generating the response."

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
