# UNSW COMP3331 20T1 Assignment - Distributed Hash Table

## Overview

This repository contains Python 3 code towards building a basic Distributed Hash Table network; which implements rudimentary peer management and data transfer services.

The report can be found in [report.pdf](./report.pdf)

## Usage

### P2P Client - `p2p.py`

The `p2p.py` file is the main entry point to the program

#### Initialising nodes of a new network

Usage: `python3 p2p.py join <PEER> <FIRST_SUCCESSOR> <SECOND_SUCCESSOR> <PING_INTERVAL>`

#### Joining an existing network

Usage: `python3 p2p.py join <PEER> <KNOWN_PEER> <PEER_INTERVAL>`

### Network Launcher - `runner.py`

The `runner.py` file initialises a network with 7 nodes.  
_(2, 4, 5, 8, 9, 14 and 19_ as per the assignment outline)_

Usage: `python3 runner.py`

#### Reporter Mode

If launched with the `-r` flag, the reporter mode is entered.  
Each node initialised with the launcher will be inspected for their predecessors and successors.

Usage: `python3 runner.py -r`

