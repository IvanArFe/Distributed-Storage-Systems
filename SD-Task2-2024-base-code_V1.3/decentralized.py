from decentralizedServer import gRPC_server_desc
import threading

def start_nodes():
    thread_node0 = threading.Thread(target=gRPC_server_desc.main, args=(32770, 1))
    thread_node1 = threading.Thread(target=gRPC_server_desc.main, args=(32771, 2))
    thread_node2 = threading.Thread(target=gRPC_server_desc.main, args=(32772, 1))
    thread_node0.start()
    thread_node1.start()
    thread_node2.start()

start_nodes()

while True:
    pass
