from Classes.Peer_node import Peer_node
import time

# Lokale IP des aktuellen Rechners
MY_IP = "--eigene-ip--"  # <- IP von diesem Rechner
MY_PORT = 8005           # <- einen freien Port wählen

# IP und Port des Bootstrap-Nodes (Rechner 1)
BOOTSTRAP_IP = "--bootstrap-ip--"
BOOTSTRAP_PORT = 8001

def main():
    node = Peer_node(MY_IP, MY_PORT)
    node.start()
    print(f"[PEER NODE] Started at {MY_IP}:{MY_PORT}")

    time.sleep(1)  # Kleiner Delay für Stabilität

    if node.connect_to_peer(BOOTSTRAP_IP, BOOTSTRAP_PORT):
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
