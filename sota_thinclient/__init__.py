# package-level defaults

# UDP sending and receiving
udp_timeout = 0.2
reorder_window = 5   # how many packets to buffer while waiting for in-order packet.
image_age_max = 3    # when receiving images, how many do we buffer waiting for an old one to complete
UDP_SEQUENCE_MAX = 1000000   # sequence numbering rollover point. must match the sota thin server

# simplify the main imports
from .connection_manager import ConnectionManager
