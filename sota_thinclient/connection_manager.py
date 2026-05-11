from sota_thinclient.http_audio_stream import HTTPAudioStream
from sota_thinclient.http import HTTPManager
from sota_thinclient.udp_stream import UDPStreamReceiver, UDPStreamSender


class ConnectionManager:

    MIC_END_POINT = "/mic"
    SPEAKER_END_POINT = "/speaker"

    def __init__(self, host, http_port):
        self.host = host
        self.http = HTTPManager(host, http_port)

        self.microphone = HTTPAudioStream(self.http, self.MIC_END_POINT, UDPStreamReceiver("0.0.0.0"))
        self.speaker = HTTPAudioStream(self.http, self.SPEAKER_END_POINT, UDPStreamSender(host))


