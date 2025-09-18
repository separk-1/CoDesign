# === BOOT LOG ===
print("BOOT: app.py loaded", flush=True)

import os, math, re, json, traceback
from typing import Optional, Dict, Any, List
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
import networkx as nx

# .env 로드 (명시 경로로 안전하게)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
print("Gemini key loaded?", bool(os.getenv("GEMINI_API_KEY")), flush=True)

# 결정론적 EBCT 계산기 (너의 파서/계산)
from calculator import compute_ebct
import knowledge_graph as kg

# ---- Knowledge Graph & Gemini ----
G = kg.get_graph()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

_genai = None
if GEMINI_API_KEY:
    try:
        import google.generativeai as genai  # type: ignore
        genai.configure(api_key=GEMINI_API_KEY)
        _genai = genai
    except Exception as e:
        print("[warn] google-generativeai import failed:", e, flush=True)

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

def extract_json(s: str) -> Optional[Dict[str, Any]]:
    if not s:
        return None
    m = re.search(r"```json\s*(\{.*?\})\s*```", s, re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except:
            pass
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(s[start:end+1])
        except:
            pass
    return None

def llm_parse(question: str, used: Optional[Dict[str, Any]]):
    """자연어 → 구조화 명령(JSON)만 LLM에 맡김(키 없으면 None 반환)"""
    if not _genai or not GEMINI_API_KEY:
        return None
    sys = (
        "You convert EBCT chat questions into JSON. Return ONLY JSON.\n"
        "ops:\n"
        " - set_baseline: {'op':'set_baseline','query':'...'}\n"
        " - what_if: {'op':'what_if','changes':[{'target':'volume|flow|diameter|height','kind':'pct|abs','value':10,'unit':'gpm|gal'(opt)}]}\n"
        " - solve_for: {'op':'solve_for','target':'volume|flow','ebct_min':12}\n"
        " - ask_effect: {'op':'ask_effect','target':'volume|flow|diameter|height'}\n"
        " - explain: {'op':'explain','topic':'ebct|V|Q|units'}\n"
        " - advice: {'op':'advice','about':'increase_volume|increase_flow|increase_diameter|increase_height'}\n"
        "No explanations."
    )
    user = (
        f"Question (Korean/English): {question}\n"
        f"Baseline used: {used or {}}\n"
        "Return JSON only."
    )
    try:
        model = _genai.GenerativeModel(GEMINI_MODEL)
        resp = model.generate_content([sys, user])
        return extract_json((resp.text or "").strip())
    except Exception as e:
        print("[llm_parse] error:", e, flush=True)
        return None

# ---------- Knowledge Graph Queries ----------
def concept_or_risk_from_graph(user_msg: str):
    """Queries the knowledge graph for concepts or risks."""
    # First, check for concepts
    concept_result = kg.query_concept(G, user_msg)
    if concept_result:
        return concept_result

    # If no concept, check for risks
    risk_result = kg.query_risk(G, user_msg)
    if risk_result:
        return risk_result

    return None

# ---------- 역할별 톤 & 조언 ----------
def tone(reply: str, role: str) -> str:
    role = (role or "").lower()
    if role == "designer":
        return reply.replace("≈", "약 ").replace("EBCT", "접촉시간(EBCT)")
    return reply  # engineer는 원문 유지

def add_advice(target: str, role: str) -> str:
    """Fetches advice from the knowledge graph."""
    return kg.query_advice(G, target, role)

def is_greeting(s: str) -> bool:
    s = (s or "").strip().lower()
    return bool(re.match(r"^(hi|hello|hey|안녕|안녕하세요|ㅎㅇ)\b", s))

def apply_changes(used: Dict[str, Any], changes: Optional[List[Dict[str, Any]]]):
    if not used:
        return None
    new_used = dict(used)
    for ch in (changes or []):
        tgt = (ch.get("target") or "").lower()
        kind = (ch.get("kind") or "").lower()
        val = float(ch.get("value")) if ch.get("value") is not None else None
        unit = (ch.get("unit") or "").lower()

        if tgt in ("volume", "bed volume"):
            if kind == "pct":
                if "volume_gal" not in new_used:
                    return None
                new_used["volume_gal"] *= (1 + (val or 0) / 100.0)
            elif kind == "abs":
                if unit not in ("gal", "gallon", "gallons", ""):
                    return None
                new_used["volume_gal"] = (new_used.get("volume_gal") or 0.0) + (val or 0.0)

        elif tgt in ("flow", "gpm"):
            if kind == "pct":
                if "flow_gpm" not in new_used:
                    return None
                new_used["flow_gpm"] *= (1 + (val or 0) / 100.0)
            elif kind == "abs":
                if unit not in ("gpm", ""):
                    return None
                new_used["flow_gpm"] = (new_used.get("flow_gpm") or 0.0) + (val or 0.0)

        elif tgt == "diameter":
            key = "diam_ft" if "diam_ft" in new_used else ("diam_m" if "diam_m" in new_used else ("diam_in" if "diam_in" in new_used else None))
            if not key or kind != "pct":
                return None
            new_used[key] *= (1 + (val or 0) / 100.0)

        elif tgt in ("height", "bed height"):
            key = "height_ft" if "height_ft" in new_used else ("height_m" if "height_m" in new_used else ("height_in" if "height_in" in new_used else None))
            if not key or kind != "pct":
                return None
            new_used[key] *= (1 + (val or 0) / 100.0)
    return new_used

# ----------------- 대화형 API -----------------
@app.post("/api/chat")
def chat():
    """
    body: { messages:[{role,content}...], state:{ role: 'designer'|'engineer', used: dict|null } }
    """
    data = request.get_json(silent=True) or {}
    messages = data.get("messages") or []
    state = data.get("state") or {}
    role = (state.get("role") or "designer")
    used = (state.get("used") or {})

    if not messages:
        return jsonify({"error": "No messages"}), 400
    user_msg = messages[-1].get("content") or ""

    try:
        # A) 인사
        if is_greeting(user_msg):
            reply = "안녕하세요! EBCT(Empty Bed Contact Time) 계산과 설계 중재를 도와드려요. "\
                    "예) ‘flow 800 gpm, bed volume 9600 gal’로 기준을 잡고, "\
                    "‘increase volume by 10%’, ‘what flow for 15 min’처럼 물어보세요."
            rationale = "EBCT = V/Q. V는 bed volume(gal), Q는 flow(gpm=gal/min)."
            return jsonify({"reply": tone(reply, role), "rationale": tone(rationale, role),
                            "calc": {"minutes": _num(compute_from_used(used)), "used": used}}), 200

        # B) 개념/리스크 고정 응답 (from Knowledge Graph)
        ca = concept_or_risk_from_graph(user_msg)
        if ca:
            reply, rationale = ca
            return jsonify({"reply": tone(reply, role), "rationale": tone(rationale, role),
                            "calc": {"minutes": _num(compute_from_used(used)), "used": used}}), 200

        # C) 숫자 포함 '완전 입력' → 베이스라인 설정
        try:
            baseline_try = compute_ebct(user_msg)
        except Exception:
            baseline_try = None

        if isinstance(baseline_try, dict) and baseline_try.get("minutes") is not None:
            res = baseline_try
            used_new = (res.get("detail") or {}).get("units_normalized") or {}
            reply = f"기준을 잡았어요. EBCT ≈ {_num(res['minutes'])} min."
            rationale = f"방법: {res.get('via','-')} · 공식: EBCT = V/Q"
            return jsonify({"reply": tone(reply, role), "rationale": tone(rationale, role),
                            "calc": {"minutes": _num(res["minutes"]), "used": used_new}}), 200

        # D) LLM 파싱 (있을 때만)
        parsed = llm_parse(user_msg, used)
        if not parsed:
            guidance = "숫자로 기준을 먼저 알려주세요. 예: 'flow 800 gpm, bed volume 9600 gal'. 그 다음 'increase volume by 10%'처럼 물어보면 계산해 드려요."
            return jsonify({"reply": tone(guidance, role),
                            "rationale": tone("EBCT = V/Q. 기준이 있어야 변화량을 계산할 수 있어요.", role),
                            "calc": {"minutes": _num(compute_from_used(used)), "used": used}}), 200

        op = (parsed.get("op") or "").lower()

        if op == "set_baseline":
            q = parsed.get("query") or user_msg
            res = compute_ebct(q)
            if not isinstance(res, dict) or res.get("minutes") is None:
                return jsonify({"reply": "입력을 이해하지 못했어요. 예: 'flow 800 gpm, bed volume 9600 gal'."}), 200
            used_new = (res.get("detail") or {}).get("units_normalized") or {}
            reply = f"기준 설정 완료. EBCT ≈ {_num(res['minutes'])} min."
            rationale = f"방법: {res.get('via','-')} · 공식: EBCT = V/Q"
            return jsonify({"reply": tone(reply, role), "rationale": tone(rationale, role),
                            "calc": {"minutes": _num(res["minutes"]), "used": used_new}}), 200

        if op == "what_if":
            if not used:
                return jsonify({"reply": tone("아직 기준이 없어요. 먼저 수치를 알려주세요 (예: flow 800 gpm, volume 9600 gal).", role)}), 200
            new_used = apply_changes(used, parsed.get("changes"))
            if not new_used:
                return jsonify({"reply": tone("변경을 적용할 수 없어요. D/H는 %, flow/volume은 gpm/gal 또는 %로 요청해 주세요.", role)}), 200
            old = compute_from_used(used)
            new = compute_from_used(new_used)
            if new is None:
                return jsonify({"reply": tone("계산에 필요한 값이 부족해요.", role)}), 200

            diff = ((new - old) / old) * 100.0 if (old not in (None, 0)) else None
            reply = f"EBCT가 {_num(old)} → {_num(new)} min" + (f" ({_num(diff)}%)." if diff is not None else ".")
            changed = parsed.get("changes")[0].get("target") if parsed.get("changes") else ""
            rationale = ("근거: EBCT = V/Q. " +
                         ("Flow 증가 → 분모↑ ⇒ EBCT↓." if "flow" in changed else
                          "Volume 증가 → 분자↑ ⇒ EBCT↑." if "volume" in changed else
                          "Dims 변경 시 EBCT ∝ D²·H/Q."))
            # 역할별 대안 제안
            advice = add_advice(changed, role)
            if advice:
                reply = (f"{reply}  대신 이런 방향은 어때요? {advice}"
                         if role == "designer" else f"{reply}  Alternatives: {advice}")

            return jsonify({"reply": tone(reply, role),
                            "rationale": tone(rationale, role),
                            "calc": {"minutes": _num(new), "used": new_used}}), 200

        if op == "solve_for":
            t = parsed.get("ebct_min")
            target = (parsed.get("target") or "").lower()
            if not t:
                return jsonify({"reply": tone("목표 EBCT(분)를 알려주세요.", role)}), 200
            if target == "volume":
                Q = used.get("flow_gpm")
                if Q is None:
                    return jsonify({"reply": tone("필요한 유량(Q gpm) 기준이 없어요.", role)}), 200
                Vreq = float(t) * float(Q)
                reply = f"목표 EBCT {t} min 달성을 위해 필요한 Volume ≈ {_num(Vreq)} gal."
                rationale = "V = EBCT × Q (EBCT = V/Q)."
                return jsonify({"reply": tone(reply, role), "rationale": tone(rationale, role),
                                "calc": {"minutes": _num(t), "used": {**used, "volume_gal": Vreq}}}), 200
            if target == "flow":
                V = used.get("volume_gal")
                if V is None:
                    return jsonify({"reply": tone("필요한 체적(V gal) 기준이 없어요.", role)}), 200
                Qreq = float(V) / float(t)
                reply = f"목표 EBCT {t} min 달성을 위한 Flow ≈ {_num(Qreq)} gpm."
                rationale = "Q = V / EBCT (EBCT = V/Q)."
                return jsonify({"reply": tone(reply, role), "rationale": tone(rationale, role),
                                "calc": {"minutes": _num(t), "used": {**used, "flow_gpm": Qreq}}}), 200
            return jsonify({"reply": tone("volume로 풀지, flow로 풀지 알려주세요.", role)}), 200

        if op == "ask_effect":
            tgt = (parsed.get("target") or "").lower()
            if tgt in ("volume", "bed volume"):
                return jsonify({"reply": tone("Volume을 키우면 EBCT는 선형으로 증가합니다.", role),
                                "rationale": tone("EBCT = V/Q, V↑ ⇒ EBCT↑", role)}), 200
            if tgt in ("flow", "gpm"):
                return jsonify({"reply": tone("Flow를 키우면 EBCT는 감소합니다.", role),
                                "rationale": tone("EBCT = V/Q, Q↑ ⇒ EBCT↓", role)}), 200
            if tgt == "diameter":
                return jsonify({"reply": tone("지름을 10% 늘리면 EBCT는 대략 21% 증가합니다.", role),
                                "rationale": tone("V ∝ D²·H ⇒ EBCT ∝ D²·H/Q", role)}), 200
            if tgt in ("height", "bed height"):
                return jsonify({"reply": tone("Bed height 10% 증가 → EBCT 약 10% 증가.", role),
                                "rationale": tone("V ∝ H ⇒ EBCT ∝ H", role)}), 200
            return jsonify({"reply": tone("EBCT = V/Q; 어떤 변수를 바꾸려는지 알려주세요.", role)}), 200

        return jsonify({"reply": tone("해석이 어려웠어요. 수치를 주시거나, %/gpm/gal로 변경 폭을 알려주세요.", role)}), 200

    except Exception as e:
        tb = traceback.format_exc()
        print("[/api/chat] error:", e, "\n", tb, flush=True)
        return jsonify({"error": str(e)}), 500

# === RUN SERVER ===
if __name__ == "__main__":
    print("RUN: starting Flask...", flush=True)
    app.run("0.0.0.0", int(os.environ.get("PORT", 5001)), debug=True)