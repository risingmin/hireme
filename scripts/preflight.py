#!/usr/bin/env python3
"""Validate config and record approval of exact facts without printing personal values."""
import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path('state/facts-approved.json')
SAFETY = ('never_create_accounts', 'never_solve_interactive_captcha',
          'never_fabricate_a_fact', 'screenshot_every_submit', 'require_log_before_submit')


def snapshot(root):
    settings = json.loads((root / 'config/settings.json').read_text())
    profile = json.loads((root / 'config/profile.json').read_text())
    answers = (root / 'config/answers.md').read_text()
    if not isinstance(settings, dict) or not isinstance(profile, dict):
        raise ValueError('Settings and profile must be JSON objects.')
    for section in ('run', 'targets', 'eligibility', 'channels', 'safety'):
        if not isinstance(settings.get(section), dict):
            raise ValueError('Missing or invalid settings section: ' + section)
    for key in SAFETY:
        if settings['safety'].get(key, True) is not True:
            raise ValueError('Safety rule cannot be disabled: ' + key)
    for key in ('max_applications_per_run', 'max_applications_per_company_lifetime'):
        value = settings['run'].get(key, 3 if key.endswith('_run') else 2)
        if type(value) is not int or value < 0:
            raise ValueError('run.' + key + ' must be a non-negative integer.')
    for key in ('name_legal', 'first_name', 'last_name', 'email', 'resume'):
        value = profile.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError('Missing profile field: ' + key)
        if re.search(r'Firstname|Lastname|you@example\.com|\byourhandle\b', value, re.I):
            raise ValueError('Unfilled example profile field: ' + key)
    if not answers.strip() or answers == (root / 'config/answers.example.md').read_text():
        raise ValueError('Fill config/answers.md with your confirmed facts and presets first.')
    if re.search(r'\[(?:One paragraph|Job, internship|Something you own|Research, analysis|Education:|your score|answer\])', answers, re.I):
        raise ValueError('config/answers.md still contains example placeholders.')
    tracker = settings['run'].get('interview_tracker_path', '')
    if tracker:
        Path(tracker).read_text()  # fail closed when configured but unreadable
    files = ['config/settings.json', 'config/profile.json', 'config/answers.md']
    files += [profile[k] for k in ('resume', 'transcript') if profile.get(k)]
    routing = root / 'config/resume-routing.json'
    if routing.exists():
        # Review covers every selectable PDF, not just the legacy profile resume.
        spec = importlib.util.spec_from_file_location('resume_router', Path(__file__).with_name('resume_router.py'))
        router = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(router)
        variants = router.validate(json.loads(routing.read_text()))
        files.append('config/resume-routing.json')
        files.extend(v['resume'] for v in variants)
    digests = {}
    for name in files:
        path = root / name
        digests[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digests


def check(root, require_approval=True):
    current = snapshot(root)
    if require_approval:
        try:
            approved = json.loads((root / MANIFEST).read_text())
        except (OSError, ValueError):
            raise ValueError('Facts need review. After reviewing your config and documents, run python3 scripts/preflight.py approve.')
        if approved != current:
            raise ValueError('Config or uploaded documents changed since approval. Review and approve the updated facts before running.')
    return current


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check', 'approve'], nargs='?', default='check')
    args = parser.parse_args()
    try:
        if args.action == 'approve':
            current = snapshot(ROOT)
            print('Review config/profile.json, config/answers.md, config/settings.json, optional config/resume-routing.json, and every upload document.')
            print('Verify all identity, authorization, dates, numbers, EEO, and willingness answers.')
            if input('Type APPROVE to record review of these exact files: ').strip() != 'APPROVE':
                raise ValueError('Approval was not recorded.')
            (ROOT / MANIFEST).parent.mkdir(parents=True, exist_ok=True)
            (ROOT / MANIFEST).write_text(json.dumps(current, indent=2) + '\n')
            print('Fact review recorded. Changes require a new review.')
        else:
            check(ROOT)
            print('Config, documents, safety rules, and fact approval: OK')
    except (OSError, ValueError, TypeError, KeyError, EOFError) as error:
        print('ERROR: ' + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
