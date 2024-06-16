# Distributed-Storage-Systems
In this project you can test and run two examples of a Distributed System Storage, key-value one, based on centralised and decentralised implementations built using python and gRPC to deal with comunication between nodes. 
In the centralised one, there is one master node to deal with writing functions and two more nodes that are slaves. All of them can handle reading operations. On the other hand, in the decentralised implementation, there are also three nodes but all of them are equal so they can manage writing and reading operations. 

To test it, you can just run the eval.py, which runs both tests files and returns obtained results for each implementation. If you want to run it independently you can just run each test file separetly and analyze obtained results as well.

# Steps to clone and run the project by steps
1- Clone this GitHub repository on your pc or laptop: 'https://github.com/IvanArFe/Distributed-Storage-Systems.git' 
2- Check if you have Python installed, if you already have it go to next step, otherwise:
    2.1- In Linux, you can run 'apt install python3' command.
    2.2- In Windows, you can download it from Microsoft Store.
3- Install grpc tools to deal with gRPC comunications runing this command: 'pip install grpcio grpcio-tools'. If you don't have pip installed, in Lunix you can run 'python -m pip install --upgrade pip' and in windows downloadit from here: https://bootstrap.pypa.io/pip/pip.pyz 
4- Compile .proto file with this command: 'python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. --pyi_out=. your_file.proto'
5- Open a new terminal and go to eval directory to run tests separetly or go to SD-Task2 directory and run eval.py file.