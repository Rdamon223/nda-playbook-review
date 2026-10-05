# nda-playbook-review

A Claude skill that reviews a mutual non-disclosure agreement against a written playbook and reports, for each of 14 playbook topics, whether the NDA is acceptable, needs a fallback, or must go to a lawyer. The repo also measures how accurate and how fast the review is, on a set of synthetic NDAs.

> **Not legal advice.** This is a first-pass review aid. A lawyer must review any NDA before signature, and every generated memo says so.

## Status

Work in progress, following `nda-review-skill-spec.md` section 12.

- Step 1: playbook drafted in `playbooks/mutual-nda-playbook.md`, waiting for owner review.
- Next: the skill, schema, extraction and quote-verification scripts, and tests.

## Data

All NDAs in this repo are synthetic, with fictional party names. No client or employer document is ever placed here. `private/` and `outputs/private/` are git-ignored.

Full quick start, evaluation method, and results will be added as the build progresses.
