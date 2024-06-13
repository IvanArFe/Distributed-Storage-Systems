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
        self.keyValueStore: Dict[string, string] = {} # Server Dictionary to store key value pairs
        self.slowDown = False # Boolean to check if the server is in slow mode
        self.slowDownSecs = 0 # Time to slow comunication beetwen servers (nodes)
        self.semaphore = Semaphore()
        self.port = port
        self.weight = weight
        self.read_quo = 2 # Maximum quorum for read 
        self.write_quo = 3 # Maximum quorum for write

        if os.path.isfile("backup_decen.json"):
            with open("backup_decen.json", "r") as f:
                self.keyValueStore = json.load(f)

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
                response = stub.askVote(vote_req)
                total_weight += response.weight
                resp.append(response)
        
        if (total_weight >= self.write_quo): # If we have reached maximum quorum for write we are ready to commit
            # Send commit request to other nodes (servers)
            put_value = store_pb2.PutRequest(key=request.key, value=request.value)
            resp = []
            for stub in self.stubs:
                response = stub.doCommit(put_value)
                resp.append(response)
        
        # Check if all nodes have update value correctly. If not, put_value store a response with success=False
        allCorrect = False
        for response in resp:
            if not response:
                allCorrect = False
        
        if not allCorrect:
            put_value = store_pb2.PutResponse(success=False)
        else:
            # If all is correct, store the value in the server and save a backup in a file
            self.semaphore.acquire()
            self.keyValueStore[request.key] = request.value
            with open("backup_decen.json", "w") as f:
                json.dump(self.keyValueStore, f)
            self.semaphore.release()
            put_value = store_pb2.PutResponse(success=True) # Return True to let commit be done

        if self.slowDown:
            time.sleep(self.slowDownSecs) # Add delay to slow down the communication
        
        return put_value
