import time
import wave
import numpy as np

from scipy.signal import resample #for audio resampling -- install for example only

from sota_thinclient import SOTA_SPK_SAMPLERATE, SOTA_SPK_CHANNELS, SOTA_SPK_DATATYPE
from sota_thinclient import ConnectionManager

SOTA_IP = "192.168.0.23"
HTTP_PORT = "8080"
UDP_PORT = 52002
WAV_FILE = "sample.wav"

def get_audio_data(wav_file):   # Loads wav and converts to sota-friendly format
    with wave.open(wav_file, 'rb') as wf:
        print(
            f"Loaded file: {wf.getnchannels()} channels, {wf.getsampwidth() * 8}-bit, {wf.getframerate()} Hz, {wf.getnframes()} frames")

        # Convert bytes to numpy array
        dtype_map = {1: np.int8, 2: np.int16, 4: np.int32}  # BYTES to np type. Need updating for floating types
        audio = np.frombuffer(wf.readframes(wf.getnframes()),  # wf gives bytes, so we read as the intended type
                              dtype=dtype_map[wf.getsampwidth()])

        # If stereo+, reshape (frames, channels)
        if wf.getnchannels() > 1:
            audio = audio.reshape(-1, wf.getnchannels())  # makes len x channels matrix
            audio = audio[:, :SOTA_SPK_CHANNELS]  # discard unused channels.

        # resample to Sota's samplerate and datatype
        out_type = np.dtype(SOTA_SPK_DATATYPE)
        num_target_frames = int(len(audio) * SOTA_SPK_SAMPLERATE / wf.getframerate())
        resampled_audio = resample(audio, num_target_frames, axis=0)  # results in floating point,
        resampled_audio = np.clip(resampled_audio, np.iinfo(out_type).min, np.iinfo(out_type).max)
        resampled_audio = resampled_audio.astype(out_type)

    return resampled_audio.tobytes()


def simulate_streaming_audio(data_bytes, data_queue):
    chunk_size = (SOTA_SPK_SAMPLERATE * SOTA_SPK_CHANNELS * np.dtype(SOTA_SPK_DATATYPE).itemsize) // 100  # 10ms chunks

    for i in range(0, len(data_bytes), chunk_size):
        data_queue.put(data_bytes[i:i+chunk_size], block=False)
        time.sleep(.005)  # 5 ms sleep

# our central sota connection manager
sota = ConnectionManager(SOTA_IP, HTTP_PORT)
sota.speaker.enable(data_udp_port=UDP_PORT, restart_if_enabled=True) # tries to get the server to start listening for our speaker UDP stream

data = get_audio_data(WAV_FILE)
simulate_streaming_audio(data, sota.speaker.data_queue)

print(sota.speaker.get_state())

# print(sd.query_hostapis())  # look for 'ASIO'

input()  # pause until keypress

sota.speaker.disable()