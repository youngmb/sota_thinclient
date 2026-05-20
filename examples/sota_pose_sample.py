import time

from sota_thinclient.connection_manager import ConnectionManager

SOTA_IP = "10.0.0.178" # replace with your Sota's IP address
HTTP_PORT = "8080"
TEST_MOVE_MSEC = 1000

def test_read_system_status(sota):
    system_status = sota.pose.get_system_status()
    assert system_status is not None
    print("System status:\n", system_status)
    
def test_set_system_status(sota):
    sota.pose.set_servos_enabled(True)
    status = sota.pose.get_system_status()
    assert status is not None
    assert status[sota.pose._FIELD_SYSTEM_SERVOS_ENABLED] == True
    
def test_get_pose_jointspace(sota):
    pose = sota.pose.get_pose_jointspace()
    assert pose is not None
    print("current pose:\n", pose)
    
def test_send_pose_jointspace(sota):
    # attempt to append to queue (create other tests for other queue operations)
    pose = sota.pose.get_pose_jointspace()
    servo_positions = pose[sota.pose._FIELD_POSE_SERVO_STATUS]
    for servo in servo_positions:
        servo['radians'] = 0  # set to a neutral position for test
    result = sota.pose.send_pose_jointspace(
        servo_positions=servo_positions,
        led_positions=pose[sota.pose._FIELD_POSE_LED_STATUS],
        move_msec=TEST_MOVE_MSEC,
        command="APPEND"
    )
    assert result == True

sota = ConnectionManager(SOTA_IP, HTTP_PORT)

test_read_system_status(sota)
test_set_system_status(sota)
test_get_pose_jointspace(sota)
test_send_pose_jointspace(sota)

time.sleep(TEST_MOVE_MSEC / 1000)
sota.pose.set_servos_enabled(False)