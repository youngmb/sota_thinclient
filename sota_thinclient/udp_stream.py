# sota-thinclient/udp_stream.py
import socket
import struct
import threading
import heapq
from queue import Empty

from . import udp_timeout, reorder_window, UDP_SEQUENCE_MAX, image_age_max

class UDPStream:
    def __init__(self, address):
        self._running = False
        self._thread = None
        self._data_queue = None
        self._address = address
        self._port = None
        self._sock = None
        self._debug_print = False

    def start(self, port, data_queue, debug_print: bool = False):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.settimeout(udp_timeout)  # half second timeout, to let the receiver be stopped gracefully

        self._thread = threading.Thread(target=self._run_loop, daemon=True)

        self._port = port
        self._debug_print = debug_print
        self._data_queue = data_queue
        self._running = True
        self._thread.start()

    def stop(self):
        if not self._running: return
        self._running = False
        if self._thread.is_alive():
            self._thread.join()
        self._sock.close()
        self._data_queue = None

    def _run_loop(self):  # Needs to be overloaded by subclass to be useful.
        pass

class UDPStreamReceiver (UDPStream):
    _HEADER_SIZE = 4

    def __init__(self, address):
        super().__init__(address)

        # we need to keep a very small priority queue to manage reordering out of order UDP packets
        self._expected_seq = None
        self._priority_queue = []
        self._reorder_window = None

    def start(self, port, data_queue, debug_print: bool = False):
        self._reorder_window = reorder_window
        super().start(port, data_queue, debug_print)
        self._sock.bind((self._address, port))

    def _run_loop(self):
        while self._running:
            data = None
            try:
                data, addr = self._sock.recvfrom(65536)

            except socket.timeout: # ignore, just block again. Wakes from timout
                pass

            except Exception as e:
                print(f"UDP receive error: {e}")

            if data is not None and len(data) > self._HEADER_SIZE:

                # packet_data: bytes object, first 4 bytes = seq_num
                seq_num = struct.unpack_from(">i", data, 0)[0]
                if self._expected_seq is None: self._expected_seq = seq_num  # initial seq_num init

                payload = memoryview(data)[self._HEADER_SIZE:]  # zero-copy
                self._queue_in_order( (seq_num, payload))

    def _queue_in_order(self, packet):
        (seq_num, payload) = packet

        if seq_num < self._expected_seq:  # less should never happen   #and self._is_newer(seq_num, self._expected_seq):

            ### just dump the heap into the queue and startover. the effect is just a shorter wait window once a wraparound
            while self._priority_queue:
                self._data_queue.put(heapq.heappop(self._priority_queue)[1])
            ## queue is now empty, we start with an empty queue using the regular algorithm.

        heapq.heappush(self._priority_queue, packet)

        if len(self._priority_queue) >= self._reorder_window:  # full, skip ahead
            self._expected_seq = self._priority_queue[0][0]  # first item is smallest. (seq,data)[0] is seq

        (seq_num, payload) = self._priority_queue[0]
        while self._priority_queue and seq_num == self._expected_seq:
            self._data_queue.put(payload, block=True)
            heapq.heappop(self._priority_queue)
            if self._priority_queue: (seq_num, payload) = self._priority_queue[0]
            self._expected_seq = (self._expected_seq + 1) % UDP_SEQUENCE_MAX

class UDPStreamChunkedReceiver (UDPStream):
    _packet_header_len = 8   # 8 bytes for 4 byte int+ 2byte + 2 byte

    class ImageBuffer:### Helper class to manage image buffers that arrive piecewise
        def __init__(self, part_count):
            self.piece_count = part_count
            self.pieces = {}

        def add(self, part_num, data):
            self.pieces[part_num] = data

        def is_complete(self):
            return len(self.pieces) == self.piece_count

        def compile(self):
            if not self.is_complete(): return None
            return b"".join(self.pieces[i] for i in range(self.piece_count))


    def __init__(self, address):
        super().__init__(address)

        # we need to keep a very small priority queue to manage reordering out of order UDP packets
        self._expected_seq = None
        self._image_age_max = image_age_max
        self._images = {}

    def start(self, port, data_queue, debug_print: bool = False):
        super().start(port, data_queue, debug_print)
        self._sock.bind((self._address, port))

    def _run_loop(self):
        packet = 0
        while self._running:
            data = None
            try:
                data, addr = self._sock.recvfrom(65536)

                if self._debug_print:
                    packet = (packet + 1) % 1000
                    if packet % 10 == 0: print(".",end="")
                    if packet == 0: print ()

            except socket.timeout: # ignore, just block again. Wakes from timout
                pass

            except Exception as e:
                print(f"UDP receive error: {e}")

            if data is not None and len(data) > self._packet_header_len:

                # packet_data: bytes object, first 4 bytes = seq_num
                seq_num, piece_num, piece_count = struct.unpack_from(">ihh", data, 0)
                if piece_count <= 0:
                    if self._debug_print: print ("corrupted piece count")
                    continue

                if not (0 <= piece_num < piece_count):  # ensure data is valid and sane
                    if self._debug_print: print("corrupted piece num and or count")
                    continue

                if self._expected_seq is None: self._expected_seq = seq_num  # initial seq_num init

                if self.seq_ahead(self._expected_seq, seq_num):  # drop stale packets that show up.
                    if self._debug_print: print("dropped unexpected packet for old frame")
                    continue

                payload = memoryview(data)[self._packet_header_len:]  # zero-copy. 8 byte header
                self._register_packet(seq_num, piece_num, piece_count, payload)

    def _register_packet(self, seq_num, piece_num, piece_count, payload ):

                # check if cur sequence is too far ahead, get rid of old
                threshold = (self._expected_seq + self._image_age_max) % UDP_SEQUENCE_MAX
                if self.seq_ahead(seq_num, threshold):
                    if self._debug_print: print("pruning old incomplete images older than "+str(threshold))
                    self._expected_seq = (seq_num - self._image_age_max) % UDP_SEQUENCE_MAX  # move expected ahead
                    images = { k: v    #re-pack images, dropping old ones
                               for k, v in self._images.items()
                               if self.seq_ahead_or_equal(k, self._expected_seq ) }
                    self._images = images

                img = self._images.get(seq_num) # create image if new
                if img is None:
                    self._images[seq_num] = self.ImageBuffer(piece_count)

                elif img.piece_count != piece_count:  # skip ahead of piece_count doesn't match - corrupted?
                    if self._debug_print: print("corrupted frame, skipping ahead")
                    return

                if seq_num not in self._images:
                    self._images[seq_num] = self.ImageBuffer(piece_count)

                self._images.get(seq_num).add(piece_num, payload)

                img = self._images.get(self._expected_seq)
                while img and img.is_complete():
                    if self._debug_print: print("complete frame received: "+str(self._expected_seq))
                    self._data_queue.put(self._images[self._expected_seq].compile(), block=True)
                    del self._images[self._expected_seq]
                    self._expected_seq = (self._expected_seq + 1) % UDP_SEQUENCE_MAX
                    img = self._images.get(self._expected_seq)

    @staticmethod
    def seq_ahead(ahead_of_a, a):
        return 0 < (ahead_of_a - a) % UDP_SEQUENCE_MAX < (UDP_SEQUENCE_MAX // 2)

    @staticmethod
    def seq_ahead_or_equal(ahead_of_a, a):
        return 0 <= (ahead_of_a - a) % UDP_SEQUENCE_MAX < (UDP_SEQUENCE_MAX // 2)

class UDPStreamSender(UDPStream):
    def __init__(self,address):
        super().__init__(address)
        self._packet_seq = 0

    def _run_loop(self):
        while self._running:
            try:
                data = self._data_queue.get(block=True, timeout=0.2)  # block until data is available, timeout to enable shutdown
                header = struct.pack(">i", self._packet_seq)  # 4-byte signed int, big-endian
                data = header + data
                # print(f"sending: {self._address}, {self._port}. Data {len(data)}")
                self._sock.sendto(data, (self._address, self._port))
                self._packet_seq = (self._packet_seq + 1) % UDP_SEQUENCE_MAX

            except Empty:
                continue   # just do nothing and try again, was timeout

            except Exception as e:   #??? if we should handle better, fix
                print(f"UDPStreamSender error: {e}")