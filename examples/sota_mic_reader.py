import queue
import time
import sounddevice as sd
# import os
import numpy as np

from sota_thinclient import SOTA_MIC_SAMPLERATE, SOTA_MIC_CHANNELS, SOTA_MIC_DATATYPE
from sota_thinclient import ConnectionManager

SOTA_IP = "192.168.0.23"
HTTP_PORT = "8080"
UDP_PORT = 52001
# os.environ["SD_ENABLE_ASIO"] = "1"

###### A simple buffer reader that dumps to the default output audio device.
## This is the callback, the stream is initialized and started below
class audioListener:

    def __init__(self, queue):
        self._leftover = np.empty((0, SOTA_MIC_CHANNELS), dtype=np.dtype(SOTA_MIC_DATATYPE))  # persistent across callbacks
        self._queue = queue

    def start(self):
        self._stream = sd.OutputStream(
            samplerate=SOTA_MIC_SAMPLERATE,  # SAMPLE_RATE,
            channels=SOTA_MIC_CHANNELS,
            dtype=SOTA_MIC_DATATYPE,
            latency='low',
            blocksize=256,  # this is number of frames. you can calculate how many ms latency are introduced here
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
                audio_array = np.frombuffer(packet, dtype=np.dtype(SOTA_MIC_DATATYPE)).reshape(-1, SOTA_MIC_CHANNELS)

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

audio = audioListener(sota.microphone.data_queue)
audio.start()

time.sleep(3)
print(sota.microphone.get_state())

# print(sd.query_hostapis())  # look for 'ASIO'

input()  # pause until keypress

sota.microphone.disable()
audio.stop()

