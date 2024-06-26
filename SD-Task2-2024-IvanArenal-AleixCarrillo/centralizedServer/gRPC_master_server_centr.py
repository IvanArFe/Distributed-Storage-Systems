import json
import threading
import time
from concurrent import futures
import sys
import os
from threading import Semaphore

import grpc
from typing import Dict

# Adapt path to import proto files
sys.path.append(os.path.join(os.path.dirname(__file__) + '/../proto'))
import store_pb2
import store_pb2_grpc

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../eval')

#Class were we define our Master node which implements the KeyValueStoreServicer functions
class MasterServiceServicer(store_pb2_grpc.KeyValueStoreServicer):   
    def __init__(self):
        self.keyValueStore: Dict[str, str] = {} # Dictionary to store key value pairs
        # Read backup file in order to restore the state of the server
        if os.path.isfile("backup_centr.json"):
            with open("backup_centr.json", "r") as f:
                self.keyValueStore = json.load(f)

        self.slowDownActive = False # Boolean to check if the server is in slow mode
        self.slowDownSecs = 0 # Time to slow comunication beetwen servers (nodes)
        self.semaphore = Semaphore()
        self.port = 32770 # Port for the master node

        # List for discovery port ranges
        ports = []

        # Discovered ports (from documentation), this should be implemented with a method called portDiscovery()
        ports.append(32771)
        ports.append(32772)

        # Here we save the three stubs from each node
        self.stubs = []
        for port in ports:
            channel = grpc.insecure_channel(f"127.0.0.1:{port}") # Open a new channel for each node
            self.stubs.append(store_pb2_grpc.KeyValueStoreStub(channel))

    # This funtion returns corresponding value to a key if exists, if not return None
    def get(self, request: store_pb2.GetRequest, context: grpc.aio.ServicerContext) -> store_pb2.GetResponse:
        self.semaphore.acquire() 
        value = self.keyValueStore.get(request.key) # Obtain value from corresponding key
        self.semaphore.release()
        
        if value is None:
            resp = store_pb2.GetResponse(value=None, found=False) # If value is None, set found to False
        else:
            resp = store_pb2.GetResponse(value=value, found=True) # Else set value and found true
        
        if self.slowDownActive == True:
            # Add delay to slow down the communication as requested in documentation
            time.sleep(self.slowDownSecs)

        return resp

    # This function stores a key value for a given key
    def put(self, request: store_pb2.PutRequest, context: grpc.aio.ServicerContext) -> store_pb2.PutResponse:

        # First, master asks the other nodes if key value can be modified by creating a commit request
        commit_req = store_pb2.CommitRequest(key=request.key) # Create commit request

        node_resp = [] # List to store responses from nodes in order to know if they can modify the key value
        for stub in self.stubs:
            node_resp.append(stub.canCommit(commit_req)) # Send commit request to the slaves nodes and get their responses
        
        canCommit = True # Boolean to check if all nodes can modify the key value
        # If any node cannot modify the key value, save a False value in canCommit
        for resp in node_resp:
            if not resp:
                canCommit = False
        
        self.semaphore.acquire()
        if canCommit:
            put_value = store_pb2.PutRequest(key=request.key, value=request.value) # Create put request
            responses = [] # List to savbe responses from nodes in order to know if they have stored the key value correctly
            for stub in self.stubs:
                responses.append(stub.put(put_value)) # Send put request to the slaves nodes and get their responses
        
            all_Correct = True # Boolean to check if all nodes have stored the key value correctly
            for resp in responses:
                if not resp:
                    all_Correct = False

        if not all_Correct:
            print("Error in one of the nodes, key value not stored correctly")
            put_value = store_pb2.PutResponse(success=False) # If any node has stored the key value incorrectly, set correct to False
        else:
            # Here we knopw that all slaves nodes have modified value propperly, so we can modify the value in the master node
            self.keyValueStore[request.key] = request.value
            put_value = store_pb2.PutResponse(success=True) # Set correct to True
            # After modifying the key value, save the state of the server in a backup file in order to restore it if needed due to a failure
            with(open('backup_centr.json', 'w')) as f:
                json.dump(self.keyValueStore, f) # Save the state of the server in a backup file
         
        self.semaphore.release()

        if self.slowDownActive == True:
            # Add delay to slow down the communication as requested in documentation
            time.sleep(self.slowDownSecs)
        
        return put_value

    # Here we define can_commit function in order to check if a key value can be modified by the master node if all slaves nodes agree
    def canCommit(self, request: store_pb2, context: grpc.aio.ServicerContext) -> store_pb2.CommitResponse:
        self.semaphore.acquire()
        if request.key in self.keyValueStore: 
            resp = store_pb2.CommitResponse(success=True)
        else:
            resp = store_pb2.CommitResponse(success=False)
        self.semaphore.release()
        return resp

    # This function add delay to the communication between nodes with the value seconds in request
    def slowDown(self, request: store_pb2.SlowDownRequest, context: grpc.aio.ServicerContext) -> store_pb2.SlowDownResponse:
        self.slowDownActive = True # Set slowDown to True
        self.slowDownSecs = request.seconds # Set the time to slow down the communication
        return store_pb2.SlowDownResponse(success=True)

    # Restore to default values in order to drop delays in communication
    def restore(self, request: store_pb2.RestoreRequest, context: grpc.aio.ServicerContext) -> store_pb2.RestoreResponse:
        self.slowDownActive = False # Set slowDown to False
        self.slowDownSecs = 0 # Set the time to slow down the communication to 0
        return store_pb2.RestoreResponse(success=True)
    
def master_node():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10)) # Create a new gRPC server
    store_pb2_grpc.add_KeyValueStoreServicer_to_server(MasterServiceServicer(), server) # Add previous class to the server

    print("[!] Starting Master Server. Listening on port 32770") # Print message to show that the server is running
    server.add_insecure_port('127.0.0.1:32770') # Set the port for the server, specified in documentation
    server.start() # Start the server
    server.wait_for_termination() # Wait for termination

def main():
    master_node() # Call master_node function
    
if __name__ == '__main__':
    main() # Call main function