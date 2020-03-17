#!/usr/bin/python3.7

import sys
from Peer import Peer

ID_SPACE = 256

if __name__ == "__main__":
    def _(): # Argument parser
        global TYPE, PEER, FIRST_SUCCESSOR, SECOND_SUCCESSOR, PING_INTERVAL
        try:
            _, TYPE, PEER, FIRST_SUCCESSOR, SECOND_SUCCESSOR, PING_INTERVAL = sys.argv

            if TYPE.lower() not in ["init", "join"]:
                print("Type must be `init` or `join`")
                return

            PEER = int(PEER)
            FIRST_SUCCESSOR = int(FIRST_SUCCESSOR)
            SECOND_SUCCESSOR = int(SECOND_SUCCESSOR)

            if PEER | FIRST_SUCCESSOR | SECOND_SUCCESSOR >= ID_SPACE:
                print(f"Peer IDs must be from 0 to {ID_SPACE-1} (inclusive)")
                return

            PING_INTERVAL = int(PING_INTERVAL)

        except Exception as e:
            print(f"Usage: {sys.argv[0]} <TYPE> <PEER> <FIRST_SUCCESSOR> <SECOND_SUCCESSOR> <PING_INTERVAL>")
        else:
            return True
    _() or sys.exit(1)


a = Peer(PEER,FIRST_SUCCESSOR, SECOND_SUCCESSOR, PING_INTERVAL)
print(a)