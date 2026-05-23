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


class HTTPConnector:   #an abstract base class that holds basic functions for other clases to use to connect to the manager

    def __init__(self, http_manager, end_point_path, error_print=True):
        self._http = http_manager
        self._end_point_path = end_point_path
        self._error_print = error_print
        self._state_cached = {}  # will be the state. empty means we don't have it

    def _get_state(self, endpoint="",
                   use_cached=False) -> dict | None:  # cached gets local copy if we have one instead of getting new
        if use_cached and self._state_cached:
            return self._state_cached

        self._state_cached = self._http.get_as_json(self._end_point_path + endpoint)
        return self._state_cached

    def _post_state(self, payload, endpoint="") -> bool:
        post_payload = self._http.post_dict_as_json(self._end_point_path + endpoint, payload)
        if post_payload is None: return False

        self._state_cached = post_payload  # save most recent state
        return True

    def _set_capability_enabled(self, field : str, enabled: bool, endpoint = "", restart_if_enabled=True, additional_fields : dict | None = None) -> bool:
        payload = self._get_state(endpoint)    #we need this to check if its already enabled
        if payload is None: return False

        field_data = payload.get(field)
        if field_data is None:
            if self._error_print: print(f"Field '{field}' not found for enabling feature, using endpoint '{endpoint}'.")
            return False

        if field_data == enabled:  # already enabled or disabled
            if not restart_if_enabled:
                return True

            # try to disable first
            if not self.disable():
                if self._error_print: print(
                    f"Error disabling '{field}' before enabling endpoint '{self._end_point_path}'.")
                return False

        payload[field] = enabled
        if additional_fields: payload |= additional_fields
        return self._post_state(payload, endpoint)

    def disable(self):
        pass