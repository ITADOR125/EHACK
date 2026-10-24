"""Nova localhost client, including the narrow qualification-question record gate."""
import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class BackendError(RuntimeError):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


class BackendClient:
    def __init__(self, base_url="http://127.0.0.1:8000", timeout=10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path):
        return self._request(path)

    def _request(self, path, proposal=None, headers=None):
        request = self.base_url + path
        if proposal is not None:
            request = Request(request, data=json.dumps(proposal).encode("utf-8"),
                              headers={"Content-Type": "application/json", **(headers or {})}, method="POST")
        try:
            with urlopen(request, timeout=self.timeout) as response:
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

    def get_agent_actions(self, lead_id):
        return self._get("/leads/" + quote(lead_id, safe="") + "/actions")

    def evaluate_proposal(self, proposal):
        """Return backend safety preflight; never execute the proposed action."""
        return self._request("/proposals/evaluate", proposal)

    def execute_proposal(self, proposal, execution_key):
        """Record a question only if backend safety allows it. Reuse the key on retries.

        No customer message is sent and no proposed lead updates are applied.
        Non-act decisions raise BackendError with HTTP status 409.
        """
        return self._request("/proposals/execute", proposal, {"Idempotency-Key": execution_key})
