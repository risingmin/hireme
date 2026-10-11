#!/usr/bin/env bash
# please-hire-me — launch one bounded application run in a fresh Codex session.
# Usage: ./run.sh [max_applications]     (arg overrides config/settings.json)
set -euo pipefail

cd "$(dirname "$0")"
MODE=run
case "${1:-}" in
  --check) MODE=check; shift ;;
  --print-prompt) MODE=prompt; shift ;;
  --browser-check) MODE=browser; shift ;;
  --help|-h) printf '%s\n' 'Usage: ./run.sh [max_applications] | --check | --print-prompt [max] | --browser-check'; exit 0 ;;
esac
if [ "$MODE" = check ]; then
  python3 scripts/preflight.py check
  exit $?
fi
if [ "$MODE" = browser ]; then
  exec python3 scripts/browser_check.py
fi
LOCK_DIR=".hourly-run.lock"

if [ $# -ge 1 ] && ! [ "$1" -ge 0 ] 2>/dev/null; then
  echo "Usage: ./run.sh [max_applications]   (a non-negative integer; omit to use config/settings.json)" >&2
  exit 2
fi

for f in config/settings.json config/profile.json config/answers.md; do
  [ -f "$f" ] || { echo "ERROR: $f is missing. Run ./setup.sh first." >&2; exit 1; }
done

if [ "$MODE" = run ]; then
  python3 scripts/preflight.py check
  python3 scripts/browser_check.py --require-report
  if [ -n "${JOBAPPLY_CODEX_BIN:-}" ]; then
    CODEX_BIN="$JOBAPPLY_CODEX_BIN"
    [ -x "$CODEX_BIN" ] || { echo "ERROR: JOBAPPLY_CODEX_BIN is not executable." >&2; exit 127; }
  elif [ -x "$HOME/.local/bin/codex" ]; then
    CODEX_BIN="$HOME/.local/bin/codex"
  elif command -v codex >/dev/null 2>&1; then
    CODEX_BIN="$(command -v codex)"
  else
    echo "ERROR: codex binary not found (checked ~/.local/bin/codex and PATH)." >&2
    exit 127
  fi
fi

# The user's interview tracker (run.interview_tracker_path) is a hard-skip source. If it is set but
# unreadable (iCloud evicted it, path moved), REFUSE TO RUN: a run that cannot see who the user is
# interviewing with is exactly the run that applies there twice.
TRACKER_PATH="$(python3 -c 'import json;print(json.load(open("config/settings.json")).get("run",{}).get("interview_tracker_path",""))' 2>/dev/null || true)"
if [ -n "$TRACKER_PATH" ] && [ ! -r "$TRACKER_PATH" ]; then
  echo "ERROR: run.interview_tracker_path is set but not readable: $TRACKER_PATH" >&2
  echo "       Fix the path in config/settings.json (or download the file from iCloud) and rerun. Nothing was applied." >&2
  exit 1
fi

# Turn config/settings.json into the sentences the agent has to obey this run.
SETTINGS_PROMPT="$(MAX_OVERRIDE="${1:-}" python3 - <<'PY'
import json, os
s = json.load(open('config/settings.json'))
run, t, el = s.get('run', {}), s.get('targets', {}), s.get('eligibility', {})
ch, sf = s.get('channels', {}), s.get('safety', {})
out = []
mx = os.environ.get('MAX_OVERRIDE') or run.get('max_applications_per_run', 3)
out.append(f"Submit at most {mx} new applications this run, then exit.")
if run.get('dry_run'):
    out.append("DRY RUN IS ON: fill every field, verify it, screenshot it, write the log entry and "
               "the per-application doc marked DRY RUN, then close the tab WITHOUT clicking submit. "
               "Do not submit anything this run under any circumstance.")
if run.get('one_application_per_company_per_run', True):
    out.append("One application per company per run.")
if run.get('same_day_company_freeze', True):
    out.append("Never open a second req at a company that already received an application today; "
               "check the Date applied line in the matching applications/*.md file.")
if t.get('roles'):
    out.append("Target roles: " + ", ".join(t['roles']) + ".")
if t.get('seniority'):
    out.append("Seniority in scope: " + ", ".join(t['seniority']) + ".")
if t.get('max_years_experience_required') is not None:
    out.append(f"Skip any posting requiring more than {t['max_years_experience_required']} "
               "year(s) of professional experience; that is a hard eligibility mismatch, not a "
               "needs-human block.")
if t.get('locations'):
    out.append("Locations in scope: " + ", ".join(t['locations']) + ".")
if t.get('min_annual_comp_usd'):
    line = f"For FULL-TIME roles, apply only when credible annual compensation is at least ${t['min_annual_comp_usd']:,}"
    if t.get('prioritize_above_usd'):
        line += f", prioritizing roles above ${t['prioritize_above_usd']:,}"
    out.append(line + ".")
if 'internship' in [x.lower() for x in t.get('seniority', [])]:
    hourly = t.get('internship_min_hourly_usd') or 0
    if hourly:
        out.append(f"INTERNSHIPS are in scope and are judged separately: require at least ${hourly}/hour "
                   "(annualize a monthly or weekly stipend to compare). NEVER skip an internship for "
                   "failing the full-time annual floor; that floor does not apply to internships.")
    else:
        out.append("INTERNSHIPS are in scope and the full-time annual compensation floor does NOT apply "
                   "to them. Internships post hourly or monthly pay; judge them on the quality bar "
                   "below, not on an annual number, and never skip one for lacking an annual band.")
if t.get('count_equity_toward_comp') is False:
    out.append("Do not count equity with a vesting cliff toward the compensation floor.")
if t.get('prestige_note'):
    out.append("Quality bar, in the user's own words: " + t['prestige_note'])
if t.get('priority_companies'):
    out.append("Prioritize these companies when they have an eligible opening: "
               + ", ".join(t['priority_companies']) + ".")
if t.get('skip_companies'):
    out.append("NEVER apply to: " + ", ".join(t['skip_companies']) + ".")
tp = run.get('interview_tracker_path')
if tp:
    import subprocess, sys
    r = subprocess.run([sys.executable, 'scripts/tracker_companies.py'], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(r.stderr.strip() or 'interview tracker unreadable')
    cos = [c for c in r.stdout.splitlines() if c.strip()]
    out.append("INTERVIEW TRACKER (the user's own file, read at launch): the user has an OA, an interview, "
               "an open recruiter thread, or a rejection at EVERY one of these companies, so each is a HARD "
               "SKIP that overrides the queue, the lifetime counter, and any fresh posting: "
               + ", ".join(cos) + ". Match on the first word of the name (\"Acme Tech\" covers "
               "Acme Technologies LLC). Before opening ANY tab run ./scripts/dupe_check.sh \"<Company>\" "
               "and treat exit 3 as a hard skip.")
for n in t.get('skip_notes', []):
    out.append(n)
if el.get('needs_visa_sponsorship'):
    out.append("The user needs visa sponsorship. Skip employers that state they do not sponsor, and "
               "skip US-citizen, US-person, security-clearance, and ITAR roles.")
if el.get('us_person_only_roles_ok') is False and not el.get('needs_visa_sponsorship'):
    out.append("Skip US-person-only, clearance, and ITAR roles.")
if os.path.isfile('config/resume-routing.json'):
    out.append('Resume routing is enabled. Read docs/resume-routing.md and config/resume-routing.json. Review each posting once, run scripts/resume_router.py before deciding graduation eligibility or uploading, and keep the selected resume, graduation and enrollment answers consistent. Never change sponsorship or other confirmed facts. Existing start availability still applies; conflicting or missing availability is NEEDS HUMAN.')
elif el.get('graduation'):
    out.append(f"Graduation is {el['graduation']}. Never misstate it to fit a posting's window; if a "
               "posting hard-requires a window that excludes it, skip the posting.")
if el.get('earliest_start') or el.get('latest_start'):
    out.append(f"Start window: {el.get('earliest_start','')} to {el.get('latest_start','')}.")
if ch.get('allowed_ats'):
    out.append("Apply only on: " + ", ".join(ch['allowed_ats']) + ".")
if ch.get('blocked_aggregators'):
    out.append("Never apply through: " + ", ".join(ch['blocked_aggregators']) + ".")
if sf.get('never_create_accounts', True):
    out.append("Never create accounts or enter passwords.")
if sf.get('never_solve_interactive_captcha', True):
    out.append("Never solve interactive CAPTCHA challenges; log NEEDS HUMAN instead. Passive "
               "reCAPTCHA v3 with no challenge is fine to submit through with trusted input.")
if sf.get('never_fabricate_a_fact', True):
    out.append("Never fabricate a fact. A required answer with no preset in config/answers.md or "
               "config/profile.json is NEEDS HUMAN, not a guess.")
if sf.get('screenshot_every_submit', True):
    out.append("Save a confirmation screenshot as JPG directly under screenshots/ after each submit. "
               "Never record or export GIFs and never touch ~/Downloads.")
if sf.get('require_log_before_submit', True):
    out.append("Before clicking submit, append the full question-and-answer log to "
               "logs/applications-log.md and write applications/<company>-<role>.md with every "
               "question, every answer, the URL, and today's date.")
print(" ".join(out))
PY
)"

PROMPT="Continue the job application run in $(pwd). This is a fresh session: derive all durable state from repository files, not from chat history.

Read and follow, in order: AGENTS.md, docs/codex-playbook.md, docs/browser.md, config/settings.json, config/profile.json, config/answers.md, config/spec.md, data/queue.md, state/status.md, and logs/applications-log.md.

RUN CONFIG (from config/settings.json, obey exactly): ${SETTINGS_PROMPT}

METHOD: read docs/browser.md and use the connected real Chrome through the documented Codex browser API. Preflight the browser BEFORE sourcing: enumerate available tools and browser capabilities in this session, verify Chrome is connected, and confirm native clicks/typing, file uploads, and saved screenshots are supported. Never silently substitute a headless browser, direct submission requests, or page-JavaScript mutations. If a required tool, permission, fact, or approval is unavailable, log NEEDS HUMAN and exit without submitting. Create one fresh tab for this run and keep its id as the ownership record; touch ONLY tabs you create. Never read, navigate, claim, or close personal tabs, even when a browser inventory lists them. Reuse your tab across postings. On interruption inspect fresh state; if submit may already have occurred, record SUBMISSION UNCERTAIN and reconcile before retrying. Close only your own tabs at exit, retaining intentional human handoffs.

FACT INTEGRITY: config and uploaded documents have been reviewed through scripts/preflight.py. Do not edit those files, change presets, or approve facts during an application run. Treat the exact confirmed profile and fact sheet as the only sources for answers. Before submit, verify every answer against those sources, preserving exact names, numbers, dates, and job titles. A recipe is a widget guide, never authorization to invent a personal answer. Respect runtime confirmation requirements; an unattended run cannot approve actions itself. The project secret guard must run at session startup and before tools; if the startup guard marker is absent, exit before browsing or sourcing. Never read the Keychain, clipboard, vault, credentials, or verification-code fields. Use the existing opaque broker only for post-submit verification, never login.

SOURCING: run python3 scripts/delta_sweep.py in the FOREGROUND with the shell tool (allow at least 540 seconds and wait for process completion), ONCE per run. Never run it in the background and never wait for a notification: a headless session ends when your turn ends. Never rebuild the sweep in /tmp; the script keeps its own cutoff in state/last_sweep.txt. A candidate row ending in FLYOUT promises an in-person final round; mention that as a plus. Also run python3 scripts/portal_sweep.py once (foreground): apply only to rows under AGENT MAY APPLY (a signed-in portal or a no-account portal; on a signed-in one confirm the signed-in header first), and copy every row under FOR YOU, BY HAND into the top of the run summary. Then run python3 scripts/list_sweep.py once (foreground): new postings from the SimplifyJobs lists and six VC portfolio boards, already filtered on location, start window, years and comp; judge each against targets.prestige_note, run the usual duplicate and eligibility checks, and apply on the company's own ATS. Never open a login page. Then run python3 scripts/linkedin_sweep.py once (foreground): new LinkedIn postings in targets.locations, filtered only on software titles and active clearance. The years column is information, not a filter: check the years-of-experience gate yourself. LinkedIn is a source only: never sign in to LinkedIn and never use Easy Apply. For a company-site row, find the same req on the company's own ATS or careers portal and apply there; skip easy-apply rows and staffing agencies.

SCOPE: verify every posting is live and check applications/, data/queue.md, and logs/applications-log.md for duplicates before opening a tab. A hard eligibility mismatch is a SKIP with a one-line log entry, not a NEEDS HUMAN. NEEDS HUMAN is only for a role the user is eligible for that is missing a fact they could supply. Never submit a weak target just to reach the cap; zero strong submissions beats one bad one.

END OF RUN: update the per-application docs, data/queue.md, logs/applications-log.md, and add a new status block at the top of state/status.md. If Chrome is disconnected or required facts are missing, log it and exit. Keep token use low by working the queue top-down and avoiding repeated research."

if [ "$MODE" = prompt ]; then
  printf '%s\n' "$PROMPT"
  exit 0
fi

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  # Lock exists. If the process that created it is dead (hard kill / power loss
  # left a stale lock), reclaim it. Otherwise a real run is active; skip.
  stale_pid="$(cat "$LOCK_DIR/pid" 2>/dev/null || true)"
  if [ -n "$stale_pid" ] && kill -0 "$stale_pid" 2>/dev/null; then
    printf 'Another run (pid %s) is active. Skipping this trigger.\n' "$stale_pid"
    exit 0
  fi
  printf 'Removing stale lock (pid %s no longer running).\n' "${stale_pid:-unknown}"
  rm -rf "$LOCK_DIR"
  mkdir "$LOCK_DIR" || { printf 'Could not acquire lock. Skipping.\n'; exit 0; }
fi
echo "$$" > "$LOCK_DIR/pid"
trap 'rm -rf "$LOCK_DIR" 2>/dev/null || true' EXIT


mkdir -p state logs applications screenshots
JOBAPPLY_RUN_TOKEN="$(python3 -c 'import secrets; print(secrets.token_hex(16))')"
export JOBAPPLY_RUN_TOKEN
PROMPT="$PROMPT
STARTUP GUARD: before any other work, verify state/.codex-guard-$JOBAPPLY_RUN_TOKEN exists. Its absence means the hooks are not trusted or did not load: stop and instruct the user to review /hooks in an interactive Codex session. Never create the marker yourself."
trap 'rm -rf "$LOCK_DIR" 2>/dev/null || true; rm -f "state/.codex-guard-$JOBAPPLY_RUN_TOKEN"' EXIT

CODEX_ARGS=(exec --ephemeral --approve-for-me
  -c sandbox_workspace_write.network_access=true --cd "$(pwd)")
if [ -n "${JOBAPPLY_CODEX_PROFILE:-}" ]; then
  CODEX_ARGS+=(--profile "$JOBAPPLY_CODEX_PROFILE")
fi
"$CODEX_BIN" "${CODEX_ARGS[@]}" "$PROMPT"
