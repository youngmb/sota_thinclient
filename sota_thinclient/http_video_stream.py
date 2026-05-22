import queue

from sota_thinclient.udp_stream import UDPStreamReceiver

class HTTPVideoStream:
    _FIELD_ENABLED = "enabled"
    _FIELD_IMAGE_FORMAT = "streamImageFormat"
    _FIELD_IMAGE_SIZE = "streamImageSize"
    _FIELD_PORT = "streamPort"
    _FIELD_IP = "streamIP"
    _FIELD_BUFFERSIZE = "bufferSize"
    _FIELD_BITRATE_CAP_kbps = "bitrate_cap_kbps"

    _FIELD_SUPPORTED_SIZES = "supportedSizes"
    _FIELD_SUPPORTED_FORMATS = "supportedFormats"

    def __init__(self, http_manager, end_point, udp_stream, error_print=True):
        self._http = http_manager
        self._end_point = end_point
        self._error_print = error_print
        self._state = {}  # will be the state. empty means we don't have it
        self._udp_stream = udp_stream

        self.data_queue = queue.Queue(maxsize=100)  # Buffer for incoming packets

    def get_state(self, use_cached=False) -> dict | None:  # cached gets local copy if we have one instead of getting new
        if use_cached and self._state:
            return self._state

        self._state = self._http.get_as_json(self._end_point)
        return self._state

    def _post_state(self, payload) -> bool:
        post_payload = self._http.post_dict_as_json(self._end_point, payload)
        if post_payload is None: return False

        self._state = post_payload  # save most recent state
        return True

    def enable(self, data_udp_port, restart_if_enabled=True,
               request_image_size : str = None,
               request_image_format : str = None,
               request_bitrate_kbps : int = None) -> bool:

        ## Ask Sota to turn on the video streaming, pointed at us.
        payload = self.get_state()
        if payload is None: return False

        if self._FIELD_ENABLED not in payload:
            if self._error_print: print(f"Field '{self._FIELD_ENABLED}' not found for enabling endpoint '{self._end_point}'.")
            return False

        if payload[self._FIELD_ENABLED]:  # already enabled

            if (not restart_if_enabled) and \
                (not request_image_size) and \
                (not request_image_format) and \
                    (not request_bitrate_kbps)    : return True

            # try to disable first
            if not self.disable():
                if self._error_print: print(f"Error disabling existing stream before enabling endpoint '{self._end_point}'.")
                return False

        self._udp_stream.start(data_udp_port, self.data_queue)  #start UDP stream

        # enabling needs to set the enabled flag, and provide a UDP port to send out to
        payload[self._FIELD_ENABLED] = True
        payload[self._FIELD_PORT] = data_udp_port
        if request_image_size: payload[self._FIELD_IMAGE_SIZE] = request_image_size
        if request_image_format: payload[self._FIELD_IMAGE_FORMAT] = request_image_format
        if request_bitrate_kbps: payload[self._FIELD_BITRATE_CAP_kbps] = request_bitrate_kbps
        payload.pop(self._FIELD_IP)  # no IP tells it to use our, the requestor's, IP
        return self._post_state(payload)

    def disable(self) -> bool:

        if self._udp_stream:
            self._udp_stream.stop()

        # Ask Sota to disable
        payload = self.get_state()
        if payload is None: return False

        if self._FIELD_ENABLED not in payload:
            if self._error_print: print(f"Field '{self._FIELD_ENABLED}' not found for disabling endpoint '{self._end_point}'.")

        if not payload[self._FIELD_ENABLED]:  # already disabled
            return True

        payload[self._FIELD_ENABLED] = False
        return self._post_state(payload)