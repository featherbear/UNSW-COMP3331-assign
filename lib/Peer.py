from . import portUtils

import socket
import threading
import time
from select import select
import re
import sys

SHOW_PING_REQUEST = False
SHOW_PING_RESPONSE = False

# TODO - Flags to check if the Peer is connected

class Peer:
    def __init__(self, peer_id: int, ping_interval: int):
        self.__id = peer_id

        self.first_successor = None
        self.second_successor = None
        self.first_predecessor = None
        self.second_predecessor = None

        self.ping_interval = ping_interval

        self.isConnected = False

        self.__lastPing = 0
        self.__pingInfo = {}

        self._connections = []
        self._connectionsMetadata = {}

        self.__dprint(f"I am Peer #{self.id}")

        threading.Thread(target=self.__serverFn, daemon=True).start()
        threading.Thread(target=self.__pingServerFn, daemon=True).start()
        
    def __repr__(self):
        return f"(Peer[{self.id}]->{self.first_successor}->{self.second_successor})"
    
    def ___sendTCP(self, peerID: int, data):
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.connect(('127.0.0.1', portUtils.calculate_port(peerID)))
        conn.sendall(data)
        conn.close()

    def ___closeTCP(self, conn: socket.socket) -> bool:
        if conn in self._connections:
            metadata = self._connectionsMetadata.get(conn, False)
            if metadata:
                if "fileHandle" in metadata:
                    metadata["fileHandle"].close()
                del self._connectionsMetadata[conn]
            
            conn.close()
            self._connections.remove(conn)
            return True

        return False

    def join(self, known_peer: int):
        if self.isConnected:
            return False

        self.___sendTCP(known_peer, f"join|{self.id}".encode())

    def setup(self, first_successor: int, second_successor: int):
        self.first_successor = first_successor
        self.second_successor = second_successor
        self.isConnected = True

    def ready(self):
        threading.Thread(target=self.ping_client, daemon=True).start()

    def __serverFn(self):
        self.__serverRunning = True
        LISTEN_PORT = portUtils.calculate_port(self.id)

        self.__dprint(f"Listening for connections on TCP:{LISTEN_PORT}")
        
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('', LISTEN_PORT))
        server.listen()

        while self.__serverRunning:
            for readableSock in select([server, *self._connections], [], [], 1)[0]:
                if readableSock is server:
                    (sock, addr) = server.accept()
                    self._connections.append(sock)
                    # Read from this socket on the next `select`
                    continue
            
                data = readableSock.recv(1024)
                
                if not data:
                    # Close and remove dead connections
                    self.___closeTCP(readableSock)
                    continue
                
                if readableSock in self._connectionsMetadata:
                    metadata = self._connectionsMetadata[readableSock]

                    metadata["bytesLeft"] -= metadata["fileHandle"].write(data)
                    
                    if metadata["bytesLeft"] == 0:
                        self.__dprint(f"File {metadata['filename']} received")
                        metadata["fileHandle"].close()
                        del self._connectionsMetadata[readableSock]

                    continue

                info = data.split(b"|")
                command = info[0].decode().lower()

                if command == "join":
                    info = [*map(lambda b: b.decode(), info)]
                    newPeerID = int(info[1])
                    if newPeerID in [self.id, self.first_successor, self.second_successor]:
                        # drop if new peer claims to be an existing peer
                        self.__dprint(f"> Peer {newPeerID} trying to join, but peer ID conflicts")
                        self.___closeTCP(readableSock)
                        continue

                    if newPeerID < self.id:
                        # drop if the new peer precedes the current peer
                        self.__dprint(f"> Ignoring join request from Peer {newPeerID} - newPeerID < self.id")
                        self.___closeTCP(readableSock)
                        continue

                    if newPeerID > self.id:
                        if newPeerID < self.first_successor or self.first_successor < self.id:
                            self.__dprint(f"> Peer {newPeerID} Join request received")
                            
                            self.___sendTCP(newPeerID, f"offer|{self.first_successor}|{self.second_successor}".encode())

                            if self.first_predecessor is not None:
                                self.___sendTCP(self.first_predecessor, f"secondsuccessor|{newPeerID}".encode())

                            self.second_successor = self.first_successor
                            self.first_successor = newPeerID
                            self.__dprint(f"> My first successor is Peer {self.first_successor}")
                            self.__dprint(f"> My second successor is Peer {self.second_successor}")

                        else:
                            self.__dprint(f"Peer {newPeerID} Join request forwarded to my successor")
                            self.___sendTCP(self.first_successor, data)

                elif command == "offer":
                    info = [*map(lambda b: b.decode(), info)]
                    self.setup(*map(int, info[1:]))
                    self.__dprint("> Join request has been accepted")
                    self.__dprint(f"> My first successor is Peer {self.first_successor}")
                    self.__dprint(f"> My second successor is Peer {self.second_successor}")
                    self.ready()

                elif command == "secondsuccessor":
                    info = [*map(lambda b: b.decode(), info)]
                    self.second_successor = int(info[1])
                    self.__dprint(f"> Successor Change request received")
                    self.__dprint(f"> My new first successor is Peer {self.first_successor}")
                    self.__dprint(f"> My new second successor is Peer {self.second_successor}")
                
                elif command == "store":
                    info = [*map(lambda b: b.decode(), info)]
                    if len(info) == 3:
                        self.store(info[1], info[2])
                elif command == "request":
                    info = [*map(lambda b: b.decode(), info)]
                    if len(info) == 3:
                        self.request(info[1], info[2])
                elif command == "file":
                    _, peer, filename, dataLength, data = data.split(b"|", 4)
                    
                    peer = peer.decode()
                    filename = filename.decode()
                    dataLength = int(dataLength.decode())
                    
                    self.__dprint(f"> Peer {peer} had File {filename}")
                    
                    f = open(f"received_{filename}.pdf", "wb")

                    metadata = dict(
                        filename = filename,
                        fileHandle = f,
                        bytesLeft = dataLength,
                    )

                    metadata["bytesLeft"] -= f.write(data)
                    self._connectionsMetadata[readableSock] = metadata
                elif command == "quit":
                    info = [*map(lambda b: b.decode(), info)]
                    peer, first_successor, second_successor = map(int,info[1:4])

                    self.__dprint(f"> Peer {peer} will depart from the network")
                    if peer == self.first_successor:
                        self.first_successor = first_successor
                        self.second_successor = second_successor
                    elif peer == self.second_successor:
                        self.second_successor = first_successor

                    self.__dprint(f"My new first successor is Peer {self.first_successor}")
                    self.__dprint(f"My new second successor is Peer {self.second_successor}")
                    
        server.close()

    def __pingServerFn(self):
        self.__pingServerRunning = True

        LISTEN_PORT = portUtils.calculate_port(self.id)

        self.__dprint(f"Listening for ping requests on UDP:{LISTEN_PORT}")
        self.___pingServer = server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('', LISTEN_PORT))

        while self.__pingServerRunning:
            if select([server], [], [], 1)[0]:
                (data, addr) = server.recvfrom(1024)
                info = data.decode().split("|")
                if len(info) > 1 and int(info[1]) == self.id:
                    if self.first_predecessor is None:
                        self.__dprint("> Circular DHT established")
                    self.first_predecessor = int(info[0])
                if len(info) > 2 and int(info[2]) == self.id:
                    if self.second_predecessor is None:
                        self.__dprint("> Second predecessor determined")
                    self.second_predecessor = int(info[0])
                SHOW_PING_REQUEST and self.__dprint(
                    f"> Ping request message received from Peer {info[0]}")

                string = f"{self.id}"
                if self.first_successor: string += f"|{self.first_successor}"
                if self.second_successor: string += f"|{self.second_successor}"
                server.sendto(string.encode(), addr)
        
        server.close()

    def __sendPing(self, *, peerID=None, ctime=None):
        # stub.
        # Gets overriden when ping_client spawns
        raise NotImplementedError("STUB")

    def ping_client(self):
        c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        c.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        def sendPing(*, peerID=None, ctime=None):
            if ctime is None:
                ctime = time.time()
            if peerID is None:
                self.__lastPing = ctime
            for peerID in [peerID] if peerID else [self.first_successor, self.second_successor]:
                if peerID is not None:
                    string = f"{self.id}"
                    if self.first_successor: string += f"|{self.first_successor}"
                    if self.second_successor: string += f"|{self.second_successor}"
                    c.sendto(string.encode(), ('localhost', portUtils.calculate_port(peerID)))

        self.__sendPing = sendPing

        while True:

            # Check if a new periodic ping is needed
            ctime = time.time()
            if ctime - self.__lastPing > 10:
                sendPing(ctime=ctime)
                SHOW_PING_REQUEST and self.__dprint(
                    f"> Ping requests sent to Peers {self.first_successor} and {self.second_successor}")

            # Check for replies
            while select([c], [], [], 10)[0]:
                (data, addr) = c.recvfrom(1024)
                info = data.decode().split("|")
                info = [*map(int, info)]

                try:
                    self.__pingInfo[info[0]] = time.time()
                    SHOW_PING_RESPONSE and self.__dprint(f"> Ping response received from Peer {info[0]}")

                    if info[0] == self.first_successor and self.second_successor is None:
                        self.second_successor = info[1]
                        
                except:
                    pass

            # Check if last response was a while ago
            ctime = time.time()
            for peerID in [self.first_successor, self.second_successor]:
                if peerID is None:
                    continue
                if peerID not in self.__pingInfo: 
                    self.__pingInfo[peerID] = ctime
                    continue
                if ctime - self.__pingInfo[peerID] < min(max(20, self.ping_interval * 4), self.ping_interval * 4):
                    continue

                self.__dprint(f"Peer {peerID} is no longer alive")
                if peerID == self.first_successor:
                    self.first_successor = self.second_successor
                    self.second_successor = None
                    self.__sendPing(peerID = self.first_successor)
                else: # peerID == self.second_successor
                    self.second_successor = None
                    pass


    def store(self, filename, requestor=None):
        requestor = requestor or self.id

        # TODO: Possibly ^\d{4}$
        if not re.match("^\d{1,4}$", filename):
            return False
  
        _filename = int(filename)
        _hash = _filename % 256

        if any([
            _hash == self.id,
            self.first_predecessor and self.id < self.first_predecessor and (_hash > self.first_predecessor or _hash < self.id),
            self.first_predecessor and _hash > self.first_predecessor and _hash < self.id
        ]):
            self.__dprint(f"> Store {_filename} request accepted")
        else:
            self.__dprint(f"> Store {_filename} request forwarded to my successor")

            """ # This here will enable DHT shortcuts, but it is not asked within the assignment specifications """
            # if hash > self.first_successor:
            #     self.___sendTCP(self.second_successor, f"store|{_filename}|{requestor}".encode())
            # else:
            #     self.___sendTCP(self.first_successor, f"store|{_filename}|{requestor}".encode())
            """ # END """
            self.___sendTCP(self.first_successor, f"store|{_filename}|{requestor}".encode())

    def request(self, filename, requestor=None):
        requestor = requestor or self.id

        # TODO: Possibly ^\d{4}$
        if not re.match("^\d{1,4}$", filename):
            print("NO MATCH")
            return False
  
        _filename = int(filename)
        _hash = _filename % 256

        _requestor = int(requestor)

        if any([
            _hash == self.id,
            self.first_predecessor and self.id < self.first_predecessor and (_hash > self.first_predecessor or _hash < self.id),
            self.first_predecessor and _hash > self.first_predecessor and _hash < self.id
        ]):

            self.__dprint(f"> File {filename} is stored here")

            if self.id == _requestor:
                self.__dprint("Yeah well, i have it...")
                return

            self.__dprint(f"> Sending file {filename} to Peer {_requestor}")
            self.sendFile(_requestor, filename.zfill(4))
        else:
            if self.id == requestor:
                self.__dprint(f"> File request for {filename} has been sent to my successor")
            else:
                self.__dprint(f"> Request for File {filename} has been received, but the file is not stored here")

            """ # This here will enable DHT shortcuts, but it is not asked within the assignment specifications """
            # if hash > self.first_successor:
            #     self.___sendTCP(self.second_successor, f"request|{filename}|{requestor}".encode())
            # else:
            #     self.___sendTCP(self.first_successor, f"request|{filename}|{requestor}".encode())
            """ # END """
            self.___sendTCP(self.first_successor, f"request|{filename}|{requestor}".encode())

    def sendFile(self, peerID: int, filename: str):
        with open(filename + ".pdf", "rb") as f:
            data = f.read()
            dataLength = len(data) # struct pack me?

            self.___sendTCP(peerID, f"file|{self.id}|{filename}|{dataLength}|".encode() + data)
        self.__dprint("> The file has been sent")

    def quit(self):
        payload = f"quit|{self.id}|{self.first_successor}|{self.second_successor}".encode()

        if self.first_predecessor is not None: self.___sendTCP(self.first_predecessor, payload)
        if self.second_predecessor is not None: self.___sendTCP(self.second_predecessor, payload)
        
        self.__serverRunning = False
        self.__pingServerRunning = False

    @property
    def id(self):
        return self.__id

    def __dprint(self, *args, **kwargs):
        print(f"[{self.id}]", *args, **kwargs)
