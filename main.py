import time
import sys
from threading import Thread

from Backend import peer_node as pn
import socket

from flask import Flask, render_template, app


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect(('10.254.254.254', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


def check_flags():
    # Ignoriere das erste Argument (Skriptname)
    args = sys.argv[1:]

    # Wenn keine Argumente übergeben wurden, gib False zurück
    if not args:
        return False

    # Wenn genau ein Argument "-b" ist, gib True zurück
    if len(args) == 1 and args[0] == "-b":
        return 1

    if len(args) == 1 and args[0] == "-s":
        return 2

    # In allen anderen Fällen (z. B. andere Argumente), gib False zurück
    return 0


def main():
    ip = get_ip()
    print(ip)
    # node of this peer
    match check_flags():
        case 1:
            node = pn.PeerNode(pn.BOOTSTRAP[0], port=pn.BOOTSTRAP[1], super_peer=True)
        case 2:
            node = pn.PeerNode(ip, port=0, super_peer=True)
        # DEFAULT
        case _:
            node = pn.PeerNode(ip, port=0)

    # start node
    node.start()

    # bootstrap node
    node.do_bootstrap()

    if node.bootstrap:
        while True:
            time.sleep(10)
    else:
        while len(node.peers) < 5:
            node.request_peers()
            time.sleep(1)

def start_background_thread():
    Thread(target=main, daemon=True).start()


app = Flask(__name__)
start_background_thread()
# app.run(debug=True)

@app.route("/")
def home():
    return render_template("index.html")  # Renders templates/index.html


if __name__ == "__main__":
    app.run(debug=True)