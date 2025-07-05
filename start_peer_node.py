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
import sys

# Lokale IP des aktuellen Rechners
MY_IP, MY_PORT = LOCAL # Tuple für die IP und den Port

# IP und Port des Bootstrap-Nodes (Rechner 1)
BOOTSTRAP_IP, BOOTSTRAP_PORT = BOOTSTRAP

def start_frontend():
    # Webserver im Hauptverzeichnis starten (eine Ebene höher)
    main_path = os.path.abspath("../PeerNote")
    
    # Prüfen ob der Pfad existiert
    if not os.path.exists(main_path):
        print(f"[ERROR] Hauptverzeichnis nicht gefunden: {main_path}")
        return
    
    # Prüfen ob bulletin_board_frontend existiert
    frontend_path = os.path.join(main_path, "bulletin_board_frontend")
    if not os.path.exists(frontend_path):
        print(f"[ERROR] Frontend-Verzeichnis nicht gefunden: {frontend_path}")
        return
    
    # Liste der Ports zum Ausprobieren
    ports = [8080, 8081, 8082, 8083, 8084, 8085]
    
    for port in ports:
        try:
            print(f"[INFO] Versuche Webserver auf Port {port} zu starten...")
            # Webserver starten
            process = subprocess.Popen(
                ["python", "-m", "http.server", str(port)], 
                cwd=main_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Kurz warten, damit der Server startet
            time.sleep(2)
            
            # Prüfen ob der Prozess noch läuft
            if process.poll() is None:
                print(f"[INFO] Webserver erfolgreich gestartet auf Port {port}")
                # Browser öffnen - Frontend ist dann unter /bulletin_board_frontend/ erreichbar
                webbrowser.open(f"http://localhost:{port}/bulletin_board_frontend/")
                return  # Erfolgreich gestartet, Funktion verlassen
            else:
                # Fehler beim Starten - nächsten Port probieren
                stdout, stderr = process.communicate()
                if "Address already in use" in stderr.decode():
                    print(f"[WARNING] Port {port} ist bereits belegt, probiere nächsten...")
                    continue
                else:
                    print(f"[ERROR] Unerwarteter Fehler auf Port {port}:")
                    print(f"STDERR: {stderr.decode()}")
                    
        except Exception as e:
            print(f"[ERROR] Fehler beim Starten des Webservers auf Port {port}: {e}")
            continue
    
    # Alle Ports fehlgeschlagen
    print("[ERROR] Konnte Webserver auf keinem Port starten!")
    print("[INFO] Bitte starten Sie den Webserver manuell:")
    print("1. Öffnen Sie ein neues Terminal")
    print("2. Wechseln Sie ins Hauptverzeichnis")
    print("3. Führen Sie aus: python -m http.server 8080")
    print("4. Öffnen Sie: http://localhost:8080/bulletin_board_frontend/")

def main():
    try:
        # Peer Node starten
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
        
        # Frontend starten
        start_frontend()
        
        # Kleiner Delay für Stabilität
        time.sleep(1)
        
        # Bootstrap-Verbindung
        print(f"node.do_bootstrap(): {node.do_bootstrap()}")
        
        if node.do_bootstrap():
            print(f"[PEER NODE] Connected to Bootstrap at {BOOTSTRAP_IP}:{BOOTSTRAP_PORT}")
            print(f"Node Board id is: {node.board.board_id if node.board else 'No Board'}")
            # node.board_request(BOOTSTRAP_IP, BOOTSTRAP_PORT, keywords=set())
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
        
        # Hauptschleife
        print("[INFO] Drücken Sie Ctrl+C zum Beenden")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n[PEER NODE] Stopping...")
        try:
            node.stop()
        except:
            pass
        print("[INFO] Programm beendet")
        
    except Exception as e:
        print(f"[ERROR] Unerwarteter Fehler: {e}")
        try:
            node.stop()
        except:
            pass

if __name__ == "__main__":
    main()