from Backend.peer_node import PeerNode
from Backend.config import BOOTSTRAP
import time
import webbrowser
import subprocess
import os

# IP-Adresse und Port des Bootstrap-Nodes
BOOTSTRAP_IP, BOOTSTRAP_PORT = BOOTSTRAP

def start_frontend():
    # Starte einfachen Webserver im Hintergrund
    frontend_path = os.path.abspath("./bulletin_board_frontend")
    subprocess.Popen(["python", "-m", "http.server", "8080"], cwd=frontend_path)

    # Öffne Browser
    webbrowser.open("http://localhost:8080")

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
