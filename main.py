import time

from Backend import peer_node as pn
import socket


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


import sys

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


# node of this peer
match check_flags():
    case 1:
        node = pn.PeerNode(pn.BOOTSTRAP[0], port=pn.BOOTSTRAP[1], super_peer=True)
    case 2:
        node = pn.PeerNode(get_ip(), port=0, super_peer=True)
    # DEFAULT
    case _:
        node = pn.PeerNode(get_ip(), port=0)


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