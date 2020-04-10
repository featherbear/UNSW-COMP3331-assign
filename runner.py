#!/usr/bin/python3

PING_INTERVAL = 3

REPORTER = False
REPORTER_INTERVAL = 1

###

from lib.Peer import Peer

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

from lib.Reporter import Reporter
reporter = Reporter(REPORTER_INTERVAL)

def _setup(PEER: int, FIRST_SUCCESSOR: int, SECOND_SUCCESSOR: int, PING_INTERVAL: int):
    peer = Peer(PEER, PING_INTERVAL)
    peer.setup(FIRST_SUCCESSOR, SECOND_SUCCESSOR)
    if REPORTER: reporter.register(peer)
    return peer

nodes = [*map(lambda nodeInfo: _setup(*nodeInfo, PING_INTERVAL), nodes)]

print(nodes)

for node in nodes:
    node.ready()

if REPORTER:
    reporter.run()

import time
while True:
    time.sleep(0.1)