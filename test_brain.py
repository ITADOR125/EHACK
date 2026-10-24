import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import brain

EMPTY = {'facts': {}, 'quotes': {}}


class NovaTests(unittest.TestCase):
    def decide(self, lead_key, message, raw=None):
        return brain.decide_next_action(
            brain.BUSINESS, copy.deepcopy(brain.SEED_LEADS[lead_key]),
            [{'role': 'customer', 'content': message}],
            extraction_override=raw if raw is not None else EMPTY
        )

    def test_sarah_needs_info(self):
        d = self.decide('sarah', 'My son needs GCSE Maths support.')
        self.assertEqual(d['lead_status'], 'needs_information')
        self.assertEqual(d['next_action'], 'ask_customer')

    def test_rachel_price(self):
        d = self.decide('rachel', 'How much does GCSE Maths tutoring cost?')
        self.assertEqual(d['next_action'], 'answer_customer')
        self.assertIn('£30', d['message'])
        self.assertEqual(d['lead_status'], d['updated_lead']['lead_status'])
        self.assertEqual(d['lead_status'], 'consultation_needed')

    def test_rachel_consultation(self):
        d = self.decide('rachel', 'Could we have the free consultation?')
        self.assertEqual(d['next_action'], 'recommend_consultation')
        self.assertEqual(d['lead_status'], 'consultation_needed')
        self.assertTrue(d['requires_human_approval'])
        self.assertNotIn('booked', d['message'].lower())

    def test_james_unsupported(self):
        d = self.decide('james', brain.SEED_LEADS['james']['initial_message'])
        self.assertEqual(d['lead_status'], 'not_qualified')
        self.assertEqual(d['next_action'], 'close_lead')
        self.assertIn('university-level', d['message'])

    def test_university_admissions_price_escalation(self):
        d = self.decide('rachel', 'How much does university admissions application support cost?')
        self.assertEqual(d['next_action'], 'escalate_to_human')
        self.assertEqual(d['lead_status'], 'consultation_needed')
        self.assertEqual(d['review_status'], 'pending')
        self.assertEqual(d['escalation']['status'], 'requested_not_routed')
        self.assertNotIn('£', d['message'])

    def test_alevel_price_escalation(self):
        d = self.decide('rachel', 'What are your A-Level prices?')
        self.assertEqual(d['next_action'], 'escalate_to_human')
        self.assertNotIn('£', d['message'])

    def test_in_person_not_booked(self):
        d = self.decide('rachel', 'Can you confirm in-person tutoring tomorrow at 6?')
        self.assertEqual(d['next_action'], 'escalate_to_human')
        self.assertIn('availability', d['message'])

    def test_extraction_specific(self):
        latest = 'He is studying Edexcel Higher.'
        raw = {'facts': {'exam_board': 'Edexcel', 'tier': 'Higher', 'current_grade': 'Grade 9'},
               'quotes': {'exam_board': 'Edexcel', 'tier': 'Higher', 'current_grade': 'Edexcel'}}
        d = self.decide('sarah', latest, raw)
        self.assertEqual(d['extracted_information'], {'exam_board': 'Edexcel', 'tier': 'Higher'})
        self.assertEqual(d['updated_lead']['exam_board'], 'Edexcel')
        self.assertNotIn('current_grade', d['extracted_information'])

    def test_rejected_unquoted_fact(self):
        d = self.decide('sarah', 'Hi', {'facts': {'exam_board': 'Edexcel'}, 'quotes': {'exam_board': 'Edexcel'}})
        self.assertEqual(d['extracted_information'], {})

    def test_pricing_another_service_does_not_reassign(self):
        q = 'Do you offer GCSE History and what does that cost?'
        raw = {'facts': {'subject': 'GCSE History'}, 'quotes': {'subject': 'GCSE History'}}
        d = self.decide('rachel', q, raw)
        self.assertEqual(d['updated_lead']['subject'], 'GCSE Maths')

    def test_existing_qualified_survives_escalation(self):
        lead = copy.deepcopy(brain.SEED_LEADS['sarah'])
        lead['lead_status'] = 'qualified'
        d = brain.decide_next_action(brain.BUSINESS, lead,
            [{'role': 'customer', 'content': 'How much is university admissions support?'}],
            extraction_override=EMPTY)
        self.assertEqual(d['lead_status'], 'qualified')
        self.assertEqual(d['review_status'], 'pending')

    def test_no_realtime_bookings(self):
        d = self.decide('rachel', 'Please book a session with a tutor at 6 PM tonight')
        self.assertNotIn('confirmed', d['message'].lower())

    def test_unsupported_gcse_pricing_never_quoted(self):
        d = self.decide('rachel', 'How much does GCSE History cost?')
        self.assertEqual(d['next_action'], 'answer_customer')
        self.assertNotIn('£30', d['message'])
        self.assertIn('not services', d['message'])

    def test_blank_subject_asks_first(self):
        d = brain.decide_next_action(brain.BUSINESS, {'id': 'new', 'name': 'Alex'},
            [{'role': 'customer', 'content': 'Hello'}], extraction_override=EMPTY)
        self.assertEqual(d['next_action'], 'ask_customer')

    def test_local_sessions_dont_mix(self):
        data = {'active': 'sarah', 'sessions': {k: brain.new_session(v) for k,v in brain.SEED_LEADS.items()}}
        data['sessions']['sarah']['conversation'].append({'role':'customer','content':'Only Sarah fact'})
        self.assertEqual(data['sessions']['rachel']['conversation'], [])
        self.assertEqual(data['sessions']['james']['conversation'], [])

    def test_local_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(brain, 'DATA_FILE', Path(tmp) / 'sessions.json'):
                d = brain.load_sessions()
                d['sessions']['rachel']['conversation'].append({'role': 'customer','content': 'hello'})
                brain.save_sessions(d)
                loaded = brain.load_sessions()
                self.assertEqual(len(loaded['sessions']['rachel']['conversation']), 1)
                self.assertEqual(len(loaded['sessions']['sarah']['conversation']), 0)


if __name__ == '__main__':
    unittest.main()
