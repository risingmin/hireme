# scripts/

| File | What |
|---|---|
| `schedule.sh` | Install, check, or remove the recurring run. Reads `schedule.frequency` from `config/settings.json`. Uses launchd on macOS, cron elsewhere. |
| `scheduled_run.sh` | What the scheduler calls. One bounded run, everything appended to `logs/scheduled-run.log`. |
| `fetch_hn_hiring.sh` | Pull the current HN "Who is hiring?" thread as plain text, one posting per block. Best source of startups that never hit a job board. |
| `probe_boards.sh` | Re-verify every slug in `data/slug-candidates.txt` and rewrite `data/boards.md`. Run before a big sourcing session. |
| `render_boards.py` | Turns probed payloads into `data/boards.md`. Called by `probe_boards.sh`. |
| `resume_server.py` | Legacy localhost helper for resume upload. Only needed if `file_upload` is unavailable. |
| *(your own)* | Set `integrations.post_run_script` in `config/settings.json` to a python3 script and it runs after every run. Nothing ships here by default. |

Codex-specific helpers:
- `preflight.py check`: verify config, documents, hard safety rules, and reviewed-file hashes.
- `preflight.py approve`: record the user's explicit review of exact config and upload documents.
- `browser_check.py`: exercise the CLI browser with a local dummy form; writes capability proof
  to `state/browser-check.json` and screenshot to `state/browser-proof.jpg`.
- `resume_router.py --assessment state/posting-review.json`: select a reviewed graduation
  variant from the existing posting assessment. Returns SELECT, SKIP or NEEDS HUMAN; no
  extra network/model call. See [routing setup and assessment format](../docs/resume-routing.md).

Application policy is in `AGENTS.md`, `docs/codex-playbook.md`, and `docs/browser.md`.
The sourcing and scheduling helpers remain unchanged. Tests: `python3 -m unittest discover -s tests -v`.
