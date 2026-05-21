class PoseManager:
    _FIELD_SYSTEM_SERVOS_ENABLED = "servosEnabled"
    _FIELD_SYSTEM_TALKING_LED_ENABLED = "talkingLEDEnabled"
    _FIELD_SYSTEM_LIST_SERVO_CAPABILITIES = "servoCapabilities"
    
    _FIELD_POSE_SERVO_STATUS = "servoStatus"
    _FIELD_POSE_LED_STATUS = "LEDStatus"
    _FIELD_POSE_MOVE_MSEC = "move_msec"
    _FIELD_POSE_COMMAND = "command"

    _ENDPOINT_SYSTEM = "/system"
    _ENDPOINT_JOINTSPACE = "/jointspace"
    _ENDPOINT_WORLDSPACE = "/worldspace_skeleton"

    def __init__(self, http_manager, end_point_path, error_print=True):
        self._http = http_manager
        self._end_point_path = end_point_path
        self._error_print = error_print
        self._state = {}  # will be the state. empty means we don't have it
        
    def _get_state(self, endpoint, use_cached=False) -> dict | None:  # cached gets local copy if we have one instead of getting new
        if use_cached and self._state:
            return self._state

        self._state = self._http.get_as_json(self._end_point_path + endpoint)
        return self._state

    def _post_state(self, payload, endpoint) -> bool:
        post_payload = self._http.post_dict_as_json(self._end_point_path + endpoint, payload)
        if post_payload is None: return False

        self._state = post_payload  # save most recent state
        return True
    
    def get_system_status(self) -> dict | None:
        return self._get_state(self._ENDPOINT_SYSTEM)

    def get_servo_capabilities(self) -> dict | None:
        state = self._get_state(self._ENDPOINT_SYSTEM)
        if state is None: return None

        if self._FIELD_SYSTEM_LIST_SERVO_CAPABILITIES not in state:
            if self._error_print: print(f"Field '{self._FIELD_SYSTEM_LIST_SERVO_CAPABILITIES}' not found for endpoint '{self._end_point_path}'.")
            return None

        return state[self._FIELD_SYSTEM_LIST_SERVO_CAPABILITIES]

    def set_servos_enabled(self, enable: bool) -> bool:
        payload = self._get_state(self._ENDPOINT_SYSTEM)
        if payload is None: return False

        if self._FIELD_SYSTEM_SERVOS_ENABLED not in payload:
            if self._error_print: print(f"Field '{self._FIELD_SYSTEM_SERVOS_ENABLED}' not found for enabling endpoint '{self._end_point_path}'.")
            return False

        if payload[self._FIELD_SYSTEM_SERVOS_ENABLED] == enable:  # already enabled or disabled
            return True

        payload[self._FIELD_SYSTEM_SERVOS_ENABLED] = enable
        return self._post_state(payload, self._ENDPOINT_SYSTEM)
    
    def set_talking_led_enabled(self, enable: bool) -> bool:
        payload = self._get_state(self._ENDPOINT_SYSTEM)
        if payload is None: return False

        if self._FIELD_SYSTEM_TALKING_LED_ENABLED not in payload:
            if self._error_print: print(f"Field '{self._FIELD_SYSTEM_TALKING_LED_ENABLED}' not found for enabling endpoint '{self._end_point_path}'.")
            return False

        if payload[self._FIELD_SYSTEM_TALKING_LED_ENABLED] == enable:  # already enabled or disabled
            return True

        payload[self._FIELD_SYSTEM_TALKING_LED_ENABLED] = enable
        return self._post_state(payload, self._ENDPOINT_SYSTEM)
    
    def get_pose_jointspace(self) -> dict | None:
        return self._get_state(self._ENDPOINT_JOINTSPACE)
    
    def send_pose_jointspace(self, servo_positions: dict, led_positions: dict, move_msec: int, command: str = "APPEND"):
        """
        servo_positions: a dict of servo positions in radians, e.g., [{"servo_id": "R_SHOULDER", "radians": 0.5}, ...]
        led_positions: a dict of LED colors with hex values, e.g., [{"led_id": "EYE_LEFT", "color": "#FF0000"}, ...]
        move_msec: time in milliseconds for the movement to take
        command: defines queue insertion behavior, defaults to APPEND. See thinserver PoseCommand enum for options.
        """
        payload = {}
        payload[self._FIELD_POSE_COMMAND] = command
        payload[self._FIELD_POSE_MOVE_MSEC] = move_msec
        payload[self._FIELD_POSE_SERVO_STATUS] = servo_positions
        payload[self._FIELD_POSE_LED_STATUS] = led_positions
        return self._post_state(payload, self._ENDPOINT_JOINTSPACE)
    
    def get_pose_worldspace_skeleton(self) -> dict | None:
        return self._get_state(self._ENDPOINT_WORLDSPACE)
    
    def send_pose_worldspace_skeleton(self, skeleton_positions: dict, led_positions: dict, move_msec: int, command: str = "APPEND"):
        print('send_pose_worldspace_skeleton not implemented yet')
        pass