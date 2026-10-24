import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from backend_client import BackendClient, BackendError
from lead_inspection import load_inspection
from test_brain_adapter import BUSINESS, SARAH


class LeadInspectionTests(unittest.TestCase):
    def setUp(self):
        self.lead = {**copy.deepcopy(SARAH), "name": "Sarah Johnson (backend)",
                     "currentGrade": 4, "status": "contacted"}
        self.business = copy.deepcopy(BUSINESS)
        self.messages = [
            {"id": "message1", "leadId": SARAH["id"], "sender": "customer", "content": "Backend customer message", "timestamp": "2026-01-01T10:00:00Z"},
            {"id": "message2", "leadId": SARAH["id"], "sender": "owner", "content": "Backend owner note", "timestamp": "2026-01-01T10:01:00Z"},
        ]
        self.actions = [{"id": "action1", "leadId": SARAH["id"], "action": "record_qualification_question",
                         "reason": "Backend recorded reason", "status": "completed", "timestamp": "2026-01-01T10:02:00Z"}]
        self.requests = []

    def read(self, path, proposal=None, headers=None):
        self.assertIsNone(proposal, "Viewing a lead must never POST")
        self.assertIsNone(headers)
        self.requests.append(path)
        routes = {
            "/leads/sarah-johnson": self.lead, "/businesses/nova-tutors": self.business,
            "/leads/sarah-johnson/messages": self.messages, "/leads/sarah-johnson/actions": self.actions,
        }
        self.assertIn(path, routes, "Unexpected non-inspection endpoint")
        return copy.deepcopy(routes[path])

    @staticmethod
    def visible(app):
        return "\n".join(str(element.value) for kind in ["title", "markdown", "caption", "text"]
                         for element in getattr(app, kind))

    def test_loader_uses_only_reads_and_keeps_records_canonical(self):
        with patch.object(BackendClient, "_request", side_effect=self.read):
            snapshot = load_inspection(BackendClient(), "sarah-johnson")
        self.assertEqual(snapshot["lead"], self.lead)
        self.assertEqual(snapshot["messages"], self.messages)
        self.assertEqual(snapshot["actions"], self.actions)
        self.assertEqual(len(self.requests), 4)

    def test_streamlit_open_refresh_and_back_never_run_agent_or_execution(self):
        files = [Path("nova_profile.json"), Path("data/sessions.json")]
        original_files = {path: path.read_bytes() for path in files if path.exists()}
        original_state = copy.deepcopy((self.business, self.lead, self.messages, self.actions))
        with patch.object(BackendClient, "_request", side_effect=self.read), \
             patch.object(BackendClient, "execute_proposal", side_effect=AssertionError("Execution called")) as execute, \
             patch.object(BackendClient, "evaluate_proposal", side_effect=AssertionError("Evaluation called")) as evaluate, \
             patch("agent.analyse_lead", side_effect=AssertionError("Analysis called")) as analyse, \
             patch("agent.draft_reply", side_effect=AssertionError("Drafting called")) as draft, \
             patch("brain.decide_next_action", side_effect=AssertionError("Brain called")) as brain:
            app = AppTest.from_file("front.py").run()
            self.assertFalse(app.exception)
            app.button(key="inspect_sarah_start").click().run()
            self.assertFalse(app.exception)
            text = self.visible(app)
            for expected in ["Sarah Johnson (backend)", "Status: contacted", "Current grade: 4",
                             "Exam board: Unknown", "Backend customer message", "Backend owner note",
                             "Backend recorded reason", "record_qualification_question"]:
                self.assertIn(expected, text)
            self.assertEqual(len(app.chat_input), 0)
            self.assertEqual(len(app.text_area), 0)
            for forbidden in ["Approve and send", "Send reply (simulated)", "Reset this lead", "End conversation"]:
                self.assertNotIn(forbidden, [button.label for button in app.button])
            self.lead["currentGrade"] = 6
            app.button(key="refresh_backend_lead").click().run()
            self.assertIn("Current grade: 6", self.visible(app))
            app.button(key="backend_lead_back").click().run()
            self.assertEqual(app.session_state["stage"], "start")
            for mock in [execute, evaluate, analyse, draft, brain]:
                mock.assert_not_called()
        self.lead["currentGrade"] = 4
        self.assertEqual((self.business, self.lead, self.messages, self.actions), original_state)
        for path, content in original_files.items():
            self.assertEqual(path.read_bytes(), content)

    def test_dashboard_uses_backend_sarah_instead_of_duplicate_demo(self):
        with patch.object(BackendClient, "_request", side_effect=self.read):
            app = AppTest.from_file("front.py").run()
            app.session_state["stage"] = "active"
            app.session_state["leads"] = [{"id": "sarah", "parent": "STALE DEMO SARAH"}]
            app.run()
            self.assertFalse(app.exception)
            self.assertIn("Sarah Johnson (backend)", self.visible(app))
            self.assertNotIn("STALE DEMO SARAH", self.visible(app))
            self.assertEqual(app.session_state["leads"], [])
            app.button(key="open_backend_sarah").click().run()
            self.assertFalse(app.exception)
            self.assertIn("Backend recorded reason", self.visible(app))

    def test_backend_failure_shows_error_without_mock_fallback(self):
        with patch.object(BackendClient, "_request", side_effect=BackendError("Backend offline")):
            app = AppTest.from_file("front.py").run()
            app.button(key="inspect_sarah_start").click().run()
            self.assertFalse(app.exception)
            self.assertTrue(app.error)
            self.assertNotIn("Sarah Johnson", self.visible(app))
            self.assertEqual(len(app.chat_input), 0)

    def test_empty_history_and_actions_are_displayed_without_fabrication(self):
        self.messages, self.actions = [], []
        with patch.object(BackendClient, "_request", side_effect=self.read):
            app = AppTest.from_file("front.py").run()
            app.button(key="inspect_sarah_start").click().run()
            self.assertIn("No recorded messages.", self.visible(app))
            self.assertIn("No recorded agent actions.", self.visible(app))


if __name__ == "__main__":
    unittest.main()
