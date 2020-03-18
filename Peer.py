import portUtils

import socket
import threading
import time
from select import select

SHOW_PING_REQUEST = False
SHOW_PING_RESPONSE = False

# TODO - Flags to check if the Peer is connected


class Peer:
    def __init__(self, peer_id: int, ping_interval: int):
        # first_successor: int, second_successor: int,

        self.__id = peer_id

        self.first_successor = None
        self.second_successor = None
        self.predecessor = None

        self.ping_interval = ping_interval

        self.isConnected = False

        self.__lastPing = 0
        self.__pingInfo = {}

        self._connections = []

        self.__dprint(f"I am Peer #{self.id}")
        threading.Thread(target=self.ping_server).start()
        threading.Thread(target=self.server).start()

    def __repr__(self):
        return f"(Peer[{self.id}]->{self.first_successor}->{self.second_successor})"
    
    def ___sendTCP(self, peerID: int, data):
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.connect(('127.0.0.1', portUtils.calculate_port(peerID)))
        conn.sendall(data)
        conn.close()

    def ___closeTCP(self, conn: socket.socket) -> bool:
        if conn in self._connections:
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

    def ready(self):
        threading.Thread(target=self.ping_client).start()

    def server(self):
        LISTEN_PORT = portUtils.calculate_port(self.id)

        self.__dprint(f"Listening for connections on TCP:{LISTEN_PORT}")
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('', LISTEN_PORT))
        server.listen()

        while True:
            for readableSock in select([server, *self._connections], [], [])[0]:
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

                info = data.decode().split("|")
                command = info[0].lower()

                if command == "join":
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

                            if self.predecessor is not None:
                                self.___sendTCP(self.predecessor, f"secondsuccessor|{newPeerID}".encode())

                            self.second_successor = self.first_successor
                            self.first_successor = newPeerID
                            self.__dprint(f"> My first successor is Peer {self.first_successor}")
                            self.__dprint(f"> My second successor is Peer {self.second_successor}")

                        else:
                            self.__dprint(f"Peer {newPeerID} Join request forwarded to my successor")
                            self.___sendTCP(self.first_successor, data)

                elif command == "offer":
                    self.setup(*map(int, info[1:]))
                    self.__dprint("> Join request has been accepted")
                    self.__dprint(f"> My first successor is Peer {self.first_successor}")
                    self.__dprint(f"> My second successor is Peer {self.second_successor}")
                    self.ready()
                    # self.isConnected = True

                elif command == "secondsuccessor":
                    self.second_successor = int(info[1])
                    self.__dprint(f"> Successor Change request received")
                    self.__dprint(f"> My new first successor is Peer {self.first_successor}")
                    self.__dprint(f"> My new second successor is Peer {self.second_successor}")

    def ping_server(self):
        LISTEN_PORT = portUtils.calculate_port(self.id)

        self.__dprint(f"Listening for ping requests on UDP:{LISTEN_PORT}")
        server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('', LISTEN_PORT))

        while True:
            (data, addr) = server.recvfrom(1024)
            info = data.decode().split("|")

            if len(info) > 1 and int(info[1]) == self.id:
                # predecessor
                # TODO: ref `e`
                self.predecessor = int(info[0])
            SHOW_PING_REQUEST and self.__dprint(
                f"> Ping request message received from Peer {info[0]}")
            server.sendto(str(self.id).encode(), addr)

    def ping_client(self):
        c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        c.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        while True:

            # Check if a new periodic ping is needed
            ctime = time.time()
            if ctime - self.__lastPing > 10:
                self.__lastPing = ctime
                for peerID in [self.first_successor, self.second_successor]:
                    c.sendto(f"{self.id}|{self.first_successor}|{self.second_successor}".encode(
                    ), ('localhost', portUtils.calculate_port(peerID)))

                SHOW_PING_REQUEST and self.__dprint(
                    f"> Ping requests sent to Peers {self.first_successor} and {self.second_successor}")

            # Check for replies
            while select([c], [], [], 10)[0]:
                (data, addr) = c.recvfrom(1024)
                data = data.decode()
                self.__pingInfo[data] = time.time()
                SHOW_PING_RESPONSE and self.__dprint(
                    f"> Ping response received from Peer {data}")

            # Check if last response was more than 10 seconds
            ctime = time.time()
            for peerID in [self.first_successor, self.second_successor]:
                if ctime - self.__pingInfo[data] < self.ping_interval * 4:
                    continue
                self.__dprint(f"Peer {data} is no longer alive")

    @property
    def id(self):
        return self.__id

    def __dprint(self, *args, **kwargs):
        print(f"[{self.id}]", *args, **kwargs)
