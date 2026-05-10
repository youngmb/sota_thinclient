from sota_thinclient.audio import Microphone
from sota_thinclient.http import HTTPManager


class ConnectionManager:

    def __init__(self, host, http_port):
        self.host = host
        self.http = HTTPManager(host, http_port)

        self.microphone = Microphone(self.http)


