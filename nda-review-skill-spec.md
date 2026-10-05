# Build Spec: NDA Playbook Review Skill (for Claude Code)

Hand this whole file to Claude Code as the task. Work in a new empty repo named `nda-playbook-review`.

## 1. Goal

Build a Claude skill that reviews a non-disclosure agreement against a written playbook and returns, for each playbook topic, whether the NDA is acceptable, needs a fallback, or must be escalated to a lawyer. Then measure how accurate it is and how long it takes, and publish a short, honest write-up of the results.

The repo is a portfolio piece for a Legal Engineer application. It should show three things: legal workflow design (the playbook), AI building (the skill), and evaluation discipline (the accuracy and turnaround report).

## 2. Ground rules

- **No real client or employer documents anywhere in the repo.** All NDAs in the test set are synthetic. Add a `.gitignore` entry for `private/` and `outputs/private/`.
- The skill is a first-pass review aid. It is not legal advice. Say so in the README and in every generated memo footer.
- Never hardcode API keys. Read `ANTHROPIC_API_KEY` from the environment. Make the model name configurable through an environment variable `NDA_REVIEW_MODEL` with no default baked into the code logic (document the setting in the README).
- Do not use em-dashes in any file in this repo. Use commas, colons, or hyphens.
- Write plain, readable prose in all documentation. Avoid marketing language.
- Python 3.11+. Keep dependencies small: `python-docx`, `pdfplumber`, `anthropic`, `pytest`, `pydantic`.

## 3. Repo layout

```
nda-playbook-review/
  README.md
  LICENSE                      (MIT)
  .gitignore
  .claude/skills/nda-review/
    SKILL.md
    playbook.md                (symlink or copy of playbooks/mutual-nda-playbook.md)
    schema.json
  playbooks/
    mutual-nda-playbook.md
  scripts/
    extract_text.py            (docx and pdf to clean text with section numbering)
    review.py                  (runs the review, writes JSON and markdown memo)
    verify_quotes.py           (checks every quote is a verbatim substring of the source)
    eval.py                    (runs the evaluation and writes results)
  data/
    synthetic_ndas/            (15 NDAs, .docx)
    seeded_deviations.json     (what was planted in each NDA)
    gold_labels.json           (expected status per topic per NDA)
    manual_timing.csv          (human review times, filled in by the repo owner)
  outputs/                     (generated memos and results, committed for the sample runs only)
  REPORT.md                    (the short accuracy and turnaround write-up)
  tests/
    test_verify_quotes.py
    test_schema.py
```

## 4. The playbook (`playbooks/mutual-nda-playbook.md`)

Draft a generic, mutual NDA playbook for a commercial services relationship. The repo owner will review and edit it, so mark it clearly as a draft at the top.

Cover these 14 topics. For each, write: **Preferred position**, **Acceptable fallback** (with exact fallback wording), **Escalate if** (specific triggers), and **Severity** (high, medium, low).

1. Mutuality (obligations apply to both parties)
2. Definition of Confidential Information (marking requirements, oral disclosures)
3. Standard exclusions (public domain, prior knowledge, independent development, third-party receipt)
4. Term of the agreement and survival of confidentiality obligations
5. Permitted use (purpose limitation)
6. Permitted disclosure to representatives (need-to-know, advisors, affiliates)
7. Compelled disclosure (notice and cooperation)
8. Return or destruction of materials (including backup copies and retention for legal compliance)
9. Residuals clause
10. Non-solicitation or non-compete language buried in an NDA
11. Remedies and injunctive relief (and one-sided fee shifting)
12. Governing law and venue
13. Assignment and change of control
14. No license, no warranty, no obligation to proceed

Use realistic, mainstream positions. Do not copy any firm's or vendor's proprietary playbook language.

## 5. The skill (`.claude/skills/nda-review/SKILL.md`)

Write a SKILL.md with YAML frontmatter (`name`, `description`) where the description says when to use it: reviewing an NDA against the written playbook.

The skill instructions must require this workflow:

1. **Extract.** Run `scripts/extract_text.py` on the input file to get numbered text.
2. **Segment.** Identify the clauses that correspond to each of the 14 playbook topics. If a topic has no matching clause, record it as `absent`.
3. **Compare.** For each topic, compare the clause to the Preferred position, Acceptable fallback, and Escalate triggers in the playbook.
4. **Classify.** Assign exactly one status per topic: `acceptable`, `fallback`, `escalate`, or `absent`.
5. **Quote.** Every finding for a present clause must include a verbatim quote from the NDA and its section reference. Never paraphrase inside the quote field.
6. **Propose.** For `fallback` findings, propose replacement language taken from the playbook's fallback wording only. Do not invent new legal language.
7. **Be honest about uncertainty.** If confidence is low, or the clause is ambiguous, set the status to `escalate` and explain why. When in doubt, escalate.
8. **Report.** Write structured JSON that matches `schema.json`, then a one-page markdown memo with a summary table, the escalations first, and a footer stating that a lawyer must review the output.

Finding schema (put in `schema.json` and validate with pydantic):

```json
{
  "topic_id": 1,
  "topic_name": "Mutuality",
  "status": "acceptable | fallback | escalate | absent",
  "quote": "verbatim text from the NDA, empty only when status is absent",
  "section_ref": "e.g. 3.2",
  "rationale": "one or two sentences",
  "proposed_language": "playbook fallback wording, empty unless status is fallback",
  "confidence": "high | medium | low"
}
```

## 6. Synthetic test set

Generate 15 synthetic mutual and one-way NDAs as `.docx` files, each 2 to 5 pages, with realistic structure and varied drafting styles. Fictional party names only.

- 3 NDAs are clean (all topics acceptable).
- 9 NDAs each contain 1 to 4 planted deviations from the playbook.
- 3 NDAs are "hard cases": a deviation buried in a definitions section, a defined-term trap where a clause reads fine until you check a definition, and a clause that is ambiguous enough that escalation is the right answer.

Record every planted deviation in `data/seeded_deviations.json` (file name, topic, what was planted, where).

Then generate a first draft of `data/gold_labels.json` (expected status for each of the 14 topics in each NDA) from the manifest. **Mark the file as unreviewed.** The repo owner will read the NDAs and correct the gold labels by hand. The README must state that gold labels are single-reviewer and were assigned by a human with transactional legal experience. Do not run the final evaluation until the owner sets `"reviewed": true` in the gold file. Make `eval.py` refuse to run otherwise.

## 7. Evaluation harness (`scripts/eval.py`)

Run each NDA through two conditions:

- **Baseline:** a plain prompt ("review this NDA and list any problems") with no playbook.
- **Skill:** the full skill workflow with the playbook.

Because the baseline does not return playbook topics, map its output to topics with a second, separate grading call, and document how that mapping works.

Compute and write to `outputs/results.json` and `outputs/results.md`:

**Accuracy**
- Status accuracy per topic and overall (skill vs gold)
- **Escalation recall:** of all topics the gold says must escalate, how many did the skill escalate? This is the most important number. A missed escalation is the worst failure.
- **False escalation rate:** topics escalated that the gold says were acceptable
- **Quote validity rate:** share of quotes that are verbatim substrings of the source (checked by `verify_quotes.py`, not by the model)
- **Hallucination count:** quotes or proposed language not traceable to the NDA or the playbook
- Baseline vs skill comparison on the same measures where applicable

**Turnaround**
- Wall-clock seconds per NDA (extract through memo)
- Input and output tokens per NDA, and an estimated cost using a rate table in a config file
- Human comparison: `data/manual_timing.csv` has columns `file, minutes_manual_review, minutes_review_of_ai_output`. The repo owner fills it in for at least 5 NDAs by timing themselves reviewing the NDA from scratch, then reviewing the skill's memo and correcting it. Report both numbers honestly, including cases where the AI-assisted path was not faster.

Run each NDA 3 times in the skill condition and report how often the status for a topic changed between runs (consistency).

## 8. The write-up (`REPORT.md`)

Maximum two pages. Use these headings, with real numbers filled in from `outputs/results.md`:

1. What was tested (setup in five sentences)
2. Results table (accuracy, escalation recall, false escalations, quote validity)
3. Turnaround (machine time, human time with and without the tool)
4. Where it failed (list each miss with a one-line cause)
5. What still needs a lawyer
6. Limitations: synthetic documents, 15 NDAs, one human labeler, one playbook, one model version
7. What I would change next

Do not overstate results. If escalation recall is below 100 percent, say so plainly and discuss why.

## 9. Tests

- `test_verify_quotes.py`: a verbatim quote passes, a paraphrase fails, whitespace-only differences are handled consistently.
- `test_schema.py`: valid findings pass, a `fallback` finding without proposed language fails, a non-absent finding without a quote fails.

## 10. README

Sections: what it is, why it exists, quick start (install, set env vars, run one review, run the eval), how the playbook works, the evaluation approach, limitations and the not-legal-advice notice. Include one sample memo in `outputs/sample_memo.md` generated from a synthetic NDA.

## 11. Acceptance criteria

- `python scripts/review.py data/synthetic_ndas/<file>.docx` produces a valid JSON file and a one-page memo.
- All tests pass.
- Every quote in every committed output verifies as a verbatim substring.
- `eval.py` refuses to run until gold labels are marked reviewed.
- `REPORT.md` is filled in from real results, not placeholders.
- A search of the repo finds no em-dashes and no real party names.

## 12. Order of work

1. Playbook draft, then stop and let the owner review it.
2. Skill, schema, extraction and verification scripts, tests.
3. Synthetic NDAs, seeded manifest, draft gold labels, then stop for the owner to review gold labels and fill in manual timing.
4. Evaluation harness and run.
5. REPORT.md and README.
