# Sota thinclient
This module provides a Sota thinclient library for simple programming of a VStone Sota robot. This provides an API to
- read and sota pose values and capabilities.
  - pose includes motor positions and LED states, with motors given in radians and world-space cartesian coordinates.
  - motor positions can be set in radians or world-space cartesian coordinates.
  - Poses can be queued in order over time, or interrupt an action midway
- read and set Sota speaker, microphone parameters, and enable or disable streaming over UDP.
  - UDP port, sample rate, and buffer sizes can be set from the thinclient and requested from the Sota



## requirements
* This module requires the
Sota robot itself to be setup to run the matching [Sota thinserver](https://github.com/youngmb/sota_thinserver). Without
the thinserver this will not work.
* The Sota needs to maintain a network connection, you need to know its IP, and your used ports (e.g., http 8080 and 
selected ports for UDP) must be clear to use on the host machine as well as over the network.
* This was built and tested using Python 3.11
* The module depends on a few simple python modules defined in pyproject.toml and should be automatically installed via
pip as dependencies.
  * The test programs have different dependencies. You can automate installation with `pip install .[test]` in the 
  repository root folder

## Installation instructions
The module can be directly installed from github using pip and can be tested using the suite of example programs 
available on this repository.
- `pip install git+https://github.com/youngmb/sota_thinclient.git`

Alternatively, you can download the whole repository and install it locally. This may be more useful if you are 
actively modifying the thinclient to add or modify features. It is highly recommended to do this within a python
virtual environment.
- `git clone https://github.com/youngmb/sota_thinclient`
- `pip install -e .`  The -e tells python that you may edit the files, don't cache them.


## usage and testing
The API is not well documented, but rather, we have provided a suite of examples in `examples/`. All example programs
should run, and you can examine them for usage.

Overall we designed the structure to be very flat and simple to understand, relying mostly on simple objects and 
python dictionaries. Simple inspection should clarify most of the API.

## configuration
All configurable variables are shown in the test programs. Any changes to underlying constants relating to networking, 
or endpoint or field labels, would need to be modified concurrently in the thinserver.