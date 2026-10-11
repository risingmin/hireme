# Graduation-based resume selection

Optional: without `config/resume-routing.json`, the existing single-resume behavior stays active.
To enable, create your two PDFs, copy `config/resume-routing.example.json` to
`config/resume-routing.json`, and review the dates, paths and enrolled terms. The fall term
is a personal fact: keep it only if you will return for that term under the December plan.
Review both PDFs: they must state their matching graduation dates and preserve all other
confirmed facts. Run `python3 scripts/preflight.py approve` after reviewing these files.
Preflight hashes both PDFs and the routing config; it cannot verify PDF contents itself.

May is the full-time/new-grad default. December is the internship default. Mandatory
requirements take precedence; neither qualifying means SKIP, uncertain means NEEDS HUMAN.
A preferred date is not a mandatory exclusion. All other role eligibility, sponsorship,
start-availability, duplicate checks and submission rules remain in force.

During the existing posting review, save a JSON assessment in `state/` using the posting
text already read. This needs no additional model/API request. Include every mandatory
graduation, enrollment/return-semester and full-time start requirement. Never mark review
complete if relevant wording, job type, dates or a return semester are unclear.

Example assessment:

```json
{
  "posting_text": "Software engineering internship, summer 2027. Must return to school for fall 2027 after the internship.",
  "job_type": "internship",
  "review_complete": true,
  "uncertainties": [],
  "requirements": [
    {
      "type": "return_to_school",
      "strength": "required",
      "term": "2027-fall",
      "evidence": "Must return to school for fall 2027 after the internship."
    }
  ]
}
```

Run `python3 scripts/resume_router.py --assessment state/posting-review.json`.
The script returns SELECT, SKIP or NEEDS HUMAN (non-selection exits with code 2).
It validates evidence quotes against the posting; extraction is still the reviewing agent's
responsibility. It does not fetch postings or claim to understand arbitrary prose by itself.

Supported requirements:

- `graduation_window`: inclusive `earliest` and/or `latest` in YYYY-MM. For "before August
  2027", latest is `2027-07`; for "by August 2027", latest is `2027-08`.
- `return_to_school`: `term` such as `2027-fall`, which must appear in the selected variant's
  confirmed `enrolled_terms`. "At least a semester left" requires identifying the actual
  post-internship academic term; missing internship dates/return term means NEEDS HUMAN.
- `full_time_start`: `month` in YYYY-MM; completion must precede this month. Same-month
  graduation/start requires exact-date review. This check does not establish work availability.

Every requirement needs `strength` (`required` or `preferred`) and an exact `evidence`
quote. Date-day limits, contradictory requirements, unusual academic calendars, already-
graduated requirements, unclear ranges and unsupported constraints require human review;
do not omit them to get a selection. Empty requirements are valid only after a complete
review finds no relevant gates.

Use the SELECT result as an application-local overlay: selected `resume`, `graduation`
and `college_end_date`, plus confirmed enrollment facts. Do not rewrite shared profile,
answers or settings. Review any date-bearing education text, auto-parsed fields and free
text against the selected date. Never infer completed degrees or legal/work-authorization
answers from the selection. If a canonical answer conflicts and cannot be changed solely
by replacing the confirmed graduation date, stop for human review. Availability answers
still need confirmed presets and must fit the selected graduation plan.

Before submission record the variant ID, PDF path, graduation date, reason and evidence
in both the per-application document and application log. Verify all graduation/enrollment
fields and the uploaded PDF agree. Selection is not permission to submit an otherwise
ineligible application.
