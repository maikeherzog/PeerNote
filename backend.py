import socket
import threading
import json
import hashlib
import time
from datetime import datetime
import uuid
import random

from Classes.peer_node import PeerNode

### Bootstrapping
def join_network(new_node):
  ttl = 3

  while True:
    node = random.choice(bootstrapping_nodes)
    if new_node.connect_to_peer(node.get_host(), node.get_port()):
      break;

  print(len(new_node.get_peers()))

  for node in new_node.get_peers():
    new_node.send_message_to_peer(node, 'ping', {'path': new_node.get_id(), 'ttl': ttl})

  print(len(new_node.get_peers()))
  print(new_node.get_peers())

def main():
    global bootstrapping_nodes

    ### Base network
    node1 = PeerNode("127.0.0.1", 8001, super_peer=True)
    node2 = PeerNode("127.0.0.1", 8002, super_peer=True)
    node3 = PeerNode("127.0.0.1", 8003, super_peer=True)
    node4 = PeerNode("127.0.0.1", 8004, super_peer=True)
    node5 = PeerNode("127.0.0.1", 8005, super_peer=True)

    node1.start()
    node2.start()
    node3.start()
    node4.start()
    node5.start()

    time.sleep(1) # Give servers a moment to start
    # Form ring-like peer network
    node1.connect_to_peer("127.0.0.1", 8002)
    print(node1.peers)
    # # time.sleep(1)
    node2.connect_to_peer("127.0.0.1", 8003)
    # time.sleep(1)
    node3.connect_to_peer("127.0.0.1", 8004)
    time.sleep(1)
    node4.connect_to_peer("127.0.0.1", 8005)
    time.sleep(1)
    node5.connect_to_peer("127.0.0.1", 8001)

    bootstrapping_nodes = [node1, node2, node3, node4, node5]
    time.sleep(3)
    print("stopping")
    return

    # Join network
    node6 = PeerNode("127.0.0.1", 8018)
    # join_network(node6)

    print("Stopping nodes...")
    node1.stop()
    node2.stop()
    node3.stop()
    node4.stop()
    node5.stop()
    node6.stop()

if __name__ == "__main__":
    main()