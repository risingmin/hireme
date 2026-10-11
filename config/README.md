# config/

Everything the agent reads before it touches a form. No logs, no data here.

| File | What | Tracked? |
|---|---|---|
| `settings.json` | Run knobs and target criteria. The launcher turns it into the run's instructions. | no (yours) |
| `profile.json` | Every field value an ATS asks for. Used verbatim, never guessed. | no (yours) |
| `answers.md` | Free-text templates, fact sheet, preset legal/EEO answers. The only source for prose. | no (yours) |
| `spec.md` | The run contract: hard rules, per-application procedure, log format. | yes |
| `*.example.*` | Templates `setup.sh` copies from. Edit these when you add a new field. | yes |

Add a fact once here and the agent stops asking you about it forever.

After reviewing your real config and upload documents, run `python3 scripts/preflight.py approve`.
Changed files require a new review. No sponsorship questions, defaults, or filters were changed
by the Codex port. The existing terminal wizard behavior remains; verify its generated answers.

Optional `resume-routing.json`: copy `resume-routing.example.json` after supplying the two
matching PDFs. Review academic terms and dates, then approve all facts again. See
[resume routing](../docs/resume-routing.md). This file is ignored by git and cannot override
sponsorship or other legal facts.

The example defaults to May 2027 for full-time/new-grad roles and December 2027 for
internships. Mandatory graduation windows and confirmed return-semester requirements
take precedence. Keep only academic terms you can truthfully confirm. Setup does not
enable this optional config automatically; the single-resume workflow remains the default.
