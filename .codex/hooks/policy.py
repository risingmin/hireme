#!/usr/bin/env python3
"""Best-effort secret guard, plus exact reviewed-file integrity during job runs.

This is a hook, not an OS sandbox. Trust it with /hooks; do not bypass hook trust.
"""
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from preflight import check

SECRET = re.compile(
    r'find-(?:generic|internet)-password|dump-keychain|export-keychain|pbpaste|'
    r'generalPasteboard|NSPasteboard|stringForType|get the clipboard|clipboard info|'
    r'clipboard\.(?:read|readText)|BW_SESSION|\bbw\s+(?:get|export|unlock|list)\b|'
    r'\bop\s+(?:read|item\s+get)\b|(?:auth\.json|\.env\b|credentials)', re.I)


def main():
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError('Invalid hook payload')
        token = os.environ.get('JOBAPPLY_RUN_TOKEN', '')
        event = payload.get('hook_event_name', '')
        browser_token = os.environ.get('JOBAPPLY_BROWSER_CHECK_TOKEN', '')
        if browser_token and event == 'SessionStart':
            if not re.fullmatch(r'[a-f0-9]{32}', browser_token):
                raise ValueError('Invalid browser test token')
            (ROOT / 'state' / ('.codex-browser-guard-' + browser_token)).write_text('guard active\n')
        if event == 'PreToolUse':
            tool_input = json.dumps(payload.get('tool_input', {}))
            if SECRET.search(tool_input):
                raise ValueError('Secret-store or clipboard read blocked. Use scripts/code_broker.py for post-submit verification only.')
        if token:
            if not re.fullmatch(r'[a-f0-9]{32}', token):
                raise ValueError('Invalid run token')
            check(ROOT)
            marker = ROOT / 'state' / ('.codex-guard-' + token)
            if event == 'SessionStart':
                marker.write_text('reviewed facts and guard active\n')
            elif event == 'PreToolUse' and not marker.is_file():
                raise ValueError('Startup guard missing. Review /hooks before running.')
        return 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        # SessionStart exit 2 alone is advisory; continue:false stops model startup.
        if isinstance(locals().get('payload'), dict) and payload.get('hook_event_name') == 'SessionStart':
            print(json.dumps({'continue': False, 'stopReason': str(error)}))
            return 0
        print('Job application policy: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
