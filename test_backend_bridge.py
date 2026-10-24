"""Run against the started backend: python3 -B test_backend_bridge.py."""
import os
import unittest
from uuid import uuid4

from backend_client import BackendClient, BackendError
from lead_inspection import load_inspection


class BridgeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = BackendClient(os.getenv("NOVA_BACKEND_URL", "http://127.0.0.1:8000"))

    def test_health(self):
        self.assertEqual(self.client.health(), {"status": "ok"})

    def test_existing_mongodb_demo_lead(self):
        lead = self.client.get_lead("sarah-johnson")
        self.assertEqual(lead["id"], "sarah-johnson")
        self.assertEqual(lead["name"], "Sarah Johnson")
        self.assertEqual(lead["student"]["name"], "Daniel")
        self.assertEqual(lead["businessId"], "nova-tutors")
        self.assertNotIn("_id", lead)
        print("Python retrieved Sarah Johnson through HTTP → agentTools → MongoDB.")

    def test_business_and_conversation_history(self):
        business = self.client.get_business("nova-tutors")
        self.assertEqual(business["name"], "Nova Tutors")
        history = self.client.get_conversation_history("sarah-johnson")
        self.assertIsInstance(history, list)
        for message in history:
            self.assertEqual(message["leadId"], "sarah-johnson")

    def test_missing_lead(self):
        with self.assertRaises(BackendError) as caught:
            self.client.get_lead("bridge-missing-" + str(uuid4()))
        self.assertEqual(caught.exception.status, 404)

    def test_streamlit_inspects_real_backend_without_changes(self):
        from unittest.mock import patch
        from streamlit.testing.v1 import AppTest

        before = load_inspection(self.client, "sarah-johnson")
        original_request = BackendClient._request
        calls = []

        def read_only(client, path, proposal=None, headers=None):
            self.assertIsNone(proposal, "Inspection attempted a POST")
            self.assertNotIn("/proposals/", path)
            calls.append(path)
            return original_request(client, path, proposal, headers)

        with patch.object(BackendClient, "_request", autospec=True, side_effect=read_only):
            app = AppTest.from_file("front.py").run(timeout=30)
            app.button(key="inspect_sarah_start").click().run(timeout=30)
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
            self.assertIn(before["lead"]["name"], [title.value for title in app.title])
            app.button(key="refresh_backend_lead").click().run(timeout=30)
            self.assertFalse(app.exception)
            self.assertEqual(len(app.chat_input), 0)
        self.assertTrue(any(path.endswith("/actions") for path in calls))
        self.assertEqual(load_inspection(self.client, "sarah-johnson"), before)
        print("Streamlit read live backend data; lead, conversation, and action records stayed unchanged.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
