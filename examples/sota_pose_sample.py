
from pprint import pprint
from time import sleep

from sota_thinclient.connection_manager import ConnectionManager
from sota_thinclient.pose import ServoID, EndpointID, LedID, SotaState, EndpointPose

# SOTA_IP = "10.0.0.178" # replace with your Sota's IP address
SOTA_IP = "192.168.0.23"
# SOTA_IP = "10.151.63.71"
HTTP_PORT = "8080"

sota = ConnectionManager(SOTA_IP, HTTP_PORT)
sota.pose.enable()

print("--- NOTE: press enter in the console after each test")
print("--- Basic capability and status"+ "-"*50)
print("System state and motor capabilities in radians")
pprint(sota.pose.get_state())  # also shows motor range capabilities
input()

print("\nCurrent pose, raw data from the server")
pprint(sota.pose.get_raw_state())
input()

print("\nPose can be read into an object for easy use.")
state = sota.pose.get_sota_state()

print("For example, position of the left hand")
print(state.world_space[EndpointID.LEFT_HAND].position)

print("\nOr the angle of the right shoulder")
print(state.joint_space[ServoID.RIGHT_SHOULDER])

print("\nor the color of the left eye")
print(state.leds[LedID.LEFT_EYE])

input()

print("\n--- Setting Robot State and commands"+ "-"*50)
print("You can make an empty SotaState object and only populate what you want done.")
newState = SotaState()

print("For example, to set the left eye to blue")
newState.leds[LedID.LEFT_EYE] = "#0000FF"

print("Setting a state needs a duration in milliseconds")
sota.pose.set_sota_state(newState, msec=1000)
input()

print("\nServos need to be \"enabled\" before you can move them. Otherwise the robot can be manually manipulated.")
sota.pose.set_servos_enabled(True)

print("You can set individual motors to desired positions.")
newState = SotaState() # start over
newState.joint_space[ServoID.RIGHT_SHOULDER] = -1
newState.joint_space[ServoID.LEFT_SHOULDER] = +1
sota.pose.set_sota_state(newState, msec=1000)
input()

print("You can use IK to put the hands where you want them. Currently only hand position tested.")
print("You can pause the program here and check that the hands are at the given height.")
newState = SotaState() # start over
newState.world_space[EndpointID.LEFT_HAND] = EndpointPose(position = [-0.04, -0.09, 0.1]) # all in metres
newState.world_space[EndpointID.RIGHT_HAND] = EndpointPose(position =  [-0.1, -.01, 0.13])
sota.pose.set_sota_state(newState, msec=1000)
input()

print("You can cue a series of commands and they'll just go in order.")
newState = SotaState() # start over
newState.joint_space[ServoID.RIGHT_SHOULDER] = 0
newState.joint_space[ServoID.LEFT_SHOULDER] = 0
sota.pose.set_sota_state(newState, msec=1000)

newState = SotaState()
newState.joint_space[ServoID.RIGHT_SHOULDER] = 1
newState.joint_space[ServoID.LEFT_SHOULDER] = -1
sota.pose.set_sota_state(newState, msec=300)

newState = SotaState()
newState.joint_space[ServoID.RIGHT_SHOULDER] = -1
newState.joint_space[ServoID.LEFT_SHOULDER] = 1
sota.pose.set_sota_state(newState, msec=300)

newState = SotaState()
newState.joint_space[ServoID.RIGHT_SHOULDER] = 1
newState.joint_space[ServoID.LEFT_SHOULDER] = -1
sota.pose.set_sota_state(newState, msec=300)

newState = SotaState()
newState.joint_space[ServoID.RIGHT_SHOULDER] = 0
newState.joint_space[ServoID.LEFT_SHOULDER] = 0
sota.pose.set_sota_state(newState, msec=1000)

input()

sota.pose.disable()