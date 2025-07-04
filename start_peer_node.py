from Backend.peer_node import PeerNode
from Backend.config import BOOTSTRAP, LOCAL
import time
import webbrowser
import subprocess
import os

# Lokale IP des aktuellen Rechners
MY_IP = "192.168.2.101"  # <- IP von diesem Rechner
MY_PORT = 8005           # <- einen freien Port wählen
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
    start_frontend()

    time.sleep(1)  # Kleiner Delay für Stabilität

    print(f"node.do_bootstrap():" , node.do_bootstrap())

    if node.do_bootstrap():
        print(f"[PEER NODE] Connected to Bootstrap at {BOOTSTRAP_IP}:{BOOTSTRAP_PORT}")
    else:
        print("[PEER NODE] Failed to connect to Bootstrap Node")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[PEER NODE] Stopping...")
        node.stop()

if __name__ == "__main__":
    main()
