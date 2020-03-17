UDP_BASE_PORT = 12000

def calculate_UDP_port(offset: int) -> int:
    return UDP_BASE_PORT + offset

