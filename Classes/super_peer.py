import socket
import threading
import json
import hashlib
import time
from datetime import datetime
import uuid
import random

from Classes.peer_node import PeerNode


class SuperPeer(PeerNode):
    def __init__(self, host, port, board):
        super().__init__(host, port)
        self.board = board

    def get_board(self):
        return self.board

    def become_peernode_and_delete_board(self):
        del self.board
        # Convert back to a regular Peer_node
        peer_node = PeerNode(self.host, self.port)
        # Copy relevant attributes from the current Super_Peer to the new Peer_node
        peer_node.node_id = self.node_id
        peer_node.peers = self.peers
        peer_node.data_store = self.data_store
        peer_node.server_socket = self.server_socket
        peer_node.running = self.running

        # Stop the current Super_Peer without closing connections
        self.running = False
        self.server_socket = None  # Prevent closing the socket here

        print(f"Super_Peer {self.node_id} converted back to Peer_node.")
        return peer_node
