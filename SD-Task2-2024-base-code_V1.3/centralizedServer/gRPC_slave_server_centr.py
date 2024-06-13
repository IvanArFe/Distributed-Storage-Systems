import json
import string
import time
from concurrent import futures
from sys import argv
import sys
import os
from threading import Semaphore

import grpc
from typing import Dict

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../proto')
import store_pb2
import store_pb2_grpc

#Here we define class corresponding to Slave Nodes (Servers) which implements KeyValueStoreServicer functions
class SlaveServiceServicer(store_pb2_grpc.KeyValueStoreServicer):

    def __init__(self):
        self.keyValueStore: Dict[string, string] = {} # Dictionary to store key value pairs
        self.slowDown = False
        self.slowDownSecs = 0
        self.semaphore = Semaphore()

        # Read backup file in order to restore the state of the server in case of failure
        if os.path.isfile("backup_centr.json"):
            with open("backup_centr.json", "r") as f:
                self.keyValueStore = json.load(f)
    
    # This funtion returns corresponding value to a key if exists, if not return None
    def get(self, request: store_pb2.GetRequest, context: grpc.aio.ServicerContext) -> store_pb2.GetResponse:
        
        self.semaphore.acquire()
        value = self.keyValueStore.get(request.key) # Obtain value from corresponding key
        self.semaphore.release()

        if value is None:
            resp = store_pb2.GetResponse(value=None, found=False) # If value is Null, set found to False
        else:
            resp = store_pb2.GetResponse(value=value, found=True) # Else set value and found true
        
        # Add delay to communication
        if self.slowDown:
            time.sleep(self.slowDownSecs)
        
        return resp
    
    # This function stores a key value for a given key
    def put(self, request: store_pb2.PutRequest, context: grpc.aio.ServicerContext) -> store_pb2.PutResponse:
        self.semaphore.acquire()
        self.keyValueStore[request.key] = request.value # Store value received from request.key
        self.semaphore.release()
        return store_pb2.PutResponse(succes=True)

    # This function add delay to the communication between nodes with the value seconds in request
    def slowDown(self, request: store_pb2.SlowDownRequest, context: grpc.aio.ServicerContext) -> store_pb2.SlowDownResponse:
        self.slowDown = True # Set slowDown to True
        self.slowDownSecs = request.seconds # Delay request.seconds the communication
        return store_pb2.SlowDownResponse(succes=True)
    
    # Here we define can_commit function in order to check if a key value can be modified by the master node if all slaves nodes agree
    def canCommit(self, request: store_pb2, context: grpc.aio.ServicerContext) -> store_pb2.CommitResponse:
        return store_pb2.CanCommitResponse(succes=True) # Always return True in order to accept request modification
    
    # Restore to default values in order to drop delays in communication
    def restore(self, request: store_pb2.RestoreRequest, context: grpc.aio.ServicerContext) -> store_pb2.RestoreResponse:
        self.slow_down = False # Set slowDown to False
        self.slow_down_secs = 0 # Set the time to slow down the communication to 0
        return store_pb2.RestoreResponse(succes=True)

def slave_server(port):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10)) # Create a gRPC server with 10 threads
    store_pb2_grpc.add_KeyValueStoreServicer_to_server(SlaveServiceServicer(), server) # Add the previous class to the server

    # ports will be argv[1] and values will be 32771 or 32772
    print(f"[!] Starting Slave Server. Listening on port {port}") # Print message to show that the server is running
    server.add_insecure_port(f'localhost:{port}') # Set the port for the server, specified in documentation
    server.start() # Start the server
    server.wait_for_termination() # Wait for termination

def main(port_node):   
    slave_server(port_node) # Call slave_server function
    

if __name__ == '__main__':
    main(argv[1]) # Call main function with the port number as argument