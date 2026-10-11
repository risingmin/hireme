import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('preflight', ROOT / 'scripts/preflight.py')
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


class CodexPortTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        for name in ('scripts', '.codex', 'config'):
            shutil.copytree(ROOT / name, self.repo / name)
        shutil.copy(ROOT / 'run.sh', self.repo / 'run.sh')
        (self.repo / 'state').mkdir()
        (self.repo / 'data').mkdir()
        self.settings = json.loads((self.repo / 'config/settings.example.json').read_text())
        (self.repo / 'config/settings.json').write_text(json.dumps(self.settings))
        self.profile = dict(name_legal='Test Candidate', first_name='Test', last_name='Candidate',
                            email='candidate@test.invalid', resume='data/resume.pdf')
        (self.repo / 'config/profile.json').write_text(json.dumps(self.profile))
        (self.repo / 'config/answers.md').write_text('Confirmed test fact: Built a compiler with 12 test cases.\n')
        (self.repo / 'data/resume.pdf').write_bytes(b'%PDF-1.4 dummy test document')
        self.approve()

    def tearDown(self):
        self.tmp.cleanup()

    def test_routing_documents_require_review_and_tampering_stops_run(self):
        routing = json.loads((ROOT / 'config/resume-routing.example.json').read_text())
        (self.repo / 'config/resume-routing.json').write_text(json.dumps(routing))
        for variant in routing['variants']:
            (self.repo / variant['resume']).write_bytes(b'%PDF-1.4 variant fixture')
        with self.assertRaises(ValueError):
            preflight.check(self.repo)
        self.approve()
        preflight.check(self.repo)
        prompt = subprocess.run(['bash', 'run.sh', '--print-prompt'], cwd=self.repo,
                                capture_output=True, text=True)
        self.assertEqual(prompt.returncode, 0, prompt.stderr)
        self.assertIn('Resume routing is enabled', prompt.stdout)
        (self.repo / routing['variants'][1]['resume']).write_bytes(b'changed resume')
        with self.assertRaises(ValueError):
            preflight.check(self.repo)

    def approve(self):
        (self.repo / preflight.MANIFEST).write_text(json.dumps(preflight.snapshot(self.repo)))

    def launch(self, *args, **env):
        return subprocess.run(['bash', str(self.repo / 'run.sh'), *args], cwd=self.repo,
                              env=dict(os.environ, **env), text=True, capture_output=True)

    def hook(self, payload, **env):
        return subprocess.run(['python3', str(self.repo / '.codex/hooks/policy.py')],
                              input=json.dumps(payload), env=dict(os.environ, **env),
                              cwd=self.repo, text=True, capture_output=True)

    def test_reviewed_config_and_document_changes_stop_run(self):
        self.assertEqual(preflight.check(self.repo), preflight.snapshot(self.repo))
        (self.repo / 'data/resume.pdf').write_bytes(b'changed resume')
        with self.assertRaisesRegex(ValueError, 'changed since approval'):
            preflight.check(self.repo)
        self.approve()
        self.settings['targets']['locations'] = ['Pittsburgh']
        (self.repo / 'config/settings.json').write_text(json.dumps(self.settings))
        with self.assertRaises(ValueError):
            preflight.check(self.repo)

    def test_missing_documents_placeholders_and_disabled_safety_fail(self):
        (self.repo / 'data/resume.pdf').unlink()
        with self.assertRaises(OSError):
            preflight.check(self.repo)
        (self.repo / 'data/resume.pdf').write_bytes(b'test')
        self.settings['safety']['never_fabricate_a_fact'] = False
        (self.repo / 'config/settings.json').write_text(json.dumps(self.settings))
        with self.assertRaisesRegex(ValueError, 'cannot be disabled'):
            preflight.snapshot(self.repo)

    def test_missing_interview_tracker_fails_closed(self):
        self.settings['run']['interview_tracker_path'] = str(self.repo / 'missing-note')
        (self.repo / 'config/settings.json').write_text(json.dumps(self.settings))
        with self.assertRaises(OSError):
            preflight.snapshot(self.repo)

    def test_prompt_preserves_sourcing_sponsorship_and_caps_without_launching(self):
        self.settings['eligibility']['needs_visa_sponsorship'] = True
        (self.repo / 'config/settings.json').write_text(json.dumps(self.settings))
        result = self.launch('--print-prompt', '1')
        self.assertEqual(result.returncode, 0, result.stderr)
        for text in ('at most 1', 'needs visa sponsorship', 'Skip employers that state they do not sponsor',
                     'delta_sweep.py', 'portal_sweep.py', 'list_sweep.py', 'linkedin_sweep.py',
                     'AGENTS.md', 'docs/browser.md', 'Never fabricate a fact', 'personal tabs'):
            self.assertIn(text, result.stdout)
        self.assertFalse((self.repo / '.hourly-run.lock').exists())
        self.assertEqual(self.launch('-1').returncode, 2)

    def test_no_cli_launch_without_browser_proof(self):
        fake = self.repo / 'fake-codex'
        fake.write_text('#!/bin/sh\ntouch launched\n')
        fake.chmod(0o755)
        result = self.launch('1', JOBAPPLY_CODEX_BIN=str(fake))
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.repo / 'launched').exists())

    def test_launcher_uses_codex_and_keeps_live_lock(self):
        # Prepare the non-personal browser capability proof in this isolated fixture.
        spec = importlib.util.spec_from_file_location('browser', self.repo / 'scripts/browser_check.py')
        browser = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(browser)
        proof = {key: True for key in browser.CAPABILITIES}
        proof.update(guard_active=True, hook_digest=browser.hook_digest())
        (self.repo / 'state/browser-check.json').write_text(json.dumps(proof))
        (self.repo / 'state/browser-proof.jpg').write_bytes(b'dummy JPEG')
        fake = self.repo / 'fake-codex'
        fake.write_text('#!/usr/bin/env python3\nimport json,sys\nfrom pathlib import Path\nPath("captured.json").write_text(json.dumps(sys.argv[1:]))\n')
        fake.chmod(0o755)
        result = self.launch('1', JOBAPPLY_CODEX_BIN=str(fake))
        self.assertEqual(result.returncode, 0, result.stderr)
        args = json.loads((self.repo / 'captured.json').read_text())
        self.assertEqual(args[0], 'exec')
        self.assertIn('--ephemeral', args)
        self.assertIn('--approve-for-me', args)
        self.assertNotIn('--dangerously-bypass-approvals-and-sandbox', args)
        self.assertFalse((self.repo / '.hourly-run.lock').exists())
        (self.repo / '.hourly-run.lock').mkdir()
        (self.repo / '.hourly-run.lock/pid').write_text(str(os.getpid()))
        result = self.launch('1', JOBAPPLY_CODEX_BIN=str(fake))
        self.assertIn('Another run', result.stdout)
        self.assertTrue((self.repo / '.hourly-run.lock').exists())

    def test_secret_guard_handles_shell_and_browser_code(self):
        for code in ('security find-generic-password -w', 'pbpaste', 'tab.clipboard.readText()',
                     'cat ~/.codex/auth.json'):
            result = self.hook(dict(hook_event_name='PreToolUse', tool_input={'code': code}))
            self.assertEqual(result.returncode, 2, code)
        result = self.hook(dict(hook_event_name='PreToolUse', tool_input={'command': 'python3 scripts/code_broker.py check'}))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_bad_hook_input_is_denied(self):
        result = self.hook([])
        self.assertEqual(result.returncode, 2)

    def test_browser_proof_is_invalidated_by_hook_or_profile_change(self):
        spec = importlib.util.spec_from_file_location('browser', self.repo / 'scripts/browser_check.py')
        browser = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(browser)
        proof = {key: True for key in browser.CAPABILITIES}
        proof.update(guard_active=True, hook_digest=browser.hook_digest(), profile='different-profile')
        (self.repo / 'state/browser-check.json').write_text(json.dumps(proof))
        (self.repo / 'state/browser-proof.jpg').write_bytes(b'dummy JPEG')
        with self.assertRaisesRegex(ValueError, 'profile changed'):
            browser.check_report()
        proof['profile'] = os.environ.get('JOBAPPLY_CODEX_PROFILE', '')
        (self.repo / 'state/browser-check.json').write_text(json.dumps(proof))
        browser.check_report()
        (self.repo / '.codex/hooks/policy.py').write_text('# changed guard')
        with self.assertRaisesRegex(ValueError, 'hooks need review'):
            browser.check_report()

    def test_startup_guard_and_mid_run_fact_tampering(self):
        token = 'a' * 32
        start = self.hook(dict(hook_event_name='SessionStart'), JOBAPPLY_RUN_TOKEN=token)
        self.assertEqual(start.returncode, 0)
        self.assertTrue((self.repo / ('state/.codex-guard-' + token)).exists())
        (self.repo / 'config/answers.md').write_text('Changed personal fact')
        result = self.hook(dict(hook_event_name='PreToolUse', tool_input={'command': 'date'}), JOBAPPLY_RUN_TOKEN=token)
        self.assertEqual(result.returncode, 2)
        result = self.hook(dict(hook_event_name='SessionStart'), JOBAPPLY_RUN_TOKEN=token)
        self.assertFalse(json.loads(result.stdout)['continue'])


if __name__ == '__main__':
    unittest.main()
