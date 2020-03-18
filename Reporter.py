from Peer import Peer
import time
import sys
import os
import threading

class Reporter:
    def __init__(self, delay):
        sys.stdout = open(os.devnull, 'w')

        self.peers = []
        self.delay = delay
    
    def run(self):
        thread = threading.Thread(target=self.___run).start()
        
    def ___run(self):
        while True:
            time.sleep(self.delay)

            builder = []
            builder.append("===============")
            for peer in self.peers:
                builder.append(f"Peer {peer.id} - Online")
            builder.append("===============")
            os.system("clear")
            print("\n".join(builder), file=sys.__stdout__)
                        
    def register(self, peer: Peer):
        if peer not in self.peers:
            self.peers.append(peer)
    

