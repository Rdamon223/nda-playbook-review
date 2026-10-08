# nda-playbook-review

A Claude skill that reviews a mutual non-disclosure agreement against a written playbook. For each of 14 playbook topics, it reports whether the NDA is acceptable, needs a fallback, or must go to a lawyer, with a verbatim quote from the NDA for every finding. The repo also measures how accurate and how fast the review is, on 15 synthetic NDAs, and compares it with the same model reviewing without the playbook.

> **Not legal advice.** This is a first-pass review aid. A lawyer must review any NDA before signature, and every generated memo says so.

## Results in brief

From the full report, [REPORT.md](REPORT.md) (15 synthetic NDAs, each reviewed 3 times, `claude-sonnet-5-5` at medium effort):

| | Skill (with playbook) | Same model, no playbook |
|---|---|---|
| Status accuracy | 97.1% | 24.8% |
| Escalation recall (must-escalate topics caught) | 100% (45/45) | 93.3% (14/15) |
| Acceptable clauses wrongly escalated | 1.3% | 28.3% |
| Quotes verbatim from the NDA | 547/547 | 46/96 |
| Time and cost per review | 15 s, about $0.04 | 23 s, about $0.05 |

The sample is small and synthetic, and one person labeled it. Read [REPORT.md](REPORT.md) for the misses and the limits before relying on these numbers.

## Why it exists

Most NDAs are routine, but each one still needs someone to check every clause against the company's positions. A playbook turns those positions into explicit rules. This project tests whether a model can apply the rules consistently, quote exactly what it relied on, and send anything doubtful to a lawyer instead of guessing. It is a portfolio piece that covers legal workflow design (the playbook), AI building (the skill), and evaluation (the report).

## Quick start

Requires Python 3.11 or later.

```
pip install -r requirements.txt
python -m pytest
```

The tests do not call the API.

### Settings

Create a file named `.env` in the repo root. Git ignores it, and the code never prints its values.

```
ANTHROPIC_API_KEY=your key
NDA_REVIEW_MODEL=claude-sonnet-5-5
NDA_REVIEW_EFFORT=medium
```

- `NDA_REVIEW_MODEL` is required and has no default in the code.
- `NDA_REVIEW_EFFORT` is optional. It takes `low`, `medium`, `high`, or `max`; if it is unset, the API default applies.
- Variables already set in your environment take priority over `.env`.
- API use is billed to your Anthropic account.

### Review one NDA

```
python scripts/review.py data/synthetic_ndas/nda_04.docx
python scripts/review.py path/to/nda.pdf --company "Party name as written in the NDA"
```

This writes `outputs/<name>.json` and `outputs/<name>.md`. For the synthetic NDAs, the party being represented is read from the manifest. For any other NDA, `--company` is required, because one-sided terms are judged from that party's side. Keep real documents in `private/`, which git ignores.

You can also run the review inside Claude Code with no API key: ask Claude to review an NDA, and the skill in `.claude/skills/nda-review/` takes over.

### Run the evaluation

```
python scripts/eval.py --estimate   # call count and cost estimate, no API calls
python scripts/eval.py --run        # runs whatever is not cached yet, then scores
python scripts/eval.py --report     # rescores from cached outputs, no API calls
```

`eval.py` refuses to run until `data/gold_labels.json` has `"reviewed": true`.

## How the playbook works

`playbooks/mutual-nda-playbook.md` (Version 1) covers 14 topics, from mutuality and exclusions through residuals, non-solicits, remedies, and assignment. Each topic sets out:

- a **Preferred position**;
- an **Acceptable fallback**, with the exact replacement wording;
- **Escalate if** triggers;
- a **Severity**;
- an **If absent** rule.

General rules include: when in doubt, escalate; read every defined term a clause relies on; and never draft new legal language.

The skill (`.claude/skills/nda-review/SKILL.md`) works through these steps:

1. Confirm which party is the Company.
2. Extract numbered text.
3. Find the clauses for each topic.
4. Compare each clause with the playbook.
5. Assign one status per topic.
6. Quote verbatim.
7. Propose only playbook fallback wording.
8. Escalate when uncertain.
9. Report.

Code, not the model, checks the output:

- **Schema:** `scripts/schema.py` checks the review's structure, for example that a fallback finding includes proposed language and that low confidence comes with an escalation.
- **Quotes:** `scripts/verify_quotes.py` checks that every quote is a verbatim passage in the cited section, and that every proposed fix is the playbook's own wording.
- **Repair:** if a check fails, `review.py` sends the problems back to the model for a corrected answer, up to two times. Only a review that passes all checks becomes a memo.

## Evaluation approach

- **Test set.** There are 15 synthetic mutual NDAs: 3 clean, 9 with 1 to 4 planted deviations (22 in total), and 3 hard cases. The hard cases are a deviation buried in a definition, a defined-term trap that makes a "mutual" NDA one-way, and a clause too ambiguous to classify.
- **Gold labels.** `data/gold_labels.json` gives the expected status for every topic in every NDA. They are single-reviewer labels assigned by one human with transactional legal experience: a non-attorney with more than 2,500 negotiated transactions, most handled with attorney oversight and joint strategy. The first draft was generated from the planted-deviation manifest, then reviewed by the labeler.
- **Skill condition.** The workflow above, run 3 times per NDA to measure consistency.
- **Baseline condition.** The same model and effort with the prompt "Review this NDA and list any problems." It is told which party it acts for and gets no playbook.
- **Baseline mapping.** A separate grading call reads only the baseline's answer and the 14 topic names. For each topic it picks one label: serious, minor, missing, or not flagged. Code then turns these into statuses:

  | Grader label | Status |
  |---|---|
  | serious | escalate |
  | minor | fallback |
  | not flagged | acceptable |
  | missing | the playbook's If absent rule |

  The grader never sees the NDA, the playbook positions, or the gold labels.
- **Measures.**
  - **Status accuracy:** per topic and overall.
  - **Escalation recall:** the measure that matters most.
  - **False escalation rate.**
  - **Quote validity:** checked by code.
  - **Hallucinations.**
  - **Run-to-run consistency.**
  - **Time and cost:** wall-clock time, tokens, and estimated cost from `config/rates.json`.
  - **Human review time:** from `data/manual_timing.csv`.

## Outputs

| Path | What it is |
|---|---|
| [`REPORT.md`](REPORT.md) | Two-page write-up: results, turnaround, every miss, limitations |
| `outputs/results.md`, `outputs/results.json` | Full scores, confusion table, consistency, and the list of misses |
| [`outputs/sample_memo.md`](outputs/sample_memo.md) | One memo, for nda_04 |
| `outputs/memos/` | Run-1 memos for all 15 NDAs |
| `outputs/eval/raw/` | Every model output from the evaluation |

## Layout

| Path | What it does |
|---|---|
| `.claude/skills/nda-review/SKILL.md` | The review workflow Claude follows |
| `.claude/skills/nda-review/playbook.md` | Copy of the playbook (a test keeps it identical to the source) |
| `.claude/skills/nda-review/schema.json` | Review JSON schema, generated by `scripts/schema.py` |
| `scripts/review.py` | Reviews one NDA through the API: extract, model, validate with repair rounds, memo |
| `scripts/eval.py` | Scores the skill and the baseline against the gold labels |
| `scripts/extract_text.py` | Turns a .docx or .pdf into numbered text, one `[3.2] text` line per paragraph |
| `scripts/verify_quotes.py` | Deterministic check of quotes and proposed wording |
| `scripts/schema.py` | Pydantic models for a review; regenerates `schema.json` |
| `scripts/finalize.py` | Validates a review JSON and writes its memo |
| `scripts/memo.py` | Renders the one-page memo, escalations first, with the lawyer-review footer |
| `scripts/playbook.py` | Parses the playbook into topics |
| `scripts/env.py` | Reads settings from the environment or `.env` |
| `scripts/make_synthetic.py` | Builds the synthetic NDAs, manifest, draft gold labels, and timing sheet |
| `config/rates.json` | Token prices for cost estimates |
| `data/` | Synthetic NDAs, `seeded_deviations.json`, `gold_labels.json`, `manual_timing.csv` |

## Limitations

- All NDAs are synthetic, with invented party names, and come from one generator. Real agreements are messier.
- The sample is 15 NDAs and one playbook, and covers mutual NDAs only.
- One person labeled the NDAs and recorded the human review times. The gold labels started from the planted-deviation manifest, so that person knew where the deviations were.
- One model version and effort setting.
- The baseline's mapping to topics depends on a model grader.

No client or employer document is ever placed in this repo, and the API key stays in `.env`. A test fails if `.env` stops being git-ignored, or if anything shaped like a key appears in a tracked file.

This tool is a first-pass aid, not legal advice. A lawyer must review the NDA and the memo before anyone relies on either.

## License

MIT
