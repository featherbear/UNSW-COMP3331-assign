#!/usr/bin/python3.7

from Peer import Peer
from argParser import _
import sys

ID_SPACE = 256

if __name__ == "__main__":
    args = _(ID_SPACE) or sys.exit(1)

    if args[0] == "join":
        PEER, KNOWN_PEER, PING_INTERVAL = args[1:]
        p = Peer(PEER, PING_INTERVAL)
        p.join(KNOWN_PEER)
        print(p)
        
    elif args[0] == "init":
        PEER, FIRST_SUCCESSOR, SECOND_SUCCESSOR, PING_INTERVAL = args[1:]
        p = Peer(PEER, PING_INTERVAL)
        p.setup(FIRST_SUCCESSOR, SECOND_SUCCESSOR)
        print(p)

