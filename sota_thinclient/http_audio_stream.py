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

    # def enable(self, data_udp_port, restart_if_enabled=True,
    #            request_buffer_size : int =None) -> bool:
    #
    #     ## Ask Sota to turn on the mic streaming, pointed at us.
    #     payload = self.get_state()
    #     if payload is None: return False
    #
    #     need_buffersize_change = ( (request_buffer_size is not None) and
    #                                (int(payload[_FIELD_BUFFERSIZE] or 0) != request_buffer_size))
    #
    #     if _FIELD_ENABLED not in payload:
    #         if self._error_print: print(f"Field '{_FIELD_ENABLED}' not found for enabling endpoint '{self._end_point_path}'.")
    #         return False
    #
    #     if payload[_FIELD_ENABLED]:  # already enabled
    #
    #         if (not restart_if_enabled) and (not need_buffersize_change): return True
    #
    #         # try to disable first
    #         if not self.disable():
    #             if self._error_print: print(f"Error disabling existing stream before enabling endpoint '{self._end_point_path}'.")
    #             return False
    #
    #     self._udp_stream.start(data_udp_port, self.data_queue)  #start UDP stream
    #
    #     # enabling needs to set the enabled flag, and provide a UDP port to send out to
    #     payload[_FIELD_ENABLED] = True
    #     payload[_FIELD_PORT] = data_udp_port
    #     if need_buffersize_change: payload[_FIELD_BUFFERSIZE] = request_buffer_size
    #     payload.pop(_FIELD_IP)  # no IP tells it to use our, the requestor's, IP
    #     return self._post_state(payload)

    def enable(self, data_udp_port, restart_if_enabled=True,
               request_buffer_size : int =None) -> bool:

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