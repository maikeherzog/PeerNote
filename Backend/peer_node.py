import json
import time
import uuid
import random
import requests
import os

from collections import deque
from Backend.Board import Board
from Backend.peer_message_handler import *
from message_type import MessageType
from Backend.config import BOOTSTRAP


class PeerNode:
    MAX_PEER_LIST = 5

    def __init__(self, host: str = "127.0.0.1", port: int = 8000, super_peer: bool = False, board: Board = None):

        # if host == "0.0.0.0" or host == "" or port == 0:
        #     raise Exception("0.0.0.0 and port 0 is not supported")
        self.host: str = host
        self.port: int = port

        if (host, port) == BOOTSTRAP:
            self.bootstrap = True
        else:
            self.bootstrap = False
        # max number of active tcp connections
        self.max_connections = 100

        self.max_total_conn = 100

        # Data structures for routing using ping and pong
        self.routing_table = {}  # ping_id: (conn, timestamp)
        self.pongs_received = {}  # ping_id: list of pong info (optional, for storing results)

        # MUTEXE -------------------------------------------
        self.peers_lock = threading.Lock()
        self.routing_lock = threading.Lock()
        self.pong_lock = threading.Lock()

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
        if self.bootstrap and board is None:
            self.board = Board("default", {""})
        else:
            self.board = board
        print(f"Node {self.node_id} initialized at {self.host}:{self.port}")

        self.pongs = 0

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

        self.port = self.server_socket.getsockname()[1]
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
                print(f"{self.host}:{self.port}: incoming connection from {addr}")
                # Handle connection in a new thread
                threading.Thread(target=self._handle_peer_connection_request, args=(conn, addr), daemon=True).start()
            except Exception as e:
                if self.running:
                    print(f"Error accepting connection: {e}")
                break

    def connect(self, host, port, add_to_peers: bool = False) -> bool:
        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect((host, port))
            print("Successful connection")
            data = create_packet(MessageType.CONNECT, self.node_id, self.host, self.port, self.super_peer, [])
            send_packet(data, conn)

            # await response
            response = receive_packet(conn)

            if response is not None:
                resp_data = json.loads(response)
                res = resp_data.get("type") == MessageType.CONNECT_RESPONSE.value and resp_data.get(
                    'node_id') != self.node_id
                if res and add_to_peers:
                    self.peers[resp_data.get('node_id')] = (host, port, resp_data.get("super", False))
                return res
            return False
        except Exception as e:
            print(f"Error while {self.host}:{self.port} tries to connect to {host}:{port}: {e}")
            return False

    def request_peers(self):
        '''
        Using this function a (super) peer can request other peers from it's own peer list
        :return:
        '''

        # only allow connecctions this way if this is a super peer, other peers have to search for boards and add this way
        if not self.super_peer:
            return

        # if there is no peer in the list use the bootstrapping peer as connection
        if len(self.peers) == 0 and not self.bootstrap:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            conn.connect(BOOTSTRAP)

            data = create_packet(MessageType.GET_PEERS, self.node_id, self.host, self.port, self.super_peer, [])
            send_packet(data, conn)

            # expect some kind of answer
            self._handle_peer_connection_request(conn, BOOTSTRAP)

            # sanity close
            if conn.fileno() != -1:
                self.send_close(conn)

        # avoid using self.peers because it does not allow to change size during iteration

        # copy peers into deque
        with self.peers_lock:
            queue = deque(self.peers.items())

            # copy to keep track of visited and to be visited peers
            visited = list(self.peers.keys())

        # 'iterate' through all peers
        while queue:

            # LIFO - Queue
            peer_id, (host, port, is_super) = queue.popleft()

            # return if not super
            if not is_super or peer_id == self.node_id:
                continue

            # connect to remote peer - TODO: fix if connection fails
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect((host, port))

            # send get peers message
            data = create_packet(MessageType.GET_PEERS, self.node_id, self.host, self.port, self.super_peer, [])
            send_packet(data, conn)

            self._handle_peer_connection_request(conn, (host, port))

            if len(self.peers) >= self.max_total_conn:
                return

            # close socket

            if conn.fileno() != -1:
                self.send_close(conn)

            # add possible new peers - TODO: visited as set
            with self.peers_lock:
                for new_peer_id, new_peer_info in self.peers.items():
                    if new_peer_id not in visited and new_peer_id != self.node_id:
                        visited.append(new_peer_id)
                        queue.append((new_peer_id, new_peer_info))

    def do_bootstrap(self):
        '''
        This function shall work for simple peers to bootstrap to the network, in order to do this just try to connect
        with bootstrap peer, if successful connected add to peerslist as default peer. Superpeers may not need to use this.


        :return:
        '''

        if not self.bootstrap:
            return self.connect(BOOTSTRAP[0], BOOTSTRAP[1], True)

    def issue_search_request(self, keywords: set = {}):
        ping_id = str(uuid.uuid4())
        ttl = 5

        payload = {
            "ping_id": ping_id,
            "origin_id": self.node_id,
            "origin_host": self.host,
            "origin_port": self.port,
            "ttl": ttl,
            "keywords": keywords,
        }

        self.pongs_received[ping_id] = []  # to save all received pongs (if any)
        with self.peers_lock:
            for _, (host, port, _) in self.peers.items():
                try:
                    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    conn.connect((host, port))
                    packet = create_packet(MessageType.PING, self.node_id, self.host, self.port, self.super_peer,
                                           payload)
                    send_packet(packet, conn)
                    # optional das ganze hierdurch handeln lassen
                    # threading.Thread(target=self._handle_peer_connection, args=(conn, (host, port)), daemon=True).start()
                except Exception as e:
                    print(f"Error sending ping to {host}:{port} – {e}")

    def _handle_peer_connection_request(self, conn, addr):
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
                payload = data.get('payload')

                match msg_type:
                    case MessageType.DATA_REQUEST:
                        print("Data request received.")
                        # send requested data
                        self.data_request_handler(conn, payload, reach_host, reach_port)
                    case MessageType.DATA_PEER_REQUEST:
                        self.send_req_card_frame(conn, payload)
                    case MessageType.DATA_RESPONSE:
                        print("Got data response.")
                        # send close, only react to possible cases
                        send_close(self, conn)
                    case MessageType.DATA_UPDATE:
                        print("Data update received.")
                        self.data_update_handler(other_id, payload, reach_host, reach_port)
                        # update local data

                    case MessageType.PING:
                        print("Received PING.")
                        handle_ping(self, conn, data)
                        # reply with PONG

                    case MessageType.PONG:
                        print("Received PONG.")
                        self.pongs += 1
                        handle_pong(self, data)
                        # maybe update liveness

                    case MessageType.GET_PEERS:
                        get_peers_handler(self, conn, other_id, reach_host, reach_port)
                        print("Peer requests peer list.")
                        # send known peers

                    case MessageType.PEER_LIST:
                        print("Got peer list.")
                        peer_list_handler(self, data.get('payload'))
                        # after adding whole peer list break this loop ???
                        return
                        # add peers
                    case MessageType.CLOSE:
                        print("Connection close requested.")
                        if conn.fileno() != -1:
                            conn.shutdown(socket.SHUT_RDWR)
                            conn.close()
                        # cleanup and close
                    case MessageType.ERROR:
                        print("Received unknown or malformed message.")
                        # maybe log or ignore

                        # DEFAULT handling: close connection
                        send_close(self, conn)
                        break

                    case MessageType.CONNECT:
                        print("Connection request")
                        connect_handler(self, conn, other_id, reach_host, reach_port, data.get('super'))

                    case MessageType.CONNECT_RESPONSE:
                        print("Response to connection request")
                        # always decline
                        send_close(self, conn)

                    case MessageType.BOARD_REGISTER:
                        print("Board registration received.")
                        self.handle_board_registration(payload)
                        # Send confirmation back
                        response = create_packet(MessageType.BOARD_REGISTER_RESPONSE, self.node_id, self.host, self.port, self.super_peer, {"status": "registered"})
                        send_packet(response, conn)

                    case MessageType.BOARD_REGISTER_RESPONSE:
                        print("Board registration confirmed.")
                        # Handle confirmation if needed
                    
                    case MessageType.BOARD_UNREGISTER:
                        print("Board unregistration received.")
                        self.handle_board_unregistration(payload)
                        # Send confirmation back
                        response = create_packet(MessageType.BOARD_UNREGISTER_RESPONSE, self.node_id, self.host, self.port, self.super_peer, {"status": "unregistered"})
                        send_packet(response, conn)

                    case MessageType.BOARD_UNREGISTER_RESPONSE:
                        print("Board unregistration confirmed.")
                        # Handle confirmation if needed

            except Exception as e:
                print(
                    f"Error host: {self.host}:{self.port} handling client connection from {addr} with msg_type: {msg_type}: {e}")
            finally:
                conn.close()
                # if finally executes break or return the error is discarded (maybe think about this here??!?)

            # sanity check whether is closed, this can happen whenever
            if conn.fileno() < 0:
                # break the while loop and therefore close connection entirely
                break
            else:
                data = receive_packet(conn)

    def stop(self):
        """Stops the node and closes all connections."""
        self.running = False
        self.peers.clear()
        if self.server_socket:
            self.server_socket.close()

    def set_super_peer(self, title, keywords):
        print("set_super_peer called")
        
        if not self.super_peer:
            # First time becoming super peer
            self.super_peer = True
            self.board = Board(title, keywords)
            
            # Send board registration to bootstrap via P2P
            if not self.bootstrap:
                self.send_board_registration_to_bootstrap(title, keywords)
            
            print(f"Peer is superpeer:{self.super_peer}")
            return True
        else:
            # Already a super peer, but allow additional board creation
            print("Peer is already super peer, registering additional board")
            
            # Send board registration to bootstrap via P2P for additional boards
            if not self.bootstrap:
                self.send_board_registration_to_bootstrap(title, keywords)
            
            return True  # Return True to indicate success

    # -------------------- BOARD / DATA Handler --------------------
    def data_update_handler(self, other_id: str, payload: list[dict], req_host, req_port):
        '''
        payload shoul look something like this
        [{
        board: title,
        type: card comment etc
        c_title:,
        }]

        :param other_id:
        :param payload:
        :return:
        '''

        # only manipulate board if super peer and a board exists
        if not self.super_peer or self.board is None:
            return

        for entry in payload:
            board_title = entry.get('board', "")
            content_title = entry.get('title', "")
            c_type = entry.get("type", "")

            if board_title == "" or content_title == "" or self.board.get_title() != board_title or c_type != "card":
                pass
                # TODO: print an error
                print(f"Could not add the content-meta information {content_title}")
            else:
                self.board.update_reference(other_id, content_title, host=req_host, port=req_port)

    def update_data_req(self, board_title: str, content_title: str, c_type: str = "card"):
        # eventuell hier noch eine ping id mit rein legen oder soo

        payload = [
            {
                'board': str(board_title),
                'title': str(content_title),
                'type': str(c_type)
            }
        ]

        with self.pong_lock:
            # TODO: auf mehrere Auswahlmöglichkeiten erweitern
            for pong_row in self.pongs_received.values():
                for pong in pong_row:
                    if pong.get("board_title") == board_title:
                        host = pong.get("responder_host")
                        port = pong.get("responder_port")

                        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        conn.connect((host, port))
                        data = create_packet(MessageType.DATA_UPDATE, self.node_id, self.host, self.port,
                                             self.super_peer, payload)
                        send_packet(data, conn)

    # CHAT-GPT -lol
    def send_req_card_frame(self, conn, payload):
        try:
            board_title = payload.get("board")
            request_type = payload.get("type")  # "meta" or "content"
            content_title = payload.get("title")  # optional if meta

            # add meta here if we want to ask peers for meta information
            if not board_title or request_type not in ("content"):
                raise ValueError("Malformed payload")

            self.send_content_card(conn, content_title)

        except Exception as e:
            error_packet = create_packet(
                MessageType.ERROR,
                self.node_id, self.host, self.port, self.super_peer,
                {"error": str(e)}
            )
            send_packet(error_packet, conn)

        finally:
            # aufräumen, also connection schließen
            if conn.fileno() != -1:
                conn.close()

    def send_content_card(self, conn, content_title):

        card_ref = self.data_store.get(content_title)
        if not card_ref:
            # no such content reference
            # just leave this function
            return

        (content, board) = card_ref

        # Open connection to actual content peer
        forward_payload = [{
            "type": "content_response",
            "title": content_title,
            "content": str(self.data_store.get(content_title))
        }]

        payload = [(board, content_title, content)]

        # board, title , content

        forward_packet = create_packet(MessageType.DATA_RESPONSE, self.node_id, self.host, self.port,
                                       self.super_peer, payload)
        send_packet(forward_packet, conn)


    def data_request_handler(self, conn, payload, requester_host, requester_port):
        try:
            board_title = payload.get("board")
            request_type = payload.get("type")  # "meta" or "content"
            content_title = payload.get("title")  # optional if meta

            # Fallback
            if not board_title or request_type not in ("meta", "content"):
                raise ValueError("Malformed payload")

            if not self.super_peer or self.board is None:
                raise ValueError("Node is not a super peer or board not available")

            if board_title != self.board.get_title():
                raise ValueError("Board title mismatch")

            print(f"Meta data requested for board: {board_title}")
            card_refs = self.board.get_card_references()
            meta = []
            for (node_id, title), card in card_refs.items():
                meta.append((
                    node_id,
                    title,
                    card.host,
                    card.port,
                    card.get_timestamp()
                ))

            response = create_packet(
                MessageType.DATA_RESPONSE,
                self.node_id, self.host, self.port, self.super_peer,
                meta
            )
            send_packet(response, conn)

        except Exception as e:
            print(f"Data request error: {e}")
            error_packet = create_packet(
                MessageType.ERROR,
                self.node_id, self.host, self.port, self.super_peer,
                {"error": str(e)}
            )


            try:
                send_packet(error_packet, conn)
            except Exception as _e:
                #ignore
                pass


    def resolve_meta_data(self, meta_list: str, board_title: str, board_id: str):
        # load meta list into a json format
        result = []
        # sequentiell:
        for (b_id, title, host, port, timestamp) in meta_list:
            # define meta_info as tuple (id, host, port, title
            # ask for the content matching to the meta informaton
            response = self.send_data_request(host, port, board_title, "content", title, peer_request=True)

            # response = json.loads(response)
            payload = response.get("payload")
            # expect a list in return
            if response and response.get("type") == MessageType.DATA_RESPONSE and response.get("payload"):
                # Every entry in payload should contain (board-title, content-title, content)
                node_id = response.get("node_id")
                for (board, content_title, content) in payload:
                    # TODO put the data into the right format
                    if board == board_title:
                        result.append((board_id, board_title, node_id, content_title, content))
            else:
                continue

        return result


    def send_data_request(self, host: str, port: int, board_title: str, request_type: str = "meta",
                          content_title: str = None, peer_request: bool = False):
        """
        Sendet eine gezielte DATA_REQUEST an einen Peer.

        :param peer_request: if true, the request is executed as data peer request
        :param host: Zielhost
        :param port: Zielport
        :param board_title: Titel des Boards
        :param request_type: "meta" für Meta-Daten oder "content" für konkreten Inhalt
        :param content_title: optionaler Titel für eine spezifische Karte (bei Content-Anfrage) nicht implementiert!!!!!!!!!!!!
        """
        payload = {
            "board": board_title,
            "type": request_type
        }

        if request_type == "content" and content_title:
            payload["title"] = content_title

        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect((host, port))

            packet = create_packet(
                MessageType.DATA_REQUEST if not peer_request else MessageType.DATA_PEER_REQUEST,
                self.node_id,
                self.host,
                self.port,
                self.super_peer,
                payload
            )
            send_packet(packet, conn)

            # Direkt Antwort lesen (optional, falls synchron gewünscht)
            response = receive_packet(conn)
            response = json.loads(response)

            if response and request_type == "meta" and response.get("payload"):
                print(f"DATA_RESPONSE erhalten: {response}")
                return self.resolve_meta_data(response.get("payload"), board_title, response.get("board_id"))

            elif response and request_type == "content" and response.get("payload"):
                return response

                # Verarbeitung (optional)
                # z. B. json.loads(response) und weiterreichen an eine handler-Methode
            else:
                print("Keine Antwort vom Peer erhalten.")

                return None

            # Verbindung schließen
            # if conn.fileno() != -1:
            #     send_close(self, conn)

        except Exception as e:
            print(f"Fehler beim Senden des DATA_REQUEST an {host}:{port} – {e}")


    # ______________________________________________________________________________________________________________________
    #                                   Manipulate content on the peer node

    def add_content_card(self, content: str, title: str, board: str = None):
        if len(content) > 1024:
            raise ValueError("Tooo long content")

        if board is None:
            board = "default"
        # very simple, maybe optimize
        self.data_store[title] = (content, board)

    def send_board_registration_to_bootstrap(self, title, keywords):
        try:
            from Backend.config import BOOTSTRAP
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect(BOOTSTRAP)
            
            board_data = {
                "board_id": str(uuid.uuid4()),
                "peer_id": self.node_id,
                "board_title": title,
                "keywords": keywords,
                "peer_host": self.host,
                "peer_port": self.port
            }
            
            packet = create_packet(MessageType.BOARD_REGISTER, self.node_id, self.host, self.port, self.super_peer, board_data)
            send_packet(packet, conn)
            
            # Wait for response
            response = receive_packet(conn)
            if response:
                print(f"Board registration response: {response}")
            
            conn.close()
        except Exception as e:
            print(f"Error registering board with bootstrap: {e}")

    def handle_board_registration(self, board_data):
        """Handle board registration from a peer (only on bootstrap node)"""
        if not self.bootstrap:
            return  # Only bootstrap should handle registrations
        
        import json
        import os
        
        # Create data directory if it doesn't exist
        os.makedirs("data", exist_ok=True)
        file_path = os.path.join("data", "boards.json")
        
        # Load existing boards
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                boards = json.load(f)
        else:
            boards = []
        
        # Add new board
        board_entry = {
            "board_id": board_data["board_id"],
            "peer_id": board_data["peer_id"],
            "board_title": board_data["board_title"],
            "keywords": board_data["keywords"],
            "peer_host": board_data["peer_host"],
            "peer_port": board_data["peer_port"],
            "created_at": time.time(),
            "status": "active"
        }
        
        boards.append(board_entry)
        
        # Save boards
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(boards, f, ensure_ascii=False, indent=2)
        
        print(f"[BOOTSTRAP] Board registered: {board_data['board_title']} by peer {board_data['peer_id']}")

    def send_board_unregistration_to_bootstrap(self, board_title):
        try:
            from Backend.config import BOOTSTRAP
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect(BOOTSTRAP)
            
            unregister_data = {
                "peer_id": self.node_id,
                "board_title": board_title
            }
            
            packet = create_packet(MessageType.BOARD_UNREGISTER, self.node_id, self.host, self.port, self.super_peer, unregister_data)
            send_packet(packet, conn)
            
            # Wait for response
            response = receive_packet(conn)
            if response:
                print(f"Board unregistration response: {response}")
            
            conn.close()
        except Exception as e:
            print(f"Error unregistering board with bootstrap: {e}")

    def handle_board_unregistration(self, unregister_data):
        """Handle board unregistration from a peer (only on bootstrap node)"""
        if not self.bootstrap:
            return  # Only bootstrap should handle unregistrations
        
        import json
        import os
        
        file_path = os.path.join("data", "boards.json")
        
        if not os.path.exists(file_path):
            return
        
        # Load existing boards
        with open(file_path, "r", encoding="utf-8") as f:
            boards = json.load(f)
        
        # Remove boards matching peer_id and board_title
        peer_id = unregister_data["peer_id"]
        board_title = unregister_data["board_title"]
        
        original_count = len(boards)
        boards = [board for board in boards if not (board["peer_id"] == peer_id and board["board_title"] == board_title)]
        
        if len(boards) < original_count:
            # Save updated boards list
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(boards, f, ensure_ascii=False, indent=2)
            
            print(f"[BOOTSTRAP] Board unregistered: {board_title} by peer {peer_id}")
        else:
            print(f"[BOOTSTRAP] Board not found for unregistration: {board_title} by peer {peer_id}")



