from Backend.peer_node import PeerNode
from Backend.config import BOOTSTRAP
import time
import webbrowser
import subprocess
import os
import sys

# IP-Adresse und Port des Bootstrap-Nodes
BOOTSTRAP_IP, BOOTSTRAP_PORT = BOOTSTRAP

def start_frontend():
    # Webserver im Hauptverzeichnis starten (eine Ebene höher)
    main_path = os.path.abspath("../PeerNote")
    
    try:
        print(f"[INFO] Starte Webserver in: {main_path}")
        process = subprocess.Popen(
            [sys.executable, "-m", "http.server", "8080"], 
            cwd=main_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        time.sleep(2)
        
        if process.poll() is None:
            print("[INFO] Webserver erfolgreich gestartet auf Port 8080")
            # Browser öffnen - Frontend ist dann unter /bulletin_board_frontend/ erreichbar
            webbrowser.open("http://localhost:8080/bulletin_board_frontend/")
        else:
            stdout, stderr = process.communicate()
            print(f"[ERROR] Webserver konnte nicht gestartet werden:")
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
            
    except Exception as e:
        print(f"[ERROR] Fehler beim Starten des Webservers: {e}")

def main():
    node = PeerNode(BOOTSTRAP_IP, BOOTSTRAP_PORT)
    node.start()
    print(f"[BOOTSTRAP NODE] Running at {BOOTSTRAP_IP}:{BOOTSTRAP_PORT}")
    start_frontend()

    # Hier könnt ihr eine Endlosschleife oder eine manuelle Stop-Möglichkeit einbauen
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[BOOTSTRAP NODE] Stopping...")
        node.stop()

if __name__ == "__main__":
    main()
