import json
import string
from threading import Semaphore
import time
from concurrent import futures
import sys
import os
import socket

import grpc
from typing import Dict

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../proto')

import store_pb2
import store_pb2_grpc

# Define class which implements methods from store_pb2_grpc.KeyValueStoreServicer
class ServerDescServicer(store_pb2_grpc.KeyValueStoreServicer):
    def __init__(self, port, weight):
        self.keyValueStore: Dict[str, str] = {} # Server Dictionary to store key value pairs
        if os.path.isfile("backup_decen.json"):
            with open("backup_decen.json", "r") as f:
                self.keyValueStore = json.load(f)

        self.slowDown = False # Boolean to check if the server is in slow mode
        self.slowDownSecs = 0 # Time to slow comunication beetwen servers (nodes)
        self.semaphore = Semaphore()
        self.port = port
        self.weight = weight
        self.read_quo = 2 # Maximum quorum for read 
        self.write_quo = 3 # Maximum quorum for write

       
        # Discovery port ranges
        ports = []

        # Discovered ports (from documentation)
        ports.append(32771)
        ports.append(32772)

        # Here we save the three stubs from each node
        self.stubs = []
        for port in ports:
            channel = grpc.insecure_channel(f"localhost:{port}") # Open a new channel for each node
            self.stubs.append(store_pb2_grpc.KeyValueStoreStub(channel))
    
    def askVote(self, request: store_pb2, context: grpc.aio.ServicerContext) -> store_pb2.PutResponse:
        return store_pb2.VoteResponse(weight=self.weight)
    
    def doCommit(self, request: store_pb2.PutRequest, context: grpc.aio.ServicerContext) -> store_pb2.PutResponse:
        self.semaphore.acquire()
        self.keyValueStore[request.key] = request.value # Obtain key value from request
        self.semaphore.release()
        return store_pb2.PutResponse(success=True) # Return True to let commit be done
    
    # This function saves the value from a specific key
    def put(self, request, context):
        vote_req = store_pb2.VoteRequest(key=request.key) # Create a vote request

        # Prepare to send VoteCommit requests to other nodes (servers)
        resp = []
        total_weight = self.weight

        for stub in self.stubs:
            if(total_weight < self.write_quo): # Check if we haven't reached maximum quorum for write
                try: 
                    response = stub.askVote(vote_req)
                    total_weight += response.weight
                    resp.append(response)
                except Exception as e:
                    context.set_details(f'Error in askVote: {str(e)}')
                    context.set_code(grpc.StatusCode.INTERNAL)
                    return store_pb2.PutResponse(success=False)
        
        if (total_weight >= self.write_quo): # If we have reached maximum quorum for write we are ready to commit
            # Send commit request to other nodes (servers)
            put_value = store_pb2.PutRequest(key=request.key, value=request.value)
            resp = []
            for stub in self.stubs:
                try:
                    response = stub.doCommit(put_value)
                    resp.append(response)
                except Exception as e:
                    context.set_details(f'Error in doCommit: {str(e)}')
                    context.set_code(grpc.StatusCode.INTERNAL)
                    return store_pb2.PutResponse(success=False)
                
            # Check if all nodes have update value correctly. If not, put_value store a response with success=False
            allCorrect = True
            for response in resp:
                if not response:
                    allCorrect = False
        
            if not allCorrect:
                put_value = store_pb2.PutResponse(success=False)
            else:
                # If all is correct, store the value in the server and save a backup in a file
                self.semaphore.acquire()
                try:
                    self.keyValueStore[request.key] = request.value
                    with open('backup_decen.json', 'w') as f:
                        json.dump(self.keyValueStore, f)
                    put_value = store_pb2.PutResponse(success=True) # Return True to let commit be done
                finally:
                    self.semaphore.release()
        else:
            put_value = store_pb2.PutResponse(success=False)

        if self.slowDown:
            time.sleep(self.slowDownSecs) # Add delay to slow down the communication
        
        return put_value

    def get(self, request: store_pb2.GetRequest, context: grpc.aio.ServicerContext) -> store_pb2.GetResponse:
        vote_req = store_pb2.VoteRequest(key=request.key) # Create a vote request

        resp = []
        total_weight = self.weight

        for stub in self.stubs:
            if(total_weight < self.read_quo): # Check if we haven't reached maximum quorum for read
                response = stub.askVote(vote_req)
                total_weight += response.weight
                resp.append(response)
        
        self.semaphore.acquire()
        # If we have reached the value of read quorum, we can obtain the value from the key, else we cannot continue
        if(total_weight >= self.read_quo):
            get_value = self.keyValueStore.get(request.key) # Obtain value from corresponding key
        else :
            get_value = None
        self.semaphore.release()

        # If value is not null, return it and set found to True, else set found to False
        if get_value is None:
            response = store_pb2.GetResponse(value=None, found=False)
        else:
            response = store_pb2.GetResponse(value=get_value, found=True)
        
        if self.slowDown:
            time.sleep(self.slowDownSecs) # Add delay to slow down the communication
        
        return response
    
    # This method decides if the server can commit a key value
    def canCommit(self, request: store_pb2, context: grpc.aio.ServicerContext) -> store_pb2.CommitResponse:
        return store_pb2.CommitResponse(success=True) # Return True to let commit be done
    
    # This function add delay to the communication between nodes with the value seconds in request
    def slowDown(self, request: store_pb2.SlowDownRequest, context: grpc.aio.ServicerContext) -> store_pb2.SlowDownResponse:
        self.slowDown = True
        self.slowDownSecs = request.seconds # Delay request.seconds the communication
        return store_pb2.SlowDownResponse(success=True)
    
    # This function restores the server to its initial state, without delay
    def restore(self, request: store_pb2.RestoreRequest, context: grpc.aio.ServicerContext) -> store_pb2.RestoreResponse:
        self.slowDown = False
        self.slowDownSecs = 0
        return store_pb2.RestoreResponse(success=True)
    
def server(port, weight):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    store_pb2_grpc.add_KeyValueStoreServicer_to_server(ServerDescServicer(port, weight), server) # Add defined class to server

    # Server will start listening on one of this ports 32770, 32771, 32772
    print(f"Starting server. Listening on port {port}.")
    server.add_insecure_port(f"localhost:{port}")
    server.start()
    server.wait_for_termination()

def main(port, weight):
    server(port, weight)
    while True:
        pass

if __name__ == '__main__':
    main(sys.argv[1]) # Call main function --> argv[1] will be the port number