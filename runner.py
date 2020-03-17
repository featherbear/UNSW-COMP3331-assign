#!/usr/bin/python3

PING_INTERVAL = 30

###

from Peer import Peer

nodes = [
    # ID 1st 2nd
    ( 2,  4,  5),
    ( 4,  5,  8),
    ( 5,  8,  9),
    ( 8,  9, 14),
    ( 9, 14, 19),
    (14, 19,  2),
    (19,  2,  4)
]

nodes = [*map(lambda nodeInfo: Peer(*nodeInfo, PING_INTERVAL), nodes)]

print(nodes)

for node in nodes:
    node.ready()