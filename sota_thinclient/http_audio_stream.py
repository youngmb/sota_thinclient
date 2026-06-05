import queue
import numpy as np
from scipy import signal

from sota_thinclient.http import HTTPConnector

_FIELD_ENABLED = "enabled"
_FIELD_VOLUME = "volume"
_FIELD_PORT = "streamPort"
_FIELD_IP = "streamIP"
_FIELD_BUFFERSIZE = "bufferSize"

class HTTPAudioStream(HTTPConnector):

    def __init__(self, http_manager, end_point, udp_stream, error_print=True):
        super().__init__(http_manager, end_point, error_print)
        self._udp_stream = udp_stream
        self.data_queue = queue.Queue(maxsize=100)  # Buffer for incoming packets

    def get_state(self, use_cached=False) -> dict | None:  # cached gets local copy if we have one instead of getting new
        return self._get_state()

    def enable(self, data_udp_port, restart_if_enabled=True,
               request_buffer_size : int = None) -> bool:

        restart_if_enabled = restart_if_enabled or request_buffer_size

        payload = {_FIELD_PORT: data_udp_port, _FIELD_IP : None}
        if request_buffer_size: payload[_FIELD_BUFFERSIZE] = request_buffer_size
        if self._set_capability_enabled(_FIELD_ENABLED, True, restart_if_enabled=restart_if_enabled, additional_fields=payload):
            self._udp_stream.start(data_udp_port, self.data_queue)  # start UDP stream
            return True

        return False

    def disable(self) -> bool:

        if self._udp_stream:
            self._udp_stream.stop()

        # Ask Sota to disable
        payload = self.get_state()
        if payload is None: return False

        if _FIELD_ENABLED not in payload:
            if self._error_print: print(f"Field '{self._FIELD_ENABLED}' not found for disabling endpoint '{self._end_point}'.")

        if not payload[_FIELD_ENABLED]:  # already disabled
            return True

        payload[_FIELD_ENABLED] = False
        return self._post_state(payload)

class StreamingMonoResampler:
    def __init__(self,
                 source_rate: int,
                 target_rate: int,
                 source_dtype : np.dtype = np.dtype('int16'),
                 target_dtype: np.dtype = np.dtype('int16'),
                 ):
        self._source_sr = source_rate
        self._target_sr = target_rate
        self._source_dtype = source_dtype
        self._target_dtype = target_dtype

        self._sample_debt = 0.0  # fractional samples owed to next chunk
        self._last_sample = None   # continuity across samples

    def resample_chunk(self, raw_audio_bytes: bytes) -> bytes:

        if self._source_sr == self._target_sr:
            return raw_audio_bytes

        new_chunk = np.frombuffer(raw_audio_bytes, dtype=self._source_dtype)

        if self._last_sample is not None:
            new_chunk = np.concatenate(([self._last_sample], new_chunk))
        self._last_sample = new_chunk[-1]  # save last sample for nex ttime. note np works in frames

        exact_output = len(new_chunk) * self._target_sr / self._source_sr + self._sample_debt
        n_output = int(exact_output)
        self._sample_debt = exact_output - n_output  # carry over fraction to next chunk

        x_old = np.linspace(0, 1, len(new_chunk))
        x_new = np.linspace(0, 1, n_output)
        resampled = np.interp(x_new, x_old, new_chunk.astype(np.float32))[1:]  # trim the prepended interpolated entry

        return np.clip(resampled, np.iinfo(self._target_dtype).min,
                       np.iinfo(self._target_dtype).max).astype(self._target_dtype).tobytes()