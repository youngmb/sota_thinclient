# package-level defaults

# UDP sending and receiving
udp_timeout = 0.2
reorder_window = 5   # how many packets to buffer while waiting for in-order packet
UDP_SEQUENCE_MAX = 100   # sequence numbering rollover point. must match the sota thin server


# Sota mic
SOTA_MIC_SAMPLERATE = 16000   # must match what the server sends
SOTA_MIC_CHANNELS = 1   # mono
SOTA_MIC_DATATYPE = 'int16'

# simplify the main imports
from .connection_manager import ConnectionManager
