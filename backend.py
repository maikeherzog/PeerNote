
import time
from Backend.Board import Board


from Backend.peer_node import PeerNode

### Bootstrapping
def join_network():

    nodes = []
    for i in range(8020, 8030):
        node = PeerNode("127.0.0.1", i, False, None)
        nodes.append(node)
        node.start()
        node.do_bootstrap()

        node.issue_search_request(["world"])
        time.sleep(1)

        node.add_content_card(content=f"node{i} happy birthday", title=f"node{i}", board="yolo")
        node.update_data_req("yolo", "node" + str(i))
        time.sleep(1)

    print("send request\n\n\n")
    nodes[5].send_data_request("127.0.0.1",8003, board_title="yolo", request_type="meta")
    return






def main():
    global bootstrapping_nodes

    ### Base network
    bootstrap = PeerNode("127.0.0.1", 8001, super_peer=True)
    node2 = PeerNode("127.0.0.1", 8002, super_peer=True)
    node3 = PeerNode("127.0.0.1", 8003, super_peer=True, board=Board("yolo", ["hello", "world"]))
    node4 = PeerNode("127.0.0.1", 8004, super_peer=True)
    node5 = PeerNode("127.0.0.1", 8005, super_peer=True)

    bootstrap.start()
    node2.start()
    node3.start()
    node4.start()
    node5.start()

    time.sleep(1) # Give servers a moment to start
    # Form ring-like peer network
    # node1.connect_to_peer("127.0.0.1", 8002)
    # print(node1.peers)
    # # time.sleep(1)
    bootstrap.request_peers()
    time.sleep(1)
    print("boot")
    node2.request_peers()
    time.sleep(1)

    print("node2")
    node3.request_peers()
    time.sleep(1)
    print("node3")
    node4.request_peers()
    time.sleep(1)
    print("node4")
    node5.request_peers()
    # node2.connect_to_peer("127.0.0.1", 8001)
    # node3.connect_to_peer("127.0.0.1", 8002)
    # node4.connect_to_peer("127.0.0.1", 8003)
    # node5.connect_to_peer("127.0.0.1", 8004)

    print(f"node5: {node5.peers}")
    # assert len(node5.peers) == 4
    time.sleep(3)
    print("stopping")
    node6 = PeerNode("127.0.0.1", 8018, super_peer=True)
    # startup node communication
    node6.start()
    # node6.peers[node5.node_id] = (node5.host, node5.port, True)
    time.sleep(1)
    node6.do_bootstrap()
    bootstrap.issue_search_request(["hello"])

    node6.issue_search_request(["hello"])

    # Join network
    join_network()

    node6.add_content_card(content="YOLOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO", title="noch mehr yolo", board="yolo")
    time.sleep(1)
    node6.update_data_req(board_title="yolo", content_title="noch mehr yolo")
    time.sleep(1)
    print(bootstrap.send_data_request("127.0.0.1", 8003, request_type="meta", board_title="yolo"))
    bootstrap.stop()

    time.sleep(4)
    print("Stopping nodes...")
    node2.stop()
    node3.stop()
    node4.stop()
    node5.stop()
    node6.stop()

if __name__ == "__main__":
    main()