import portUtils

import socket
import threading
import time
from select import select

class Peer:
    def __init__(self, peer_id: int, first_successor: int, second_successor: int, ping_interval: int):
        self.__id = peer_id
        self.first_successor = first_successor
        self.second_successor = second_successor
        self.ping_interval = ping_interval

        self.__lastPing = 0
        self.__pingInfo = {}

        self.__dprint(f"I am Peer #{self.__id}")
        threading.Thread(target=self.ping_server).start()

    def __repr__(self):
        return f"(Peer[{self.__id}]->{self.first_successor}->{self.second_successor})"

    def ready(self):
        threading.Thread(target=self.ping_client).start()


    # Respond to ping requests on UDP port `UDP_BASE_PORT + id`
    def ping_server(self):
        LISTEN_PORT = portUtils.calculate_UDP_port(self.__id)

        self.__dprint("Listening for ping requests on UDP:", LISTEN_PORT)
        server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('', LISTEN_PORT))
        while True:
            (data, addr) = server.recvfrom(1024)
            data = data.decode()
            self.__dprint(f"> Ping request message received from Peer {data}")
            server.sendto(str(self.__id).encode(), addr)

    def ping_client(self):
        c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        c.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        while True:
            ctime = time.time()
                
            # Check if a new periodic ping is needed
            if ctime - self.__lastPing > 10:
                self.__lastPing = ctime
                for peerID in [self.first_successor, self.second_successor]:
                    c.sendto(str(self.__id).encode(), ('localhost', portUtils.calculate_UDP_port(peerID)))

                self.__dprint(f"> Ping requests sent to Peers {self.first_successor} and {self.second_successor}")

            # Check for replies
            while select([c], [], [], 10)[0]:
                (data, addr) = c.recvfrom(1024)
                data = data.decode()
                # data => peerID
                self.__pingInfo[data] = time.time()
                self.__dprint(f"> Ping response received from Peer {data}")

            # Check if last response was more than 10 seconds
            ctime = time.time()
            for peerID in [self.first_successor, self.second_successor]:
                if ctime - self.__pingInfo[data] > 10:
                    self.__dprint(f"Peer {data} is no longer alive")

    @property
    def id():
        return self.__id
    
    def __dprint(self, *args, **kwargs):
        print(f"[{self.__id}]", *args, **kwargs)
