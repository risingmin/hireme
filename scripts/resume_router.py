#!/usr/bin/env python3
"""Route approved resumes using requirements extracted during the existing posting review.

No network/model calls. Run with --assessment posting-review.json. See docs/resume-routing.md.
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = 'config/resume-routing.json'


def month(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', value):
        raise ValueError('Dates must be YYYY-MM; exact-day boundaries require human review.')
    return value


def validate(config):
    # A narrow allowlist prevents a resume choice from changing legal or identity facts.
    if not isinstance(config, dict) or config.get('version') != 1:
        raise ValueError('Invalid resume-routing version.')
    variants = config.get('variants')
    if not isinstance(variants, list) or len(variants) < 2:
        raise ValueError('Configure at least two confirmed resume variants.')
    ids = set()
    allowed = {'id', 'resume', 'graduation_month', 'graduation', 'college_end_date', 'enrolled_terms'}
    for v in variants:
        if not isinstance(v, dict) or set(v) - allowed:
            raise ValueError('Variants may override only resume and graduation/enrollment facts.')
        for key in ('id', 'resume', 'graduation', 'college_end_date'):
            if not isinstance(v.get(key), str) or not v[key].strip():
                raise ValueError('Missing variant field: ' + key)
        month(v.get('graduation_month'))
        if v['id'] in ids:
            raise ValueError('Duplicate resume variant id.')
        ids.add(v['id'])
        if not isinstance(v.get('enrolled_terms'), list) or any(
                not isinstance(t, str) or not re.fullmatch(r'\d{4}-(spring|summer|fall|winter)', t)
                for t in v['enrolled_terms']):
            raise ValueError('enrolled_terms must contain confirmed academic terms.')
    defaults = config.get('defaults', {})
    if set(defaults) != {'full_time', 'internship'} or any(v not in ids for v in defaults.values()):
        raise ValueError('Specify full_time and internship defaults using variant ids.')
    return variants


def route(config, assessment):
    variants = validate(config)
    def result(status, reason, **extra):
        return dict(status=status, reason=reason, **extra)
    if not isinstance(assessment, dict):
        return result('NEEDS HUMAN', 'Posting assessment must be an object.')
    if assessment.get('review_complete') is not True or assessment.get('uncertainties') != []:
        return result('NEEDS HUMAN', 'Posting requirements are incomplete or uncertain.')
    kind = assessment.get('job_type')
    if kind not in ('full_time', 'internship'):
        return result('NEEDS HUMAN', 'Confirm whether this is full-time or an internship.')
    posting = assessment.get('posting_text')
    requirements = assessment.get('requirements')
    if not isinstance(posting, str) or not posting.strip() or not isinstance(requirements, list):
        return result('NEEDS HUMAN', 'Provide posting text and reviewed requirements.')
    normalized = ' '.join(posting.split()).casefold()
    eligible = list(variants)
    evidence = []
    for req in requirements:
        if not isinstance(req, dict):
            return result('NEEDS HUMAN', 'Invalid requirement.')
        quote = req.get('evidence')
        if not isinstance(quote, str) or not quote.strip() or ' '.join(quote.split()).casefold() not in normalized:
            return result('NEEDS HUMAN', 'Requirement evidence must quote the posting.')
        if req.get('strength') not in ('required', 'preferred'):
            return result('NEEDS HUMAN', 'Distinguish mandatory requirements from preferences.')
        # Preferences do not make an otherwise qualified graduation plan ineligible.
        if req['strength'] == 'preferred':
            continue
        rule = req.get('type')
        try:
            if rule == 'graduation_window':
                low, high = req.get('earliest'), req.get('latest')
                if low is None and high is None:
                    raise ValueError('Graduation window needs a boundary.')
                if low is not None: month(low)
                if high is not None: month(high)
                if low and high and low > high: raise ValueError('Reversed graduation window.')
                eligible = [v for v in eligible if (low is None or v['graduation_month'] >= low)
                            and (high is None or v['graduation_month'] <= high)]
            elif rule == 'return_to_school':
                term = req.get('term')
                if not isinstance(term, str) or not re.fullmatch(r'\d{4}-(spring|summer|fall|winter)', term):
                    raise ValueError('Return-to-school requirement needs the confirmed return term.')
                eligible = [v for v in eligible if term in v['enrolled_terms']]
            elif rule == 'full_time_start':
                if kind != 'full_time': raise ValueError('Full-time start rule on an internship.')
                start = month(req.get('month'))
                # Same-month completion/start ordering cannot be inferred.
                if any(v['graduation_month'] == start for v in eligible):
                    return result('NEEDS HUMAN', 'Graduation and full-time start share a month; confirm exact dates.')
                eligible = [v for v in eligible if v['graduation_month'] < start]
            else:
                raise ValueError('Unsupported or ambiguous requirement.')
        except (ValueError, TypeError) as error:
            return result('NEEDS HUMAN', str(error))
        evidence.append(quote)
    if not eligible:
        return result('SKIP', 'Neither confirmed graduation option meets all mandatory requirements.', evidence=evidence)
    default = config['defaults'][kind]
    # Apply the default only after intersecting every mandatory requirement.
    chosen = next((v for v in eligible if v['id'] == default), eligible[0])
    return result('SELECT', 'Meets all reviewed requirements; uses the role-type default when both qualify.',
                  variant=chosen, evidence=evidence,
                  reminder='Apply all selected graduation facts consistently; other eligibility and sponsorship rules still apply.')


def main():
    # The caller saves its existing posting review; this helper performs no extra inference.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assessment', required=True, type=Path)
    parser.add_argument('--config', type=Path, default=ROOT / CONFIG)
    args = parser.parse_args()
    try:
        decision = route(json.loads(args.config.read_text()), json.loads(args.assessment.read_text()))
    except (OSError, ValueError, TypeError, KeyError) as error:
        decision = {'status': 'NEEDS HUMAN', 'reason': str(error)}
    print(json.dumps(decision, indent=2))
    return 0 if decision['status'] == 'SELECT' else 2


if __name__ == '__main__':
    raise SystemExit(main())
