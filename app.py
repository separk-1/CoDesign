import os
from flask import Flask, request, jsonify, send_from_directory
from calculator import compute_ebct 

app = Flask(__name__, static_folder='.')

@app.get("/ping")
def ping():
    return "pong", 200

@app.get("/")
def index():
    return send_from_directory(".", "index.html")

@app.post("/api/calculate")
def calculate():
    try:
        data = request.get_json(force=True) or {}
        query = (data.get("query") or "").strip()
        if not query:
            return jsonify({"ok": False, "error": "Missing 'query'"}), 400
        return jsonify(compute_ebct(query)), 200
    except Exception as e:
        print("[/api/calculate] error:", e)
        return jsonify({"ok": False, "error": "Internal Server Error"}), 500

if __name__ == "__main__":
    app.run("0.0.0.0", int(os.environ.get("PORT", 5001)), debug=True)
