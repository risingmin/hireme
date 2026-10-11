import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('resume_router', ROOT / 'scripts/resume_router.py')
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / 'config/resume-routing.example.json').read_text())

    def decide(self, kind='internship', requirements=None, **kwargs):
        assessment = dict(posting_text='Requirement quoted here.', job_type=kind,
                          review_complete=True, uncertainties=[], requirements=requirements or [])
        assessment.update(kwargs)
        return router.route(self.config, assessment)

    def req(self, kind, **kwargs):
        return dict(type=kind, strength='required', evidence='Requirement quoted here.', **kwargs)

    def test_role_defaults(self):
        self.assertEqual(self.decide()['variant']['id'], 'dec-2027')
        self.assertEqual(self.decide('full_time')['variant']['id'], 'may-2027')

    def test_windows_and_exclusions(self):
        for low, high, expected in [(None, '2027-07', 'may-2027'),
                                    ('2027-08', '2028-01', 'dec-2027'),
                                    ('2027-05', '2027-12', 'dec-2027')]:
            with self.subTest(low=low, high=high):
                self.assertEqual(self.decide(requirements=[self.req('graduation_window', earliest=low, latest=high)])['variant']['id'], expected)
        self.assertEqual(self.decide(requirements=[self.req('graduation_window', latest='2027-04')])['status'], 'SKIP')

    def test_return_semester_and_conflict(self):
        returning = self.req('return_to_school', term='2027-fall')
        self.assertEqual(self.decide(requirements=[returning])['variant']['id'], 'dec-2027')
        self.assertEqual(self.decide(requirements=[returning, self.req('graduation_window', latest='2027-07')])['status'], 'SKIP')

    def test_start_dates(self):
        self.assertEqual(self.decide('full_time', [self.req('full_time_start', month='2027-06')])['variant']['id'], 'may-2027')
        self.assertEqual(self.decide('full_time', [self.req('full_time_start', month='2027-05')])['status'], 'NEEDS HUMAN')

    def test_uncertainty_evidence_and_preference(self):
        self.assertEqual(self.decide(uncertainties=['Dates unclear'])['status'], 'NEEDS HUMAN')
        self.assertEqual(self.decide(review_complete=False)['status'], 'NEEDS HUMAN')
        bad = self.req('graduation_window', latest='2027-04')
        bad['evidence'] = 'Not in posting'
        self.assertEqual(self.decide(requirements=[bad])['status'], 'NEEDS HUMAN')
        bad['evidence'] = 'Requirement quoted here.'
        bad['strength'] = 'preferred'
        self.assertEqual(self.decide(requirements=[bad])['status'], 'SELECT')
        self.assertEqual(self.decide(requirements=[self.req('unknown')])['status'], 'NEEDS HUMAN')
        self.assertEqual(self.decide(requirements=[self.req('graduation_window', latest='2027-08-01')])['status'], 'NEEDS HUMAN')

    def test_no_legal_overrides(self):
        self.config['variants'][0]['needs_visa_sponsorship'] = False
        with self.assertRaises(ValueError): router.validate(self.config)


if __name__ == '__main__':
    unittest.main()
