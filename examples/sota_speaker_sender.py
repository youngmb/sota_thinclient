import time
import wave
from queue import Full

import numpy as np

from sota_thinclient import ConnectionManager
from sota_thinclient.http_audio_stream import StreamingMonoResampler

# SOTA_IP = "192.168.0.23"
SOTA_IP = "10.151.63.71"
HTTP_PORT = "8080"
UDP_PORT = 52002
WAV_FILE = "sample-24.wav"

# our central sota connection manager
sota = ConnectionManager(SOTA_IP, HTTP_PORT)
sota.speaker.enable(data_udp_port=UDP_PORT, restart_if_enabled=True) # tries to get the server to start listening for our speaker UDP stream
speaker_state = sota.speaker.get_state()

with wave.open(WAV_FILE, 'rb') as wf:
    print(f"Loaded file: {wf.getnchannels()} channels, {wf.getsampwidth() * 8}-bit, {wf.getframerate()} Hz, {wf.getnframes()} frames")
    wav_data = wf.readframes(wf.getnframes())

    resampler = StreamingMonoResampler(
        source_rate=wf.getframerate(),
        source_dtype= np.dtype(f'int{wf.getsampwidth() * 8}'),
        target_rate= speaker_state['sampleRate'],
        target_dtype= np.dtype(f'int'+str(speaker_state['sampleSize_bits']))
    )

    chunk_size = speaker_state['bufferSize']  # simulate a reasonable streaming slice for our resampling
    resampled_data = b""
    for i in range(0, len(wav_data), chunk_size):  # could do in one go but simulate streaming for testing
        resampled_data += resampler.resample_chunk(wav_data[i:i+chunk_size])

##crudely simulate streaming audio
buffer_size = int(speaker_state['bufferSize'])
frame_size = (speaker_state['channels'] * (speaker_state['sampleSize_bits']//8))
buffer_s = (buffer_size / frame_size) / speaker_state['sampleRate']
print(f"Buffer of {buffer_size} is {buffer_s:.3f} s")
print(sota.speaker.get_state())

initial_buffer = 10  # send packets without delay to get the buffer warmed up
next_time = time.perf_counter()
for i in range(0, len(resampled_data), buffer_size):
    chunk = resampled_data[i:i+buffer_size]

    remainder = len(chunk) % buffer_size
    if remainder != 0:
        chunk = chunk + bytes(buffer_size - remainder)

    try:
        sota.speaker.data_queue.put(chunk, block=False)
    except Full:
        pass
    # print(len(chunk))

    next_time += buffer_s
    remaining = next_time - time.perf_counter()
    if initial_buffer > 0:
        initial_buffer -= 1
    elif remaining > 0:
        time.sleep(remaining*.9)

sota.speaker.disable()