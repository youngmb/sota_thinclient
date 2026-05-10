from dataclasses import dataclass
from http import HTTPStatus

import requests
from requests.exceptions import ConnectionError, Timeout, RequestException

class HTTPManager:

    def __init__(self, host, http_port, error_print=True, timeout=3):
        self.host = host
        self.http_port = http_port
        self.uri_base = f"http://{host}:{http_port}"
        self.timeout = timeout
        self.error_print = error_print

    def get_as_json(self, path) -> dict | None:
        try:
            r = requests.get(self.uri_base+path, timeout=self.timeout)
            if r.status_code != HTTPStatus.OK:
                if self.error_print: self._print_response(r)
                return None

        except ConnectionError as e:
            if (self.error_print):
                print("Error connecting to "+self.uri_base+path)
                print(e)
                return None

        return r.json()

    def post_dict_as_json(self, path, json_dict) -> dict | None:
        r = requests.post(self.uri_base+path, json=json_dict, timeout=self.timeout)
        if r.status_code != HTTPStatus.OK:
            if self.error_print: self._print_response(r)
            return None

        return r.json()

    @staticmethod
    def _print_response(r):
        print(f"Status: {r.status_code}", end=None)
        print(r.json())