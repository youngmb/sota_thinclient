import queue
import time
# import os
# os.environ["SD_ENABLE_ASIO"] = "1"

import sounddevice as sd
import numpy as np
from sota_thinclient import ConnectionManager

# SOTA_IP = "192.168.0.23"
SOTA_IP = "10.151.63.71"
HTTP_PORT = "8080"
UDP_PORT = 52001


###### A simple buffer reader that dumps to the default output audio device.
## This is the callback, the stream is initialized and started below
class audioListener():

    def __init__(self, queue, mic_channels, sample_rate, sample_size_bits, buffersize_bytes):
        self._queue = queue
        self._mic_channels = mic_channels
        self._sample_rate = sample_rate

        self._datatype = np.dtype(np.dtype(f'i{sample_size_bits // 8}'))
        self._leftover = np.empty((0, mic_channels), dtype=self._datatype)  # persistent across callbacks
        self._buffersize = buffersize_bytes

    def start(self):
        self._stream = sd.OutputStream(
            samplerate=self._sample_rate,  # SAMPLE_RATE,
            channels=self._mic_channels,
            dtype=self._datatype.name,
            latency='low',
            blocksize=  (self._buffersize // self._mic_channels // self._datatype.itemsize),  # number of frames
            callback=self.audio_callback
        )
        self._stream.start()

    def stop(self):
        self._stream.stop()
        self._stream.close()

    def audio_callback(self, outdata, frames, time, status):
        if status:
            print("Stream status:", status)

        try:
            audio_array = self._leftover

            if len(audio_array) == 0:  # nothing left over, get a new one.
                packet = self._queue.get_nowait()
                audio_array = np.frombuffer(packet, dtype=self._datatype).reshape(-1, self._mic_channels)

            # Fill outdata (may need to truncate if frames < packet length)
            out_len = min(len(audio_array), len(outdata))
            outdata[:out_len] = audio_array[:out_len]
            self._leftover = audio_array[out_len:].copy()

            # If outdata is larger than packet, fill remaining with silence
            if out_len < len(outdata):
                outdata[out_len:] = 0

        except queue.Empty:
            # No data in queue → output silence
            outdata.fill(0)

# our central sota connection manager
sota = ConnectionManager(SOTA_IP, HTTP_PORT)
sota.microphone.enable(data_udp_port=UDP_PORT, restart_if_enabled=True)  # tries to get the server to start the mic UDP stream
# sota.microphone.enable(data_udp_port=UDP_PORT, request_buffer_size=640, restart_if_enabled=True)  # tries to get the server to start the mic UDP stream
# sota.microphone.enable(data_udp_port=UDP_PORT, request_buffer_size=16, restart_if_enabled=True)  # tries to get the server to start the mic UDP stream
mic_state = sota.microphone.get_state(use_cached=True)

audio = audioListener(sota.microphone.data_queue,
                      mic_state['channels'],
                      mic_state['sampleRate'],
                      mic_state['sampleSize_bits'],
                      mic_state['bufferSize'])
audio.start()

time.sleep(3)
print(sota.microphone.get_state())

# print(sd.query_hostapis())  # look for 'ASIO'

input()  # pause until keypress

sota.microphone.disable()
audio.stop()

