import socket
import struct
import threading
import json
import hashlib
import time
from datetime import datetime
import uuid
import random

from Classes.Board import Board
from Classes.peer_message_handler import *
from message_type import MessageType


class PeerNode:
    def __init__(self, host, port, super_peer: bool = False, board: Board = None):
        self.host = host
        self.port = port

        # max number of active tcp connections
        self.max_connections = 5

        self.max_total_conn = 10

        # combined_host_port = f"{host}:{port}"
        # self.node_id=hashlib.sha256(combined_host_port.encode()).hexdigest() ## Id of node is hash of ip and port

        # node id, collision probability is close to 0
        self.node_id = str(uuid.uuid4())

        # peers of this peer
        self.peers = {}
        self.data_store = {}
        self.server_socket = None
        self.running = False

        # super peer section
        self.super_peer = super_peer
        self.board = board
        print(f"Node {self.node_id} initialized at {self.host}:{self.port}")

    ### Node Properties
    def get_id(self):
        return self.node_id

    def get_host(self):
        return self.host

    def get_port(self):
        return self.port

    def get_peers(self):
        return self.peers

    ### Connection to and communication with other peers

    def start(self):
        """Starts the node, listening for incoming connections."""

        self.server_socket: socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(self.max_connections)
        self.running: bool = True
        print(f"Node {self.node_id} listening on {self.host}:{self.port}")

        # Start a new thread to continuously accept connections
        threading.Thread(target=self._accept_connections, daemon=True).start()

    def _accept_connections(self):
        """Internal method to accept incoming connections."""
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                print(f"Incoming connection from {addr}")
                # Handle connection in a new thread
                threading.Thread(target=self._handle_client_connection, args=(conn, addr), daemon=True).start()
            except Exception as e:
                if self.running:
                    print(f"Error accepting connection: {e}")
                break

    def _handle_client_connection(self, conn, addr):
        """Handles a single client connection (a peer)."""
        cont = True

        data = receive_packet(conn)
        while data is not None:
            try:
                # data = receive_packet(conn)

                # transform into a readable dict
                peer_data: dict = json.loads(data)

                try:
                    msg_type = MessageType(peer_data.get("type", "error"))

                except ValueError as e:
                    print(e)
                    msg_type = MessageType.ERROR

                match msg_type:
                    case MessageType.TEXT:
                        print("Received a text message.")
                        # handle text
                    case MessageType.CONNECT:
                        print("Peer wants to connect.")
                        self.send_close(conn)
                        cont = False
                        # handle connection
                    case MessageType.DATA_REQUEST:
                        print("Data request received.")
                        # send requested data
                    case MessageType.DATA_RESPONSE:
                        print("Got data response.")
                        # process incoming data
                    case MessageType.DATA_UPDATE:
                        print("Data update received.")
                        # update local data
                    case MessageType.PING:
                        print("Received PING.")
                        # reply with PONG
                    case MessageType.PONG:
                        print("Received PONG.")
                        # maybe update liveness
                    case MessageType.GET_PEERS:
                        print("Peer requests peer list.")
                        # send known peers
                    case MessageType.PEER_LIST:
                        print("Got peer list.")
                        # add peers
                    case MessageType.CLOSE:
                        print("Connection close requested.")
                        conn.shutdown(socket.SHUT_RDWR)
                        conn.close()
                        cont = False
                        # cleanup and close
                    case MessageType.ERROR:
                        print("Received unknown or malformed message.")
                        # maybe log or ignore


            except Exception as e:
                print(f"Error handling client connection from {addr}: {e}")
                cont = False
                conn.close()

            # sanity check whether is closed, this can happen whenever
            if conn.fileno() < 0:
                # break the while loop and therefore close connection entirely
                break
            else:
                data = receive_packet(conn)

    def send_close(self, conn: socket):
        data = create_packet(MessageType.CLOSE, self.node_id, {})
        send_packet(data, conn)
        conn.close()

    def connect_to_peer(self, peer_host, peer_port):
        """Connects to another peer node."""
        if (peer_host, peer_port) == (self.host, self.port):
            print("Cannot connect to self.")
            return False

        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect((peer_host, peer_port))

            # Send our own node info to the peer
            data = create_packet(msg_type=MessageType.CONNECT, node_id=str(self.node_id),
                                 payload={'node_id': str(self.node_id), 'host': self.host, 'port': self.port})

            # send connection request to (not yet) peer
            send_packet(data, conn)

            # expect other package
            receive_packet(conn)

            conn.close()
            return True
        except Exception as e:
            print(f"Error while sending: {e}")
            return False

    def _listen_to_peer(self, peer_id, sock):
        """Listens for messages from a specific connected peer."""
        try:
            while True:
                # was passiert wenn die daten größer sind als 4096????????????????
                data = sock.recv(4096)
                if not data:
                    print(f"Peer {peer_id} disconnected during listen.")
                    #self.remove_peer(peer_id)                                  #### ???
                    break
                message = json.loads(data.decode('utf-8'))
                self.process_message(peer_id, message)
        except Exception as e:
            print(f"Error listening to peer {peer_id}: {e}")
            self.remove_peer(peer_id)

    def add_peer(self, peer_id, socket_obj, address_tuple):
        """Adds a new peer to the node's peer list."""
        if peer_id not in self.peers:
            self.peers[peer_id] = (socket_obj, address_tuple)
            print(f"Added peer: {peer_id} from {address_tuple}")
        else:
            print(f"Peer {peer_id} already in peer list.")

    def remove_peer(self, peer_id):
        """Removes a peer from the node's peer list."""
        if peer_id in self.peers:
            socket_obj, _ = self.peers[peer_id]
            try:
                socket_obj.close()
            except Exception as e:
                print(f"Error closing socket for peer {peer_id}: {e}")
            del self.peers[peer_id]
            print(f"Removed peer: {peer_id}")

    def send_message_to_peer(self, peer_id, message_type, content=None):
        """Sends a message to a specific peer."""
        if peer_id in self.peers:
            sock, _ = self.peers[peer_id]
            try:
                full_message = {'sender_id': str(self.node_id), 'type': message_type, 'content': content}
                sock.sendall(json.dumps(full_message).encode('utf-8'))
                print(f"Sent '{message_type}' to {peer_id}")
                time.sleep(2)
            except Exception as e:
                print(f"Error sending message to {peer_id}: {e}")
                self.remove_peer(peer_id)
        else:
            print(f"Peer {peer_id} not found in peer list.")

    def broadcast_message(self, message_type, content=None):
        """Sends a message to all connected peers."""
        print(f"Broadcasting message: Type={message_type}, Content={content}")
        for peer_id in list(self.peers.keys()):  # Use list to avoid issues if peers are removed during iteration
            self.send_message_to_peer(peer_id, message_type, content)

    def process_message(self, sender_id, message):
        """Processes an incoming message from a peer."""
        message_type = message.get('type')
        content = message.get('content')
        print(f"Node {self.node_id} received message from {sender_id}: Type='{message_type}', Content='{content}'")

        match message_type:
            case 'text_message':
                print(f"  > Text message: {content}")
            case 'data_request':
                key = content.get('key')
                if key in self.data_store:
                    self.send_message_to_peer(sender_id, 'data_response', {'key': key, 'value': self.data_store[key]})
                else:
                    self.send_message_to_peer(sender_id, 'data_response',
                                              {'key': key, 'value': None, 'error': 'not_found'})
            case 'data_update':
                key = content.get('key')
                value = content.get('value')

                # check if key is in data_store
                if key in self.data_store.keys():
                    self.data_store[key] = value
                    print(f"  > Stored data: {key} = {value}")
                # Optionally, rebroadcast the update to other peers
                # self.broadcast_message('data_update', content)
            case 'get_peers':
                # Send back a list of this node's known peers (host, port)
                peer_addresses = [peer_info[1] for peer_info in self.peers.values()]
                self.send_message_to_peer(sender_id, 'peer_list', {'peers': peer_addresses})
            case 'peer_list':
                # Add newly discovered peers to our list
                new_peers = content.get('peers', [])
                for peer_host, peer_port in new_peers:
                    if (peer_host, peer_port) != (self.host, self.port) and (peer_host, peer_port) not in [p[1] for p in
                                                                                                           self.peers.values()]:
                        print(f"Attempting to connect to new peer: {peer_host}:{peer_port}")
                        self.connect_to_peer(peer_host, peer_port)
            case 'ping':
                new_ttl = content.get('ttl') - 1
                new_path = content.get('path') + f", {self.node_id}"

                if new_ttl > 0:
                    ### Send ping to all addresses which are not included in ping path
                    ids_of_own_peers = set([str(key) for key in self.peers.keys()])
                    ids_of_peers_in_ping_path = set(content.get('path').split(", "))

                    address_ids = ids_of_own_peers.difference(ids_of_peers_in_ping_path)
                    addresses = [key for key, value in self.peers.items() if str(key) in address_ids]
                    if bool(addresses):
                        for send_to in addresses:
                            self.send_message_to_peer(send_to, 'ping', {'path': new_path, 'ttl': new_ttl})
                        print(f"Ping path: {new_path}")
                    else:
                        peer_addresses = [peer_info[1] for peer_info in self.peers.values()]
                        self.send_message_to_peer(sender_id, 'pong',
                                                  {'path': content.get('path'), 'peers': peer_addresses})
                        print(f"End of ping path: {new_path}")
                else:
                    peer_addresses = [peer_info[1] for peer_info in self.peers.values()]
                    peer_id = content.get('path').split(", ").pop(-1)
                    self.send_message_to_peer(sender_id, 'pong', {'path': content.get('path'), 'peers': peer_addresses})
                    print(f"End of ping path: {content.get('path')}, peer_id: {peer_id}")

            case 'pong':
                if content.get('path') != "":
                    peer_id = content.get('path').split(", ").pop(-1)
                    send_to = [key for key, value in self.peers.items() if str(key) == peer_id]
                    peer_addresses = [peer_info[1] for peer_info in self.peers.values()]
                    self.send_message_to_peer(send_to, 'pong', {'path': content.get('path'),
                                                                'peers': (peer_addresses).extend(content.get('peers'))})
                    path = content.get('path')
                    print(f"Pong path: {path}")
                else:
                    new_peers = content.get('peers')

                    count = self.max_connections
                    while count > 0:
                        new_peer = random.choice(new_peers)
                        peer_host, peer_port = new_peer
                        if (peer_host, peer_port) != (self.host, self.port) and (peer_host, peer_port) not in [p[1] for
                                                                                                               p in
                                                                                                               self.peers.values()]:
                            print(f"End of Pong: Attempting to connect to new peer: {peer_host}:{peer_port}")
                            if self.connect_to_peer(peer_host, peer_port):
                                count -= 1
                            new_peers.remove(new_peer)
            case 'update':
                if self.super_peer is None or self.board is None:
                    return  # bzw antworten das man dafür nicht zuständig ist
                # get key entry which shall be updated
                key = content['key']

    def stop(self):
        """Stops the node and closes all connections."""
        self.running = False
        if self.server_socket:
            print(f"Closing server socket for Node {self.node_id}.")
            self.server_socket.close()
        for peer_id in list(self.peers.keys()):
            self.remove_peer(peer_id)
        print(f"Node {self.node_id} stopped.")

    ### Data
    def add_data(self, data):
        self.data_store[data.get_id()] = data

    def get_data(self, data_id):
        if data_id not in self.data_store:
            return None
        return self.data_store[data_id]

    def remove_data(self, data_id):
        del self.data_store[data_id]

    ### Board

    def set_super_peer(self, title, keywords):
        # make code only available if the peer has did not have super peer status yet
        if not self.super_peer:
            self.super_peer = True
            self.board = Board(title, keywords)

            # Ideen: Connctions erweitern sodass man unterscheidet zwischen knonw peers und known superpeers,
            #  Anfragen für die Suche nach anderen superepeers nur noch beantworten wenn man selbst superpeer ist
    # def become_superpeer_and_create_board(self, title, keywords):
    #     # Create a Super_Peer instance from the current Peer_node
    #     super_peer = SuperPeer(self.host, self.port, Board(title, keywords))
    #     # Copy relevant attributes from the current Peer_node to the new Super_Peer
    #     super_peer.node_id = self.node_id
    #     super_peer.peers = self.peers
    #     super_peer.data_store = self.data_store
    #     super_peer.max_connections = self.max_connections  ##### Ändern!!!!!! Aber kein Neustart. Problem
    #     super_peer.server_socket = self.server_socket
    #     super_peer.running = self.running
    #
    #     # Stop the current Peer_node without closing connections
    #     self.running = False
    #     self.server_socket = None  # Prevent closing the socket here
    #
    #     print(f"Node {self.node_id} converted to Super_Peer with board '{title}'.")
    #     return super_peer
