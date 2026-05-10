import queue

from sota_thinclient.stream import UDPStreamReceiver

class Microphone:
    _FIELD_ENABLED = "enabled"
    _FIELD_VOLUME = "volume"
    _FIELD_PORT = "streamSendPort"
    _FIELD_IP = "streamIP"

    #HTTP response: 200 {"enabled":true,"volume":-1,"streamSendPort":51001,"streamIP":"192.168.0.203","error":null}

    def __init__(self, http_manager, mic_path="/mic", error_print=True):
        self._http = http_manager
        self._mic_path = mic_path
        self._error_print = error_print
        self._state = {}  # will be the microphone state
        self._udpReceiver = None

        self.mic_queue = queue.Queue(maxsize=100)  # Buffer for incoming packets

    def get_state(self, use_cached=False) -> dict | None:   #cached gets local copy if we have one instead of getting new
        if use_cached and self._state:
            return self._state

        self._state = self._http.get_as_json(self._mic_path)
        return self._state

    def _post_state(self, payload) -> bool:
        post_payload = self._http.post_dict_as_json(self._mic_path, payload)
        if post_payload is None: return False

        self._state = post_payload # save most recent state
        return True

    def enable(self, data_udp_port, restart_if_enabled=True) -> bool:

        ## Ready the UDP listener
        self._udpReceiver = UDPStreamReceiver("0.0.0.0", data_udp_port, self.mic_queue)
        self._udpReceiver.start()

        ## Ask Sota to turn on the mic streaming, pointed at us.
        payload = self.get_state()
        if payload is None: return False

        if self._FIELD_ENABLED not in payload:
            if self._error_print: print (f"Field '{self._FIELD_ENABLED}' not found for enabling mic")
            return False

        if payload[self._FIELD_ENABLED]:  # already enabled
            if not restart_if_enabled: return True

            # try to disable first
            if not self.disable():
                if self._error_print: print("Error disabling previous mic stream before enabling")
                return False

        # enabling needs to set the enabled flag, and provide a UDP port to send out to
        payload[self._FIELD_ENABLED] = True
        payload[self._FIELD_PORT] = data_udp_port
        payload.pop(self._FIELD_IP)   # no IP tells it to use our, the requestor's, IP
        return self._post_state(payload)

    def disable(self) -> bool:
        #disable the UDP listener
        if self._udpReceiver:
            self._udpReceiver.stop()
            self._udpReceiver = None

        #Ask Sota to stop sending
        payload = self.get_state()
        if payload is None: return False

        if self._FIELD_ENABLED not in payload:
            if self._error_print: print(f"Field '{self._FIELD_ENABLED}' not found for disabling mic")

        if not payload[self._FIELD_ENABLED]: # already disabled
            return True

        payload[self._FIELD_ENABLED] = False
        return self._post_state(payload)