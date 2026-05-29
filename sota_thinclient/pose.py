from dataclasses import dataclass, field
from enum import Enum, StrEnum

from sota_thinclient.http import HTTPConnector

## Field constants for the JSON
_FIELD_SYSTEM_SERVOS_ENABLED = "servosEnabled"
_FIELD_SYSTEM_TALKING_LED_ENABLED = "talkingLEDEnabled"
_FIELD_SYSTEM_LIST_SERVO_CAPABILITIES = "servoCapabilities"
_FIELD_SYSTEM_RANGE_MIN = "range_min"
_FIELD_SYSTEM_RANGE_MAX = "range_max"

_FIELD_POSE_MOVE_MSEC = "move_msec"
_FIELD_POSE_COMMAND = "command"

## joint space
_FIELD_POSE_SERVO_ID = "servo_id"
_FIELD_POSE_RADIANS = "radians"
_FIELD_POSE_SERVO_STATUS = "servoStatus"

## world space
_FIELD_POSE_ENDPOINT_STATUS = "endpointStatus"
_FIELD_POSE_ENDPOINT_ID = "endpoint_id"
_FIELD_POSE_POINT_DIRECTION = "pointDirection"
_FIELD_POSE_POSITION = "position"
_FIELD_POSE_YPR = "ypr"

#LEDs
_FIELD_POSE_LED_STATUS = "LEDStatus"
_FIELD_POSE_LED_COLOR = "color"
_FIELD_POSE_LED_ID= "led_id"


_ENDPOINT_SYSTEM = "/system"
_ENDPOINT_STATE = ""

class ServoID(StrEnum):
    BODY_YAW = "body_yaw"
    HEAD_YAW = "head_yaw"
    HEAD_ROLL = "head_roll"
    RIGHT_ELBOW = "right_elbow"
    LEFT_SHOULDER = "left_shoulder"
    HEAD_PITCH = "head_pitch"
    LEFT_ELBOW = "left_elbow"
    RIGHT_SHOULDER = "right_shoulder"

class EndpointID(StrEnum):
    HEAD = "head"
    RIGHT_HAND = "rightHand"
    LEFT_HAND = "leftHand"

class LedID(StrEnum):
    POWER = "power",
    LEFT_EYE = "leftEye",
    RIGHT_EYE = "rightEye",
    MOUTH = "mouth"

class Command(StrEnum):
    APPEND = "APPEND",
    PREPEND = "PREPEND",
    CLEAR_AND_ADD = "CLEAR_AND_ADD",
    INTERRUPT_AND_PREPEND = "INTERRUPT_AND_PREPEND"


@dataclass
class EndpointPose:
    point_direction: list[float] | None = None
    position: list[float] | None = None
    ypr: list[float] | None = None

@dataclass
class SotaState:
    joint_space: dict[ServoID, float] = field(default_factory=dict)
    world_space: dict[EndpointID, EndpointPose]  = field(default_factory=dict)
    leds: dict[LedID, str]  = field(default_factory=dict)
    servos_enabled: bool | None = None
    talking_led_enabled: bool | None = None


class PoseManager(HTTPConnector):
    def __init__(self, http_manager, end_point_path, error_print=True):
        super().__init__(http_manager, end_point_path, error_print)
        self.SERVO_MIN = {}
        self.SERVO_MAX = {}
        self._servos_enabled = False
        self._talking_led_enabled = False

    def _init_min_max(self, data):
        capabilities = data[_FIELD_SYSTEM_LIST_SERVO_CAPABILITIES]

        for entry in capabilities:
            id = ServoID(entry[_FIELD_POSE_SERVO_ID])
            self.SERVO_MIN[id] = entry[_FIELD_SYSTEM_RANGE_MIN]
            self.SERVO_MAX[id] = entry[_FIELD_SYSTEM_RANGE_MAX]

    def enable(self):
        self._init_min_max( self.get_state(use_cached=True))

    def disable(self):
        if self._servos_enabled: self.set_servos_enabled(False)
        if self._talking_led_enabled: self.set_talking_led_enabled(False)

    def get_state(self, use_cached: bool = False) -> dict | None:
        return self._get_state(_ENDPOINT_SYSTEM)

    def set_servos_enabled(self, enabled: bool) -> bool:
        self._servos_enabled = enabled
        return self._set_capability_enabled(endpoint=_ENDPOINT_SYSTEM, field=_FIELD_SYSTEM_SERVOS_ENABLED, enabled=enabled)

    def set_talking_led_enabled(self, enabled: bool) -> bool:
        self._talking_led_enabled = enabled
        return self._set_capability_enabled(endpoint=_ENDPOINT_SYSTEM, field=_FIELD_SYSTEM_TALKING_LED_ENABLED, enabled=enabled)

    def get_raw_state(self, use_cached=False) -> dict | None:
        return self._get_state(_ENDPOINT_STATE, use_cached=use_cached)

    def get_sota_state(self, use_cached: bool = False) -> SotaState:
        (joint_space, world_space, leds) = self._parse_raw_state(self.get_raw_state(use_cached))

        return SotaState(joint_space=joint_space,
                         world_space=world_space,
                         leds=leds,
                         servos_enabled=self._servos_enabled,
                         talking_led_enabled=self._talking_led_enabled)

    def send_command(self, state: SotaState, msec, command: Command = Command.APPEND):
        payload = {_FIELD_POSE_MOVE_MSEC: msec, _FIELD_POSE_COMMAND: command.value }

        if state.leds:
            payload[_FIELD_POSE_LED_STATUS] = [
                {_FIELD_POSE_LED_ID : led.value, _FIELD_POSE_LED_COLOR: color }
                for led, color in state.leds.items()
            ]

        if state.joint_space and state.world_space:  # both not empty
            print ("Error: you specified both joint and world space, defaulting to world space")
            state.joint_space = {}

        if state.joint_space:
            payload[_FIELD_POSE_SERVO_STATUS] = [
                {_FIELD_POSE_SERVO_ID: servo_id.value, _FIELD_POSE_RADIANS: radians}
                for servo_id, radians in state.joint_space.items()
            ]

        #only position is implemented for IK
        if state.world_space:
            payload[_FIELD_POSE_ENDPOINT_STATUS] = [
                {_FIELD_POSE_ENDPOINT_ID: item.value,
                 _FIELD_POSE_POSITION: pose.position
                 }
                for item, pose in state.world_space.items()
            ]

        return self._post_state(payload, _ENDPOINT_STATE)


    @staticmethod
    def _parse_raw_state(raw_state):
        joint_space = {}
        world_space = {}
        leds = {}

        for entry in raw_state[_FIELD_POSE_SERVO_STATUS]:
            servo_id = ServoID(entry[_FIELD_POSE_SERVO_ID])
            joint_space[servo_id] = entry[_FIELD_POSE_RADIANS]

        for entry in raw_state[_FIELD_POSE_ENDPOINT_STATUS]:
            servo_id = EndpointID(entry[_FIELD_POSE_ENDPOINT_ID])
            world_space[servo_id] = EndpointPose (
                point_direction=entry[_FIELD_POSE_POINT_DIRECTION],
                position=entry[_FIELD_POSE_POSITION],
                ypr=entry[_FIELD_POSE_YPR]
            )

        for entry in raw_state[_FIELD_POSE_LED_STATUS]:
            led_id = LedID(entry[_FIELD_POSE_LED_ID])
            leds[led_id] = entry[_FIELD_POSE_LED_COLOR]

        return joint_space, world_space, leds