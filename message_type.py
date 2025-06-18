from enum import Enum

'''
So stelle ich mir das ganze bisher vor:
1. ein oder mehrere Bootstrapping super peers (bei mehreren muss man wahrscheinlich einmal gucken, dass diese sich schon untereinander kennen.
2. andere peers können als peers joinen, diese können sich mit get peers neue peers suchen, sie bekommen aber ausschließlich superpeers vorgeschlagen
3. peers können die metadaten bei superpeers speichen (soft state) regelmäßiges update nötig
4. superpeers fragen bei bedarf alle superpeers die inhalte hinterlegt haben nach deren inhalten und fügen diese zusammen
'''



class MessageType(str, Enum):
    # request bulletin board html???
    DATA_REQUEST = "data_request"
    # respond with data
    DATA_RESPONSE = "data_response"
    # update soft state
    DATA_UPDATE = "data_update"
    # ping for querying bulletin boards
    PING = "ping"
    # pong as answer
    PONG = "pong"
    # request peers -> only superpeers should answer this
    GET_PEERS = "get_peers"
    # respond with a list of all peers
    PEER_LIST = "peer_list"
    # close connection, this should be used to close a connection
    CLOSE = "close_connection"
    # error in case of something unexpected
    ERROR = "error"
    CONNECT = "connect"
    CONNECT_RESPONSE = "connect_response"


'''
Eine Nachricht sollte immer den ungefähr folgendenaufgau haben:

{
    "type": MessageType,
    "node_id": uuid,
    "timestmap": timestamp of sending,
    "payload": {
        ---------------user defined dict after convention-----------------------
    }
}
'''