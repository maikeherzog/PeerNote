import random
import struct
import threading
import time
from collections import deque

from message_type import MessageType
from datetime import datetime
import json
import socket
from Backend.config import BOOTSTRAP

HEADER_SIZE = 4


def create_packet(msg_type: MessageType, node_id: str, host: str, port: int, is_super, payload: list):
    '''
    Create a json string by inserting the parameters in the following frame:

    "type": MessageType,
    "node_id": uuid,
    "timestmap": timestamp of sending,
    "payload": payload
    :param msg_type: type of message
    :param node_id: unique user id
    :param payload: user definied dict
    :return:
    '''
    # serialize to json string
    return json.dumps({
        "type": msg_type,
        "node_id": node_id,
        "host": host,
        "port": port,
        "super": is_super,
        # might be too dirty, need to maybe deserialize it
        "timestamp": str(datetime.now()),
        "payload": payload
    })


def send_packet(data: str, conn: socket):
    # prepare header containing how much bytes are being send in this packet
    header = len(data).to_bytes(HEADER_SIZE, byteorder='big')

    # send real packet
    conn.sendall(header + bytes(data, encoding="utf-8"))


def receive_packet(conn: socket):
    header = receive_exactly(n_bytes=HEADER_SIZE, conn=conn, header=True)

    # no header no package
    if header is None:
        return None

    data_size = struct.unpack(">i", header)[0]
    # receive data
    data = receive_exactly(data_size, conn)
    data = data.decode("utf-8")

    return data


def receive_exactly(n_bytes, conn, header: bool = False):
    '''


    :param n_bytes: n bytes to receive
    :param conn: connection to receive bytes from
    :return: buffer containing readed byte
    '''
    buf = bytearray()
    # Ensure that exactly the desired amount of bytes is received
    while len(buf) < n_bytes:
        # passive waiting until data is coming
        part = conn.recv(n_bytes - len(buf))
        if not part:
            if header and len(buf) == 0:
                return None
            # connection is closed from the other side if this happens
            else:
                # this happens when the header did contain more bytes to read, than the buffer really contained, or any other kind of error
                raise ConnectionError("unexpected closing while receiving data.")
        buf.extend(part)
    return buf



def handle_ping(node, conn, data: dict):
    print(f"Ping message: {data}")

    # prepare data for another ping message or pong message
    payload = data.get("payload", {})
    ping_id = payload.get("ping_id")
    ttl = payload.get("ttl", 0)
    keywords = set(payload.get("keywords", []))
    origin_id = payload.get("origin_id")
    origin_host = payload.get("origin_host")
    origin_port = payload.get("origin"
                              "_port")

    if ping_id in node.routing_table:
        print("Already received PING --> ignoring")
        # ignore duplicate ping
        return
    else:
        node.routing_table[ping_id] = (conn, time.time())

    # Match prüfen
    if True:
        print(f"Node-board id {node.board.board_id}")
        try:
            with open("data/boards.json", "r", encoding="utf-8") as f:
                boards = json.load(f)
                print(f"[BOOTSTRAP] Loaded boards: {boards}")
        except Exception as e:
            print(f"[BOOTSTRAP] Fehler beim Laden von board.json: {e}")
            boards = []

        pong_payload = {
            "ping_id": ping_id,
            "title": node.board.get_title(),
            "board_id": node.board.board_id,
            "responder_id": node.node_id,
            "responder_host": node.host,
            "responder_port": node.port,
            "boards": boards,
        }

        try:
            pong_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            pong_conn.connect((origin_host, origin_port))
            pong_packet = create_packet(MessageType.PONG, node.node_id, node.host, node.port, node.super_peer,
                                        pong_payload)
            send_packet(pong_packet, pong_conn)
            pong_conn.close()
        except Exception as e:
            print(f"Failed to send PONG to origin: {e}")

    # Weiterleiten an andere Peers
    if ttl > 1:
        new_payload = payload.copy()
        new_payload["ttl"] = ttl - 1

        with node.peers_lock:
            peers = deque(node.peers.items())

        while peers:
            peer_id, (host, port, _) = peers.popleft()

            if peer_id == data["node_id"]:
                continue  # Don't send back to sender

            try:
                fwd_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                fwd_conn.connect((host, port))
                fwd_packet = create_packet(MessageType.PING, node.node_id, node.host, node.port, node.super_peer,
                                           new_payload)
                send_packet(fwd_packet, fwd_conn)
                fwd_conn.close()
            except Exception as e:
                print(f"Failed to forward PING to {host}:{port} from sender {node.host}:{node.port}: {e}")


def handle_pong(node, data):
    payload = data.get("payload", {})
    ping_id = payload.get("ping_id")
    responder_info = {
        "responder_id": payload.get("responder_id"),
        "board_title": payload.get("title"),
        "board_id": payload.get("board_id"),
        "responder_host": payload.get("responder_host"),
        "responder_port": payload.get("responder_port"),
        "boards": payload.get("boards")
    }

    print(responder_info)

    print(data)
    # pong belongs to this node
    if ping_id in node.pongs_received:
        node.pongs_received[ping_id].append(responder_info)
        print(f"Stored PONG from {responder_info['responder_id']}")
        print(f"[PAYLOAD]: {node.pongs_received[ping_id]}")

        if payload.get("responder_host") == BOOTSTRAP[0] and payload.get("responder_port") == BOOTSTRAP[1]:
            #payload save into json file and delete old content
            try:
                with open("data/received_boards.json", "w", encoding="utf-8") as f:
                    json.dump(payload.get("boards", []), f, ensure_ascii=False, indent=2)
                print(f"Saved boards to data/received_boards.json")
            except Exception as e:
                print(f"Error saving boards to data/boards.json: {e}")
            



    # if pong is not directed to this node -> send to next in routing table
    elif ping_id in node.routing_table:

        # get previous connection
        prev_conn, _ = node.routing_table[ping_id]
        try:
            # prepare png
            pong_packet = create_packet(MessageType.PONG, node.node_id, node.host, node.port, node.super_peer,
                                        payload)

            # send pong
            send_packet(pong_packet, prev_conn)
        except Exception as e:
            print(f"Failed to route PONG: {e}")


def peer_list_handler(node, content: list[dict]):
    # expect the super peer format

    # only if this is a super peer
    if not node.super_peer:
        return

    for peer in content:
        if peer.get('node_id') in node.peers.keys():
            continue
        else:
            other_id = peer.get('node_id')
            host = peer.get('host')
            port = peer.get('port')
            super = peer.get('super')
            if other_id != node.node_id and node.connect(host, port):
                node.peers[other_id] = (host, port, True)

            if len(node.peers) > node.max_total_conn:
                break


def connect_handler(node, conn, node_id, host, port, super):
    '''
    This method is called when a peers tries to connect bidirectional to self.
    self will check if there is enough space in it's own peer list and in that case answer positively,
    otherwise negatively by sending a format which is not expected.
    :return:
    '''

    try:

        def send_correct_response(conn):
            data = create_packet(MessageType.CONNECT_RESPONSE, node.node_id, node.host, node.port, node.super_peer,
                                 [])
            send_packet(data, conn)

        if node_id in node.peers:
            # send an expected connection response as this peer is correctly added here
            send_correct_response(conn)
        elif len(node.peers) < node.max_total_conn:
            # if there is space in list accept
            node.peers[node_id] = (host, port, super)
            send_correct_response(conn)
        else:
            node.send_close(conn)
    except Exception as e:
        print(f"Error while asking sending connection resposne: {e}")


def get_peers_handler(node, conn, other_id, host, port):
    if not node.super_peer:
        return

    # add to own peer list if other_id is not in peer list
    with node.peers_lock:
        if other_id not in node.peers.keys() and node.connect(host, port):
            node.peers[other_id] = (host, port, True)

    try:
        # Filter nur Super-Peers
        with node.peers_lock:
            super_peers = [
                {"node_id": peer_id, "host": host, "port": port}
                for peer_id, (host, port, is_super) in node.peers.items()
                if is_super and peer_id != other_id
            ]
        if node.bootstrap:
            super_peers.append({
                'node_id': node.node_id,
                'host': node.host,
                'port': node.port
            })

        selected_peers = random.sample(super_peers, min(node.MAX_PEER_LIST, len(super_peers)))

        data = create_packet(MessageType.PEER_LIST, node.node_id, node.host, node.port, node.super_peer,
                             selected_peers)

        send_packet(data, conn)

    except Exception as e:
        print(f"Error sending peer list: {e}")


def send_close(node, conn: socket):
    if conn.fileno() != -1:
        data = create_packet(MessageType.CLOSE, node.node_id, node.host, node.port, node.super_peer, {})
        send_packet(data, conn)
        # conn.shutdown(socket.SHUT_RDWR)
        conn.close()
