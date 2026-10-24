"""Run against the started backend: python3 -B test_backend_bridge.py."""
import os
import unittest
from uuid import uuid4

from backend_client import BackendClient, BackendError


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
