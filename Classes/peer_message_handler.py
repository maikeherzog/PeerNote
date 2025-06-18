import struct
import threading

from message_type import MessageType
from datetime import datetime
import json
import socket

HEADER_SIZE = 4


def create_packet(msg_type: MessageType, node_id: str, host:str, port: int, is_super, payload: list):
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

    #prepare header containing how much bytes are being send in this packet
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


