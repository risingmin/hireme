#!/usr/bin/env python3
"""Test the Codex CLI's browser connection using a local form and dummy data only."""
import hashlib
import http.server
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'state/browser-check.json'
CAPABILITIES = ('connected', 'native_input', 'upload', 'screenshot_saved', 'tab_cleanup')


def hook_digest():
    digest = hashlib.sha256()
    for name in ('.codex/config.toml', '.codex/hooks.json', '.codex/hooks/policy.py', 'scripts/preflight.py'):
        digest.update((ROOT / name).read_bytes())
    return digest.hexdigest()


def check_report():
    try:
        report = json.loads(REPORT.read_text())
    except (OSError, ValueError):
        raise ValueError('CLI browser preflight is missing. Run ./run.sh --browser-check after reviewing /hooks.')
    if report.get('hook_digest') != hook_digest() or not report.get('guard_active'):
        raise ValueError('CLI hooks need review and a fresh ./run.sh --browser-check.')
    if report.get('profile', '') != os.environ.get('JOBAPPLY_CODEX_PROFILE', ''):
        raise ValueError('Codex profile changed. Repeat ./run.sh --browser-check with that profile.')
    if not all(report.get(key) is True for key in CAPABILITIES):
        raise ValueError('CLI browser capabilities are incomplete. See state/browser-check.json.')
    if not (ROOT / 'state/browser-proof.jpg').is_file():
        raise ValueError('Browser screenshot proof is missing. Repeat ./run.sh --browser-check.')


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    if sys.argv[1:] == ['--require-report']:
        try:
            check_report()
            return 0
        except ValueError as error:
            print('ERROR: ' + str(error), file=sys.stderr)
            return 1
    cli = str(Path.home() / '.local/bin/codex')
    if not os.access(cli, os.X_OK):
        cli = shutil.which('codex')
    if not cli:
        print('ERROR: Codex CLI not found.', file=sys.stderr)
        return 1
    (ROOT / 'state').mkdir(exist_ok=True)
    (ROOT / 'state/browser-proof.jpg').unlink(missing_ok=True)
    token = secrets.token_hex(16)
    marker = ROOT / 'state' / ('.codex-browser-guard-' + token)
    with tempfile.TemporaryDirectory(prefix='jobapply-browser-') as tmp:
        fixture = Path(tmp)
        (fixture / 'resume.txt').write_text('DUMMY TEST FILE. No personal data.\n')
        (fixture / 'index.html').write_text('''<!doctype html><title>Job application browser test</title>
<h1>Local browser test — dummy data only</h1>
<label>Test name <input name="test_name"></label>
<label>Test document <input type="file" name="test_file"></label>
<p>This page has no submit action or external requests.</p>''')
        handler = lambda *args, **kwargs: Handler(*args, directory=tmp, **kwargs)
        try:
            server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
        except OSError:
            print('ERROR: Cannot serve the local dummy form. Run the browser check in a terminal with loopback access.', file=sys.stderr)
            return 1
        threading.Thread(target=server.serve_forever, daemon=True).start()
        keys = {key: {'type': 'boolean'} for key in CAPABILITIES}
        keys['blockers'] = {'type': 'array', 'items': {'type': 'string'}}
        schema = {'type': 'object', 'properties': keys, 'required': list(keys), 'additionalProperties': False}
        (fixture / 'schema.json').write_text(json.dumps(schema))
        prompt = f'''DEVELOPMENT ONLY: verify the Codex CLI browser adapter. This is not an application run.
Read docs/browser.md and the runtime browser documentation. Do not onboard, source jobs, read personal
config/resumes, access email/credentials/clipboard, or open real job sites. Inspect available tools.
If connected real Chrome is unavailable, return false capabilities with blockers and stop.
Otherwise create exactly one new owned tab at http://127.0.0.1:{server.server_port}/index.html.
Use native browser input to type DUMMY TEST into Test name. Verify its visible value.
Read file-upload documentation and attach {fixture / 'resume.txt'} using the supported chooser.
Verify that dummy filename is attached. Read the runtime screenshots documentation. Capture JPEG bytes
with tab.getScreenshot({{emit:false}}) (or its documented screenshot equivalent), then save them to
{ROOT / 'state/browser-proof.jpg'}. Local artifact export through standard Node filesystem APIs is
supported: const fs = await import('node:fs/promises'); await fs.writeFile(path, bytes).
Filesystem export is not a browser interaction. Do not convert or rename image bytes as PNG.
If upload permission is refused, record that blocker, do not retry, and still test screenshot saving
and cleanup independently. Close only the tab you created
and verify cleanup. Never claim, read, navigate, or close personal tabs. Do not use page-JS mutations.
Return the capability JSON. A capability is true only after it actually succeeded, not because docs list it.
The hook may be pending trust; do not bypass hook trust or approve permissions yourself.'''
        args = [cli, 'exec', '--ephemeral', '--approve-for-me',
                '--cd', str(ROOT), '--add-dir', tmp, '--output-schema', str(fixture / 'schema.json'),
                '--output-last-message', str(fixture / 'result.json'), prompt]
        if os.environ.get('JOBAPPLY_CODEX_PROFILE'):
            args[2:2] = ['--profile', os.environ['JOBAPPLY_CODEX_PROFILE']]
        environment = dict(os.environ, JOBAPPLY_BROWSER_CHECK_TOKEN=token)
        # Prevent an inherited application token from turning the dummy test into a fact check.
        environment.pop('JOBAPPLY_RUN_TOKEN', None)
        report = {key: False for key in CAPABILITIES}
        report['blockers'] = []
        try:
            result = subprocess.run(args, cwd=ROOT, env=environment, timeout=240)
            if result.returncode:
                report['blockers'].append('Codex browser test exited with status ' + str(result.returncode))
            else:
                parsed = json.loads((fixture / 'result.json').read_text())
                if not isinstance(parsed, dict):
                    raise ValueError('Invalid capability report')
                report.update(parsed)
        except (subprocess.TimeoutExpired, OSError, ValueError) as error:
            report['blockers'].append('Browser test did not complete: ' + type(error).__name__)
        finally:
            server.shutdown()
        report['guard_active'] = marker.is_file()
        report['hook_digest'] = hook_digest()
        report['profile'] = os.environ.get('JOBAPPLY_CODEX_PROFILE', '')
        if not report['guard_active']:
            report['blockers'].append('Project hooks did not run. Review/trust them with /hooks in Codex, then repeat this test.')
        marker.unlink(missing_ok=True)
        if not (ROOT / 'state/browser-proof.jpg').is_file():
            report['screenshot_saved'] = False
        REPORT.write_text(json.dumps(report, indent=2) + '\n')
        print('Browser preflight saved to state/browser-check.json')
        try:
            check_report()
        except ValueError as error:
            print('ERROR: ' + str(error), file=sys.stderr)
            return 1
        return 0


if __name__ == '__main__':
    sys.exit(main())
