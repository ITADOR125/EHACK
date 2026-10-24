"""Read-only Nova localhost client; uses only the Python standard library."""
import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen


class BackendError(RuntimeError):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


class BackendClient:
    def __init__(self, base_url="http://127.0.0.1:8000", timeout=10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path):
        try:
            with urlopen(self.base_url + path, timeout=self.timeout) as response:
                return json.load(response)
        except HTTPError as error:
            raise BackendError(
                "Backend returned HTTP {}".format(error.code), error.code
            ) from error
        except (URLError, TimeoutError, OSError) as error:
            raise BackendError("Cannot reach the Nova backend") from error

    def health(self):
        return self._get("/health")

    def get_business(self, business_id):
        return self._get("/businesses/" + quote(business_id, safe=""))

    def get_lead(self, lead_id):
        return self._get("/leads/" + quote(lead_id, safe=""))

    def get_conversation_history(self, lead_id):
        return self._get("/leads/" + quote(lead_id, safe="") + "/messages")
