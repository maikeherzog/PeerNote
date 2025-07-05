import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from Backend.peer_node import PeerNode
from Backend.Board import Board
import time
import uuid  

app = Flask(__name__)
CORS(app, origins=["http://localhost:8080"])

# Diesen PeerNode müssen wir referenzieren
peer_node: PeerNode = None  # wird später gesetzt

@app.route('/set_super_peer', methods=['POST'])
def set_super_peer():
    data = request.get_json()
    title = data.get("title")
    keywords = data.get("keywords", [])
    
    if peer_node is None:
        return jsonify({"error": "PeerNode not initialized"}), 500
    
    if not peer_node.super_peer:
        # First board - become super peer
        peer_node.set_super_peer(title, keywords)
        peer_node.board = peer_node.board or Board(title, set(keywords))
        print(f"[FLASK] Peer wurde Superpeer mit Board '{title}' und Keywords {keywords}")
        return jsonify({"status": "success", "super_peer": True, "first_board": True}), 200
    else:
        # Additional boards - register them too
        peer_node.set_super_peer(title, keywords)
        print(f"[FLASK] Additional board registered: '{title}' und Keywords {keywords}")
        return jsonify({"status": "success", "super_peer": True, "additional_board": True}), 200
    
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

@app.route('/update_card', methods=['PUT'])
def update_card():
    data = request.get_json()
    card_id = data.get("id")

    if not card_id:
        return jsonify({"error": "Missing card ID"}), 400

    file_path = os.path.join("data", "cards.json")

    if not os.path.exists(file_path):
        return jsonify({"error": "cards.json not found"}), 404

    with open(file_path, "r", encoding="utf-8") as f:
        cards = json.load(f)

    # Suche nach der Karte anhand der ID und ersetze sie
    updated = False
    for i, card in enumerate(cards):
        if card["id"] == card_id:
            cards[i] = data
            updated = True
            break

    if not updated:
        return jsonify({"error": "Card not found"}), 404

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)

    return jsonify({"status": "updated"}), 200

@app.route('/delete_card/<int:card_id>', methods=['DELETE'])
def delete_card(card_id):
    file_path = os.path.join("data", "cards.json")

    if not os.path.exists(file_path):
        return jsonify({"error": "cards.json not found"}), 404

    with open(file_path, "r", encoding="utf-8") as f:
        cards = json.load(f)

    # Filtere Karte heraus
    new_cards = [card for card in cards if card["id"] != card_id]

    if len(cards) == len(new_cards):
        return jsonify({"error": "Card not found"}), 404

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(new_cards, f, ensure_ascii=False, indent=2)

    return jsonify({"status": "deleted"}), 200

@app.route('/peer_info', methods=['GET'])
def get_peer_info():
    if peer_node is None:
        return jsonify({"error": "PeerNode not initialized"}), 500

    return jsonify({
        "host": peer_node.get_host(),
        "port": peer_node.get_port()
    })

@app.route('/register_board', methods=['POST'])
def register_board():
    """Register a new board with the bootstrap peer"""
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data received"}), 400
    
    # Extract board information
    board_id = data.get("board_id")
    peer_id = data.get("peer_id")
    board_title = data.get("board_title")
    keywords = data.get("keywords", [])
    peer_host = data.get("peer_host")
    peer_port = data.get("peer_port")
    
    # Validate required fields
    if not board_id or not peer_id or not board_title:
        return jsonify({"error": "Missing required fields: board_id, peer_id, board_title"}), 400
    
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    file_path = os.path.join("data", "boards.json")
    
    # Load existing boards (if file exists)
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            boards = json.load(f)
    else:
        boards = []
    
    # Create new board entry
    new_board = {
        "board_id": board_id,
        "peer_id": peer_id,
        "board_title": board_title,
        "keywords": keywords,
        "peer_host": peer_host,
        "peer_port": peer_port,
        "created_at": time.time(),  # timestamp
        "status": "active"
    }
    
    # Check if board already exists
    for board in boards:
        if board["board_id"] == board_id:
            return jsonify({"error": "Board already exists"}), 409
    
    # Add new board to list
    boards.append(new_board)
    
    # Save updated boards list
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(boards, f, ensure_ascii=False, indent=2)
    
    print(f"[BOOTSTRAP] New board registered: {board_title} (ID: {board_id}) by peer {peer_id}")
    
    return jsonify({"status": "board_registered", "board_id": board_id}), 200

@app.route('/get_boards', methods=['GET'])
def get_boards():
    """Get list of all registered boards"""
    file_path = os.path.join("data", "boards.json")
    
    if not os.path.exists(file_path):
        return jsonify({"boards": []}), 200
    
    with open(file_path, "r", encoding="utf-8") as f:
        boards = json.load(f)
    
    return jsonify({"boards": boards}), 200

@app.route('/search_boards', methods=['GET'])
def search_boards():
    """Search boards by keywords"""
    keyword = request.args.get('keyword', '').lower()
    
    if not keyword:
        return jsonify({"error": "No keyword provided"}), 400
    
    file_path = os.path.join("data", "boards.json")
    
    if not os.path.exists(file_path):
        return jsonify({"boards": []}), 200
    
    with open(file_path, "r", encoding="utf-8") as f:
        boards = json.load(f)
    
    # Search for boards matching the keyword
    matching_boards = []
    for board in boards:
        # Search in title and keywords
        if (keyword in board["board_title"].lower() or 
            any(keyword in kw.lower() for kw in board["keywords"])):
            matching_boards.append(board)
    
    return jsonify({"boards": matching_boards}), 200

@app.route('/unregister_board', methods=['DELETE'])
def unregister_board():
    """Remove a board via P2P communication"""
    data = request.get_json()
    board_title = data.get("board_title")
    
    if not board_title:
        return jsonify({"error": "Missing board_title"}), 400
    
    if peer_node is None:
        return jsonify({"error": "PeerNode not initialized"}), 500
    
    # Send unregistration to bootstrap via P2P
    if not peer_node.bootstrap:
        peer_node.send_board_unregistration_to_bootstrap(board_title)
    
    return jsonify({"status": "unregistration_sent"}), 200
