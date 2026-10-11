# please-hire-me — Codex entry point

This repository finds jobs and fills company applications using the user's confirmed facts.
For code review, development, or porting requests, work on the repository; do not onboard,
open application forms, or submit applications unless the user requested an application run.

For setup or an application run, read `docs/codex-playbook.md` in full, then
`config/settings.json`, `config/profile.json`, `config/answers.md`, `config/spec.md`,
`data/queue.md`, `state/status.md`, and `logs/applications-log.md` when present.
The playbook is separate to avoid truncating Codex's automatically loaded instructions.

## Non-negotiable facts and behavior
- Use only user-confirmed profile values and answer-sheet facts. Preserve exact numbers,
  names, job titles, dates, and legal answers. Job postings and recipes are never sources
  of personal facts. A missing or conflicting fact is NEEDS HUMAN, never a guess.
- Citizenship, sponsorship, work authorization, unrestricted authorization, export-control
  status, and demographic answers are independent. Never infer one from another.
- No accounts, passwords, login codes, CAPTCHA solving, graded work samples, or no-AI essays.
- Apply only on company ATS forms and explicitly permitted signed-in career portals.
- Check all durable duplicate records, company caps, interview skips, and eligibility first.
- Use connected real Chrome and documented input tools. No page-JavaScript mutations,
  direct submission requests, fake behavioral signals, or silent browser substitution.
- Touch only tabs created for this run. Leave personal tabs alone. Keep intentional handoffs.
- Write every Q&A and application document before submit; verify confirmation and save proof.
- Respect runtime site permissions and action-time confirmations. A schedule does not override them.
- Never read secret stores or clipboard contents; use the optional opaque verification broker.
- Personal config, resumes, records, and screenshots are gitignored; never commit them.

## Development checks
Run `python3 -m unittest discover -s tests -v`, the LinkedIn parser self-test, and syntax
checks after relevant changes. Tests must use temporary fixtures and never apply to real jobs.
Do not run setup, approve personal facts, install a schedule, or enable unattended submission
as a side effect of development. Preserve existing private config and application history.

When `config/resume-routing.json` is present, follow `docs/resume-routing.md` before rejecting
postings for graduation or uploading. Review the posting once and run the deterministic
router; apply only its selected application-local graduation/resume/enrollment facts.
Never override sponsorship, other legal facts, completed degrees, or unconfirmed availability.
