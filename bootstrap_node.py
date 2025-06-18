from Classes.Peer_node import Peer_node
import time
import webbrowser
import subprocess
import os

# IP-Adresse und Port des Bootstrap-Nodes
BOOTSTRAP_IP = "--bootstrap-ip--"  # Hier die tatsächliche IP-Adresse eintragen
BOOTSTRAP_PORT = 8001

def start_frontend():
    # Starte einfachen Webserver im Hintergrund
    frontend_path = os.path.abspath("./bulletin_board_frontend")
    subprocess.Popen(["python", "-m", "http.server", "8080"], cwd=frontend_path)

    # Öffne Browser
    webbrowser.open("http://localhost:8080")

def main():
    node = Peer_node(BOOTSTRAP_IP, BOOTSTRAP_PORT)
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
