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
