#!/usr/bin/python3.7

from lib.Peer import Peer
from lib.argParser import _
import sys
import time

import threading

ID_SPACE = 256

if __name__ == "__main__":
    args = _(ID_SPACE) or sys.exit(1)

    ready = False
    def callback(*_, **__):
        global ready
        ready = True

    if args[0] == "join":
        PEER, KNOWN_PEER, PING_INTERVAL = args[1:]
        p = Peer(PEER, PING_INTERVAL)
        p.join(KNOWN_PEER, callback=callback)
        
    elif args[0] == "init":
        PEER, FIRST_SUCCESSOR, SECOND_SUCCESSOR, PING_INTERVAL = args[1:]
        p = Peer(PEER, PING_INTERVAL)
        p.setup(FIRST_SUCCESSOR, SECOND_SUCCESSOR, callback=callback)
        p.ready()
        
    print("Launched peer:", p)
    
    while not ready:
        time.sleep(0.5)

    line = None
    def getLine(prompt: str) -> str:
        global line
        line = input(prompt)
        return line or " "

    while getLine("> "):
        tokens = line.split(" ")
        command = tokens[0].lower()
        if command == "store":
            if len(tokens) != 2:
                print("Usage: Store <4-digit filename>")
                continue
            p.store(tokens[1])
            continue

        if command == "request":
            if len(tokens) != 2:
                print("Usage: Request <4-digit filename>")
                continue
            p.request(tokens[1])
            continue

        if command == "quit":
            p.quit()
            sys.exit()