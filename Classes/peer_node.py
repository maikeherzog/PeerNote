import socket
import struct
import threading
import json
import hashlib
import time
from datetime import datetime
import uuid
import random

import ipaddress

from Classes.Board import Board
from Classes.peer_message_handler import *
from message_type import MessageType

BOOTSTRAP = ("127.0.0.1", 8001)


class PeerNode:
    MAX_PEER_LIST = 5

    def __init__(self, host: str = "127.0.0.1", port: int = 8000, super_peer: bool = False, board: Board = None):

        if host == "0.0.0.0" or host == "" or port == 0:
            raise Exception("0.0.0.0 and port 0 is not supported")
        self.host: str = host
        self.port: int = port

        if (host, port) == BOOTSTRAP:
            self.bootstrap = True
        else:
            self.bootstrap = False
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

        # if set super peer there should be at least an empty board TODO
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
        print(self.server_socket.getsockname())
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
                threading.Thread(target=self._handle_peer_connection, args=(conn, addr), daemon=True).start()
            except Exception as e:
                if self.running:
                    print(f"Error accepting connection: {e}")
                break

    def _get_peers_handler(self, conn, other_id, host, port):

        if not self.super_peer:
            return

        # add to own peer list if other_id is not in peer list
        if other_id not in self.peers.keys():
            self.peers[other_id] = (host, port, True)

        try:
            # Filter nur Super-Peers
            super_peers = [
                {"node_id": peer_id, "host": host, "port": port}
                for peer_id, (host, port, is_super) in self.peers.items()
                if is_super and peer_id != other_id
            ]
            if self.bootstrap:
                super_peers.append({
                    'node_id': self.node_id,
                    'host': self.host,
                    'port': self.port
                })
            selected_peers = super_peers[:self.MAX_PEER_LIST]

            data = create_packet(MessageType.PEER_LIST, self.node_id, self.host, self.port, selected_peers)

            send_packet(data, conn)

        except Exception as e:
            print(f"Error sending peer list: {e}")

    def _peer_list_handler(self, content: list[dict]):
        # expect the super peer format

        #only if this is a super peer
        if not self.super_peer:
            return

        for peer in content:
            if peer.get('node_id') in self.peers.keys():
                continue
            else:
                self.peers[peer.get('node_id')] = (peer.get('host'), peer.get('port'), True)

                if len(self.peers) > self.max_total_conn:
                    break

    def request_peers(self):
        '''
        Using this function a peer can request other peers from it's onw peer list
        :return:
        '''

        # only allow connecctions this way if this is a super peer, other peers have to search for boards and add this way
        if not self.super_peer:
            return

        # if there is no peer in the list use the bootstrapping peer as connection
        if len(self.peers) == 0 and not self.bootstrap:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            conn.connect(BOOTSTRAP)

            data = create_packet(MessageType.GET_PEERS, self.node_id, self.host, self.port, [])
            send_packet(data, conn)

            # expect some kind of answer
            self._handle_peer_connection(conn, BOOTSTRAP)

            # sanity close
            if conn.fileno() != -1:
                self.send_close(conn)

        for peer_id, (host, port, is_super) in self.peers.items():
            if not is_super:
                continue
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            conn.connect((host, port))

            data = create_packet(MessageType.GET_PEERS, self.node_id, self.host, self.port, [])
            send_packet(data, conn)

            # expect some kind of answer
            self._handle_peer_connection(conn, (host, port))

            # sanity close
            if conn.fileno() != -1:
                self.send_close(conn)


    def bootstrap(self):
        '''
        This function shall work for simple peers to bootstrap to the network, in order to do this just try to connect
        with bootstrap peer, if successful connected add to peerslist as default peer. Superpeers may not need to use this.


        :return:
        '''

        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # if connection successful (no error) ping bootstrap
            conn.connect(BOOTSTRAP)

            data = create_packet(MessageType.PING, self.node_id, self.host, self.port, ["default"])
            send_packet(data, conn)

            # receive response as pong
            data: dict = json.loads(receive_packet(conn))

            match MessageType(data.get("type", "error")):

                case MessageType.PONG:
                    # TODO add at leat bootstrap peer to peers list and maybe all other boards ( depending on implementation)
                    return
                case _:
                    raise Exception("unexpected behavior, bootstap peer may be down")

        except Exception as e:
            raise e


    def _handle_peer_connection(self, conn, addr):
        """Handles a single client connection (a peer)."""

        data = receive_packet(conn)
        send_host, send_port = addr

        while data is not None:
            try:

                # transform data into a readable format
                data = json.loads(data)
                try:
                    msg_type = MessageType(data.get("type", "error"))

                except ValueError as e:
                    print(f"Couldnt get type of dataset: {e}")
                    msg_type = MessageType.ERROR
                other_id = data.get("node_id")
                reach_host = data.get("host")
                reach_port = data.get("port")

                match msg_type:
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
                        self._get_peers_handler(conn, other_id, reach_host, reach_port)
                        print("Peer requests peer list.")
                        # send known peers
                    case MessageType.PEER_LIST:
                        print("Got peer list.")
                        self._peer_list_handler(data.get('payload'))
                        # after adding whole peer list break this loop ???
                        return
                        # add peers
                    case MessageType.CLOSE:
                        print("Connection close requested.")
                        conn.shutdown(socket.SHUT_RDWR)
                        if conn.fileno() != -1:
                            conn.close()
                        # cleanup and close
                    case MessageType.ERROR:
                        print("Received unknown or malformed message.")
                        # maybe log or ignore


            except Exception as e:
                print(f"Error handling client connection from {addr}: {e}")
            finally:
                conn.close()
                # if finally executes break or return the error is discarded (maybe think about this here??!?)

            # sanity check whether is closed, this can happen whenever
            if conn.fileno() < 0:
                # break the while loop and therefore close connection entirely
                break
            else:
                data = receive_packet(conn)

    def send_close(self, conn: socket):
        data = create_packet(MessageType.CLOSE, self.node_id, self.host, self.port, {})
        send_packet(data, conn)
        conn.shutdown(socket.SHUT_RDWR)
        conn.close()

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
