import queue
import socket
import struct
import threading
import time
import requests
import os
import numpy as np
from sota_thinclient.stream import UDPStreamReceiver
from sota_thinclient import SOTA_MIC_SAMPLERATE, SOTA_MIC_CHANNELS, SOTA_MIC_DATATYPE

MIC_IP = "192.168.0.23"
UDP_PORT = 51001
os.environ["SD_ENABLE_ASIO"] = "1"

import sounddevice as sd

SAMPLE_RATE = 16000   #### Must match the Sota stream. these are defaults.
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit PCM

# ----------------------------
# 1. HTTP "arm mic" request
# ----------------------------
def enable_mic(ip, port):
    url = f"http://{ip}:8080/mic"

    payload = {
        "enabled": True,
        "streamSendPort": port
    }

    try:
        r = requests.post(url, json=payload, timeout=3)
        print("HTTP response:", r.status_code, r.text)
    except Exception as e:
        print("HTTP error:", e)


# ----------------------------
# 2. UDP Receiver (audio in)
# ----------------------------
class UDPAudioReceiver(threading.Thread):
    def __init__(self, ip, port):
        super().__init__(daemon=True)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((ip, port))
        self.sock.setblocking(False)  # Non-blocking socket
        self.audio_queue = queue.Queue(maxsize=100)  # Buffer for incoming packets
        self.expected_seq = 0

    def run(self):
        print(f"UDP Receiver listening on {UDP_PORT}")

        device_id = 19  # default WDM-KS output device
        device_info = sd.query_devices(device_id)

        samplerate = device_info['default_samplerate']
        channels = device_info['max_output_channels']
        print(device_info)

        # Create a low-latency output stream with callback
        with sd.OutputStream(
            samplerate=48000,  #SAMPLE_RATE,
            channels=2,
            dtype='int16',
            latency='low',
            blocksize=256,
            callback=self.audio_callback,
            device=device_id,
            # extra_settings=sd.AsioSettings(channel_selectors=[0, 1])
            # extra_settings=sd.WasapiSettings(exclusive=True)
        ) as stream:
            while True:
                try:
                    packet, addr = self.sock.recvfrom(65535)
                    seq = struct.unpack(">i", packet[:4])[0]
                    audio = packet[4:]

                    if seq != self.expected_seq:
                        print(f"[WARN] out-of-order: {seq} expected {self.expected_seq}")
                        self.expected_seq = seq + 1
                    else:
                        self.expected_seq += 1

                    # Put audio into queue; drop if full
                    if not self.audio_queue.full():
                        self.audio_queue.put(audio)
                    else:
                        print("[WARN] audio queue full, dropping packet")
                except BlockingIOError:
                    pass  # No packet available, continue

    def audio_callback(self, outdata, frames, time, status):
        if status:
            print("Stream status:", status)

        try:
            # Pull the next packet from queue
            packet = self.audio_queue.get_nowait()
            audio_array = np.frombuffer(packet, dtype=np.int16).reshape(-1, CHANNELS)

            # Fill outdata (may need to truncate if frames < packet length)
            out_len = min(len(audio_array), len(outdata))
            outdata[:out_len] = audio_array[:out_len]

            # If outdata is larger than packet, fill remaining with silence
            if out_len < len(outdata):
                outdata[out_len:] = 0

        except queue.Empty:
            # No data in queue → output silence
            outdata.fill(0)


# ----------------------------
# 2. UDP Receiver (audio in)
# ----------------------------



# # ----------------------------
# # 3. UDP Sender (dummy audio)
# # ----------------------------
# class UDPAudioSender(threading.Thread):
#     def __init__(self, target_ip, port):
#         super().__init__(daemon=True)
#
#         self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#         self.target = (target_ip, port)
#
#         self.sock.setblocking(False)
#
#
#         self.sequence = 0
#
#     def audio_callback(outdata, frames, time, status):
#         try:
#             packet = audio_queue.get_nowait()
#             audio_array = np.frombuffer(packet, dtype=np.int16).reshape(-1, 1)
#             outdata[:len(audio_array)] = audio_array
#             if len(audio_array) < len(outdata):
#                 outdata[len(audio_array):] = 0
#         except queue.Empty:
#             outdata.fill(0)
#
#     def run(self):
#         print("UDP Sender started")
#
#         while True:
#             # fake PCM audio (silence)
#             audio_chunk = b'\x00' * 512
#
#             packet = struct.pack(">i", self.sequence) + audio_chunk
#             self.sock.sendto(packet, self.target)
#
#             self.sequence += 1
#             time.sleep(0.02)  # 50 packets/sec (~20ms audio frames)
sota_mic_queue = queue.Queue(maxsize=100)  # Buffer for incoming packets

leftover = np.empty((0, SOTA_MIC_CHANNELS), dtype=np.dtype(SOTA_MIC_DATATYPE))  # persistent across callbacks  # persistent across callbacks
def audio_callback(outdata, frames, time, status):
    global leftover

    if status:
        print("Stream status:", status)

    try:
        audio_array = leftover

        if len(audio_array) == 0:  # nothing left over, get a new one.
            packet = sota_mic_queue.get_nowait()
            audio_array = np.frombuffer(packet, dtype=np.int16).reshape(-1, CHANNELS)

        # Fill outdata (may need to truncate if frames < packet length)
        out_len = min(len(audio_array), len(outdata))
        outdata[:out_len] = audio_array[:out_len]
        leftover = audio_array[out_len:].copy()

        # If outdata is larger than packet, fill remaining with silence
        if out_len < len(outdata):
            outdata[out_len:] = 0

    except queue.Empty:
        # No data in queue → output silence
        outdata.fill(0)



# ----------------------------
# Main
# ----------------------------
if __name__ == "__main__":


    stream = sd.OutputStream(
        samplerate=SOTA_MIC_SAMPLERATE,  # SAMPLE_RATE,
        channels=SOTA_MIC_CHANNELS,
        dtype=SOTA_MIC_DATATYPE,
        latency='low',
        blocksize=256,   # this is number of frames. you can calculate how many ms latency are introduced here
        callback=audio_callback
    )
    stream.start()

    # 1. enable mic over HTTP
    enable_mic(MIC_IP, UDP_PORT)

    # 2. start UDP receiver
    # receiver = UDPAudioReceiver("0.0.0.0", UDP_PORT)
    receiver = UDPStreamReceiver("0.0.0.0", UDP_PORT, sota_mic_queue)

    receiver.start()

    # 3. start UDP sender (loopback test)
    # sender = UDPAudioSender("127.0.0.1", UDP_PORT)
    # sender.start()
    print(sd.query_hostapis())  # look for 'ASIO'

    input()
    receiver.stop()
    stream.stop()
    stream.close()
    # sender.join()

