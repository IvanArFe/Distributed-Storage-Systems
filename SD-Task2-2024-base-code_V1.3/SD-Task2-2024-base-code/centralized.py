import gRPC_master_server_centr, gRPC_slave_server_centr
import threading

# Script to launch centralised master server and slaves servers with threads.
def master():
    master_thread = threading.Thread(target=gRPC_master_server_centr.main)
    master_thread.start()

def slaves():
    thread_sl1 = threading.Thread(target=gRPC_slave_server_centr.main, args=(32771,))
    thread_sl2 = threading.Thread(target=gRPC_slave_server_centr.main, args=(32772,))
    thread_sl1.start()
    thread_sl2.start()

master()
slaves()

while True:
    pass