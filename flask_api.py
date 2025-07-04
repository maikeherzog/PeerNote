import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from Backend.peer_node import PeerNode
from Backend.Board import Board  

app = Flask(__name__)
CORS(app, origins=["http://localhost:8080"])

# Diesen PeerNode müssen wir referenzieren
peer_node: PeerNode = None  # wird später gesetzt

@app.route('/set_super_peer', methods=['POST'])
def set_super_peer():
    data = request.get_json()
    title = data.get("title")
    keywords = data.get("keywords", [])

    if not peer_node.super_peer:
        peer_node.set_super_peer(title, keywords)
        #peer_node.super_peer = True
        peer_node.board = peer_node.board or Board(title, set(keywords))
        print(f"[FLASK] Peer wurde Superpeer mit Board '{title}' und Keywords {keywords}")
        return jsonify({"status": "success", "super_peer": True}), 200
    else:
        return jsonify({"status": "already_super_peer"}), 400

@app.route('/save_card', methods=['POST'])
def save_card():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data received"}), 400

    # Zielordner (z. B. im Projektordner unter "data")
    os.makedirs("data", exist_ok=True)
    file_path = os.path.join("data", "cards.json")

    # Vorherigen Inhalt laden (falls Datei existiert)
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            cards = json.load(f)
    else:
        cards = []

    # Neue Karte anhängen
    cards.append(data)

    # Datei aktualisieren
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)

    return jsonify({"status": "saved"}), 200