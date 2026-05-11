from dataclasses import dataclass
from http import HTTPStatus

import requests
from requests.exceptions import ConnectionError, Timeout, RequestException

class HTTPManager:

    def __init__(self, host, http_port, error_print=True, timeout=3):
        self.host = host
        self._http_port = http_port
        self._http_base = f"http://{host}:{http_port}"
        self._timeout = timeout
        self._error_print = error_print

    def get_uri(self, host, port, end_point) -> str:
        return self._http_base+end_point

    def get_as_json(self, end_point) -> dict | None:
        try:
            r = requests.get(self._http_base + end_point, timeout=self._timeout)
            if r.status_code != HTTPStatus.OK:
                if self._error_print: self._print_response(r)
                return None

        except ConnectionError as e:
            if (self._error_print):
                print("Error connecting to " + self._http_base + end_point)
                print(e)
                return None

        return r.json()

    def post_dict_as_json(self, end_point, json_dict) -> dict | None:
        r = requests.post(self._http_base + end_point, json=json_dict, timeout=self._timeout)
        if r.status_code != HTTPStatus.OK:
            if self._error_print: self._print_response(r)
            return None

        return r.json()

    @staticmethod
    def _print_response(r):
        print(f"Status: {r.status_code}", end=None)
        print(r.json())