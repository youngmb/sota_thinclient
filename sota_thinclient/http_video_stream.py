import queue

from sota_thinclient.http import HTTPConnector

_FIELD_ENABLED = "enabled"
_FIELD_IMAGE_FORMAT = "streamImageFormat"
_FIELD_IMAGE_SIZE = "streamImageSize"
_FIELD_PORT = "streamPort"
_FIELD_IP = "streamIP"
_FIELD_BUFFERSIZE = "bufferSize"
_FIELD_BITRATE_CAP_kbps = "bitrate_cap_kbps"

_FIELD_SUPPORTED_SIZES = "supportedSizes"
_FIELD_SUPPORTED_FORMATS = "supportedFormats"

_CAPABILITIES_SUBPATH = "/capabilities"

class HTTPVideoStream(HTTPConnector):
    def __init__(self, http_manager, end_point, udp_stream, error_print=True, debug_print=False):
        super().__init__(http_manager, end_point, error_print)
        self._debug_print = debug_print
        self._udp_stream = udp_stream
        self.data_queue = queue.Queue(maxsize=100)  # Buffer for incoming packets

    def get_state(self, use_cached=False) -> dict | None:  # cached gets local copy if we have one instead of getting new
        return self._get_state(use_cached = use_cached)

    def get_capabilities(self):
        return self._http.get_as_json(self._end_point_path+_CAPABILITIES_SUBPATH)

    def enable(self, data_udp_port, restart_if_enabled=True,
               request_image_size: str = None,
               request_image_format: str = None,
               request_bitrate_kbps: int = None,
               debug_print: bool = None) -> bool:

        if debug_print: self._debug_print = debug_print

        restart_if_enabled = restart_if_enabled or request_image_size or request_image_format or request_bitrate_kbps

        payload = {_FIELD_PORT: data_udp_port, _FIELD_IP: None}
        if request_image_size: payload[_FIELD_IMAGE_SIZE] = request_image_size
        if request_image_format: payload[_FIELD_IMAGE_FORMAT] = request_image_format
        if request_bitrate_kbps: payload[_FIELD_BITRATE_CAP_kbps] = request_bitrate_kbps
        payload.pop(_FIELD_IP)  # no IP tells it to use our, the requestor's, IP

        if self._set_capability_enabled(_FIELD_ENABLED, True, restart_if_enabled=restart_if_enabled, additional_fields=payload):
            self._udp_stream.start(data_udp_port, self.data_queue, debug_print=self._debug_print)  # start UDP stream
            return True
        return False

    def disable(self) -> bool:

        if self._udp_stream:
            self._udp_stream.stop()

        # Ask Sota to disable
        payload = self.get_state()
        if payload is None: return False

        if _FIELD_ENABLED not in payload:
            if self._error_print: print(f"Field '{_FIELD_ENABLED}' not found for disabling endpoint '{self._end_point_path}'.")

        if not payload[_FIELD_ENABLED]:  # already disabled
            return True

        payload[_FIELD_ENABLED] = False
        return self._post_state(payload)