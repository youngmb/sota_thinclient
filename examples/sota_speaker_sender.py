import time
import wave
import numpy as np

from scipy.signal import resample #for audio resampling -- install for example only

from sota_thinclient import ConnectionManager

# SOTA_IP = "192.168.0.23"
SOTA_IP = "10.151.63.71"
HTTP_PORT = "8080"
UDP_PORT = 52002
WAV_FILE = "sample.wav"

def get_resampled_audio_data(wav_file, target_channels, target_samplerate, target_sample_size_bits):   # Loads wav and converts to sota-friendly format
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
            audio = audio[:, :target_channels]  # discard unused channels.

        # resample to Sota's samplerate and datatype
        out_type = np.dtype(np.dtype(f'i{target_sample_size_bits // 8}'))
        num_target_frames = int(len(audio) * target_samplerate / wf.getframerate())
        resampled_audio = resample(audio, num_target_frames, axis=0)  # results in floating point,
        resampled_audio = np.clip(resampled_audio, np.iinfo(out_type).min, np.iinfo(out_type).max)
        resampled_audio = resampled_audio.astype(out_type)

    return resampled_audio.tobytes()

# our central sota connection manager
sota = ConnectionManager(SOTA_IP, HTTP_PORT)
sota.speaker.enable(data_udp_port=UDP_PORT, restart_if_enabled=True) # tries to get the server to start listening for our speaker UDP stream
speaker_state = sota.speaker.get_state()

data = get_resampled_audio_data(WAV_FILE,
                      speaker_state['channels'],
                      speaker_state['sampleRate'],
                      speaker_state['sampleSize_bits'])

##crudely simulate streaming audio
buffer_size = speaker_state['bufferSize']
frame_size = (speaker_state['channels'] * (speaker_state['sampleSize_bits']//8))
buffer_s = (buffer_size / frame_size) / speaker_state['sampleRate']
print(f"Buffer of {speaker_state['bufferSize']} is {buffer_s:.3f} s")

initial_buffer =0  # send packets without delay to get the buffer warmed up
next_time = time.perf_counter()
for i in range(0, len(data), buffer_size):
    chunk = data[i:i+buffer_size]
    sota.speaker.data_queue.put(chunk, block=False)

    next_time += buffer_s
    remaining = next_time - time.perf_counter()
    if initial_buffer > 0:
        initial_buffer -= 1
    elif remaining > 0:
        time.sleep(remaining)

print(sota.speaker.get_state())

input()  # pause until keypress

sota.speaker.disable()