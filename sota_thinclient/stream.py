# sota_thinclient/stream.py
import socket
import struct
import threading
import heapq
from . import udp_timeout, reorder_window, UDP_SEQUENCE_MAX

class UDPStreamReceiver:
    def __init__(self, bindIP: str, port: int, output_queue):
        self._reorder_window = reorder_window
        self.bindIP = bindIP
        self.port = port
        self.queue = output_queue
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.settimeout(udp_timeout)  #half second timeout, to let the receiver be stopped gracefully
        self._sock.bind((bindIP, port))
        self._running = False
        self._thread = threading.Thread(target=self._run_loop, daemon=True)

        # we need to keep a very small priority queue to manage reordering out of order UDP packets
        self._expected_seq = None
        self._priority_queue = []

    def start(self):
        self._running = True
        self._thread.start()

    def stop(self):
        # self._running = False
        # self._thread.join()
        # self._sock.close()
        pass

    def _run_loop(self):
        while self._running:
            data = None
            try:
                data, addr = self._sock.recvfrom(65536)

            except socket.timeout: # ignore, just block again. Wakes from timout
                pass

            except Exception as e:
                print(f"UDP receive error: {e}")

            if data is not None:

                # packet_data: bytes object, first 4 bytes = seq_num
                seq_num = struct.unpack_from(">i", data, 0)[0]
                if self._expected_seq is None: self._expected_seq = seq_num  # initial seq_num init

                payload = memoryview(data)[4:]  # zero-copy
                self._queue_in_order( (seq_num, payload))


    def _queue_in_order(self, packet):
        (seq_num, payload) = packet

        if seq_num < self._expected_seq:  # less should never happen   #and self._is_newer(seq_num, self._expected_seq):

            ### just dump the heap into the queue and startover. the effect is just a shorter wait window once a wraparound
            while self._priority_queue:
                self.queue.put( heapq.heappop(self._priority_queue)[1] )
            ## queue is now empty, we start with an empty queue using the regular algorithm.

        heapq.heappush(self._priority_queue, packet)

        if len(self._priority_queue) >= self._reorder_window:  # full, skip ahead
            self._expected_seq = self._priority_queue[0][0]  # first item is smallest. (seq,data)[0] is seq

        (seq_num, payload) = self._priority_queue[0]
        while self._priority_queue and seq_num == self._expected_seq:
            self.queue.put(payload, block=True)
            heapq.heappop(self._priority_queue)
            if self._priority_queue: (seq_num, payload) = self._priority_queue[0]
            self._expected_seq = (self._expected_seq + 1) % UDP_SEQUENCE_MAX