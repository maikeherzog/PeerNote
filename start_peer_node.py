from Backend.peer_node import PeerNode
from Backend.config import BOOTSTRAP, LOCAL
from Backend.Board import Board
import threading
from flask_api import app, peer_node as flask_peer_node  
import time
import webbrowser
import subprocess
import os
import json

# Lokale IP des aktuellen Rechners
#MY_IP = "192.168.2.101"  # <- IP von diesem Rechner
#MY_PORT = 8005           # <- einen freien Port wählen
MY_IP, MY_PORT = LOCAL # Tuple für die IP und den Port

# IP und Port des Bootstrap-Nodes (Rechner 1)
BOOTSTRAP_IP, BOOTSTRAP_PORT = BOOTSTRAP

def start_frontend():
    # Starte einfachen Webserver im Hintergrund
    frontend_path = os.path.abspath("./bulletin_board_frontend")
    subprocess.Popen(["python", "-m", "http.server", "8080"], cwd=frontend_path)

    # Öffne Browser
    webbrowser.open("http://localhost:8080")

def main():
    node = PeerNode(MY_IP, MY_PORT)
    node.start()
    print(f"[PEER NODE] Started at {MY_IP}:{MY_PORT}")
    # Setze PeerNode-Referenz für Flask
    import flask_api
    flask_api.peer_node = node

    # Starte Flask in eigenem Thread
    flask_thread = threading.Thread(target=lambda: app.run(port=5000, debug=True, use_reloader=False))
    flask_thread.daemon = True
    flask_thread.start()

    start_frontend()

    time.sleep(1)  # Kleiner Delay für Stabilität

    print(f"node.do_bootstrap():" , node.do_bootstrap())

    if node.do_bootstrap():
        print(f"[PEER NODE] Connected to Bootstrap at {BOOTSTRAP_IP}:{BOOTSTRAP_PORT}")
        print(f"Node Board id is: {node.board.board_id if node.board else 'No Board'}")

        #node.board_request(BOOTSTRAP_IP, BOOTSTRAP_PORT, keywords=set())
        node.issue_search_request([])
        node.super_peer = True  # Setze den PeerNode als Super Peer
        node.board = "fc64983c-5e1f-424e-836d-c612b9ad5de9"

        try:
            with open("data/received_boards.json", "r", encoding="utf-8") as f:
                boards = json.load(f)
                print(f"[PEER NODE] Loaded boards from data/received_boards.json: {boards}")
        except FileNotFoundError:
            print("[PEER NODE] No boards found in data/received_boards.json")

        for board in boards:
            peer_host = board.get("peer_host")
            peer_port = board.get("peer_port")
            if peer_host and peer_port:
                print(f"[PEER NODE] Sending data request to {peer_host}:{peer_port}")
                node.send_data_request(peer_host, peer_port, 'My Awesome Board')
            else:
                print("[PEER NODE] No valid peer host or port found in board data")

    else:
        print("[PEER NODE] Failed to connect to Bootstrap Node")

    print(f"[PEER NODE] Peers: {node.super_peer}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[PEER NODE] Stopping...")
        node.stop()


if __name__ == "__main__":
    main()
