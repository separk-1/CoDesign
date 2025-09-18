# === BOOT LOG ===
print("BOOT: app.py loaded", flush=True)

import os, math, json, traceback
from typing import Optional, Dict, Any
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
import networkx as nx

# .env 로드 (명시 경로로 안전하게)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
print("Gemini key loaded?", bool(os.getenv("GEMINI_API_KEY")), flush=True)

# 결정론적 EBCT 계산기 (너의 파서/계산)
from calculator import compute_ebct
import graph_manager as gm

# ---- Knowledge Graph & Gemini ----
G = gm.get_graph()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

_genai_model = None
if GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        _genai_model = genai.GenerativeModel(GEMINI_MODEL)
    except Exception as e:
        print(f"[warn] Failed to initialize Gemini Model: {e}", flush=True)
        _genai_model = None

# Flask app
app = Flask(__name__, static_folder="static")

# ----------------- 기본 라우트 -----------------
@app.get("/ping")
def ping():
    return "pong", 200

@app.get("/")
def index():
    return send_from_directory(".", "index.html")

# (옵션) 기존 계산 API 유지
@app.post("/api/calculate")
def calculate():
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"ok": False, "error": "Missing 'query'"}), 400
    try:
        res = compute_ebct(query)
        if not isinstance(res, dict) or "minutes" not in res:
            raise ValueError("compute_ebct returned invalid result")
        return jsonify(res), 200
    except Exception as e:
        print("[/api/calculate] error:", e, flush=True)
        return jsonify({"ok": False, "error": str(e)}), 500

# ----------------- 지식 그래프 API 추가 -----------------
@app.get("/api/knowledge-graph")
def get_knowledge_graph():
    """Returns the knowledge graph data as a JSON object."""
    # Convert NetworkX graph to a dictionary format suitable for D3.js
    graph_data = nx.node_link_data(G)
    return jsonify(graph_data)

# ----------------- 유틸 -----------------
def _num(x, d: int = 4):
    try:
        return round(float(x), d)
    except:
        return x

def compute_from_used(used: Dict[str, Any]):
    """정규화 값(used)으로 EBCT 재계산."""
    if not used:
        return None
    V = used.get("volume_gal")
    Q = used.get("flow_gpm")
    if V is not None and Q not in (None, 0):
        return V / Q
    GAL_PER_FT3 = 7.48052
    D = used.get("diam_ft")
    H = used.get("height_ft")
    Q = used.get("flow_gpm")
    if None not in (D, H, Q) and Q != 0:
        V_ft3 = math.pi * (D / 2.0) ** 2 * H
        V_gal = V_ft3 * GAL_PER_FT3
        return V_gal / Q
    return None

# ---------- 역할별 톤 & 조언 ----------
def tone(reply: str, role: str) -> str:
    role = (role or "").lower()
    if role == "designer":
        return reply.replace("≈", "약 ").replace("EBCT", "접촉시간(EBCT)")
    return reply  # engineer는 원문 유지

import rag_chain

# ----------------- 대화형 API (RAG-based) -----------------
@app.post("/api/chat")
def chat():
    """
    Handles chat messages using the GraphRAG chain.
    body: { messages:[{role,content}...], state:{ role: 'designer'|'engineer', used: dict|null } }
    """
    data = request.get_json(silent=True) or {}
    messages = data.get("messages") or []
    state = data.get("state") or {}
    role = (state.get("role") or "designer")

    if not messages:
        return jsonify({"error": "No messages"}), 400
    user_msg = messages[-1].get("content") or ""

    try:
        # Always try to perform a calculation first to ground the conversation
        # This can be used by the UI to display current numbers.
        try:
            calc_result = compute_ebct(user_msg)
            if not isinstance(calc_result, dict) or "minutes" not in calc_result:
                calc_result = None
        except Exception:
            calc_result = None

        # Execute the RAG chain to get a conversational response
        rag_result = rag_chain.execute_rag_chain(G, user_msg, _genai_model)

        # Combine results
        reply = rag_result.get("reply", "No response from RAG chain.")
        rationale = rag_result.get("rationale", "")

        # The 'used' state should be updated based on the latest successful calculation
        used_new = (calc_result.get("detail", {}).get("units_normalized") or {}) if calc_result and calc_result.get("ok") else state.get("used", {})
        minutes_new = calc_result.get("minutes") if calc_result and calc_result.get("ok") else _num(compute_from_used(used_new))

        response_payload = {
            "reply": tone(reply, role),
            "rationale": tone(rationale, role),
            "calc": {
                "minutes": _num(minutes_new),
                "used": used_new
            }
        }

        return jsonify(response_payload), 200

    except Exception as e:
        tb = traceback.format_exc()
        print("[/api/chat] error:", e, "\n", tb, flush=True)
        return jsonify({"error": str(e)}), 500

# ----------------- Graph Management APIs -----------------
@app.post("/api/graph/nodes")
def add_graph_node():
    """Adds a new node to the knowledge graph."""
    data = request.get_json()
    if not data or "id" not in data or "attributes" not in data:
        return jsonify({"ok": False, "error": "Missing 'id' or 'attributes'"}), 400

    node_id = data["id"]
    attributes = data["attributes"]

    success = gm.add_node(G, node_id, attributes)
    if success:
        return jsonify({"ok": True, "message": f"Node '{node_id}' added."}), 201
    else:
        return jsonify({"ok": False, "error": f"Node '{node_id}' already exists."}), 409

@app.put("/api/graph/nodes/<path:node_id>")
def update_graph_node(node_id):
    """Updates an existing node in the knowledge graph."""
    data = request.get_json()
    if not data or "attributes" not in data:
        return jsonify({"ok": False, "error": "Missing 'attributes'"}), 400

    attributes = data["attributes"]

    success = gm.update_node(G, node_id, attributes)
    if success:
        return jsonify({"ok": True, "message": f"Node '{node_id}' updated."}), 200
    else:
        return jsonify({"ok": False, "error": f"Node '{node_id}' not found."}), 404

@app.delete("/api/graph/nodes/<path:node_id>")
def delete_graph_node(node_id):
    """Deletes a node from the knowledge graph."""
    success = gm.delete_node(G, node_id)
    if success:
        return jsonify({"ok": True, "message": f"Node '{node_id}' deleted."}), 200
    else:
        return jsonify({"ok": False, "error": f"Node '{node_id}' not found."}), 404

@app.post("/api/graph/edges")
def add_graph_edge():
    """Adds a new edge to the knowledge graph."""
    data = request.get_json()
    if not data or "source" not in data or "target" not in data or "attributes" not in data:
        return jsonify({"ok": False, "error": "Missing 'source', 'target', or 'attributes'"}), 400

    source = data["source"]
    target = data["target"]
    attributes = data["attributes"]

    success = gm.add_edge(G, source, target, attributes)
    if success:
        return jsonify({"ok": True, "message": f"Edge from '{source}' to '{target}' added."}), 201
    else:
        return jsonify({"ok": False, "error": "Edge already exists or one of the nodes was not found."}), 409

@app.delete("/api/graph/edges")
def delete_graph_edge():
    """Deletes an edge from the knowledge graph."""
    data = request.get_json()
    if not data or "source" not in data or "target" not in data:
        return jsonify({"ok": False, "error": "Missing 'source' or 'target'"}), 400

    source = data["source"]
    target = data["target"]

    success = gm.delete_edge(G, source, target)
    if success:
        return jsonify({"ok": True, "message": f"Edge from '{source}' to '{target}' deleted."}), 200
    else:
        return jsonify({"ok": False, "error": "Edge not found."}), 404


# === RUN SERVER ===
if __name__ == "__main__":
    print("RUN: starting Flask...", flush=True)
    app.run("0.0.0.0", int(os.environ.get("PORT", 5001)), debug=False)