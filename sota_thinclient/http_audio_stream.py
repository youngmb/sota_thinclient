import queue
from operator import truediv

from sota_thinclient.http import HTTPConnector
from sota_thinclient.udp_stream import UDPStreamReceiver

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