---
name: nda-review
description: Review a mutual NDA (.docx or .pdf) against the written playbook in this folder and produce a structured JSON review plus a one-page memo. Use when asked to review, check, or mark up an NDA or confidentiality agreement against the playbook. First-pass aid only, not legal advice.
---

# NDA review against the playbook

You are doing a first-pass review of one NDA against `playbook.md` in this folder (a copy of
`playbooks/mutual-nda-playbook.md`). The output is not legal advice. A lawyer reviews everything.

Read `playbook.md` in full before you start, including the general rules and the status table.

## Workflow (follow every step, in order)

0. **Know who you act for.** The playbook speaks for "the Company". Confirm which party in the NDA is
   the Company before you start. If the user has not said, ask. Record it in `company`. One-sided
   terms are judged by whether they burden the Company.

1. **Extract.** Run `python scripts/extract_text.py <file>` to get numbered text. Each line is
   `[ref] text`, where ref is the section the paragraph belongs to. Work from this text only.

2. **Segment.** For each of the 14 playbook topics, find every clause that bears on it. Look
   everywhere: definitions, miscellaneous, exhibits. A topic can be spread across sections. If no
   clause covers a topic, the clause is missing: set `clause_found` to false and apply that topic's
   **If absent** rule (`absent` for topics 9 to 14, `escalate` for topics 1 to 8).

3. **Compare.** Compare each clause with the topic's Preferred position, Acceptable fallback, and
   Escalate triggers. Read every defined term the clause relies on before deciding; a clause can
   read well until a definition changes it.

4. **Classify.** Assign exactly one status per topic: `acceptable`, `fallback`, `escalate`, or
   `absent`. If any Escalate trigger applies, the status is `escalate`, even if other parts are fine.

5. **Quote.** For every clause that is present, copy a verbatim quote from the extracted text
   (one contiguous passage, no ellipses, no edits, no paraphrase) and give its `section_ref`
   exactly as the extractor printed it (for example `3`, `3.2`, or `4(b)`). Quote the words that
   drive the status. If the deciding words are in a definition, quote the definition and cite it.

6. **Propose.** For `fallback` findings only, set `proposed_language` to the topic's Acceptable
   fallback wording, copied exactly from the blockquote in the playbook (you may copy one complete
   list item or sentence from it if only that part is needed). Never write new legal language. If
   the written fallback does not fix the problem, the status is `escalate`.

7. **Be honest about uncertainty.** If confidence is low or the clause is ambiguous, the status is
   `escalate` and the rationale says why. `low` confidence with any other status is invalid. When in
   doubt, escalate.

8. **Report.** Write the review JSON to `outputs/<nda file stem>.json` matching `schema.json`, then
   run `python scripts/finalize.py outputs/<stem>.json`. It validates the schema, checks every quote
   against the NDA and every proposed language entry against the playbook, and writes the memo
   (`outputs/<stem>.md`): summary table, escalations first, and a footer saying a lawyer must
   review. If it reports problems, fix the JSON (re-copy the quote from the extracted text, correct
   the section ref, or escalate) and rerun until it passes. Never edit the memo by hand.

## Review JSON

```json
{
  "source_file": "data/synthetic_ndas/nda_01.docx",
  "company": "Fernhollow Analytics LLC",
  "playbook_version": "Version 1",
  "model": "claude-code",
  "findings": [
    {
      "topic_id": 1,
      "topic_name": "Mutuality",
      "status": "acceptable",
      "clause_found": true,
      "quote": "verbatim text from the NDA",
      "section_ref": "2",
      "rationale": "One or two sentences tying the clause to the playbook position or trigger.",
      "proposed_language": "",
      "confidence": "high"
    }
  ]
}
```

Rules the validator enforces:

- Exactly 14 findings, topic ids 1 to 14, `topic_name` exactly as the playbook heading.
- `clause_found: true` requires a non-empty `quote` and `section_ref`.
- `clause_found: false` requires an empty `quote` and `section_ref`, and status `absent` or
  `escalate` as the topic's If absent rule says.
- `fallback` requires `proposed_language`; every other status requires it to be empty.
- `low` confidence requires `escalate`.

## Do not

- Do not use outside positions or "market" views that are not in the playbook.
- Do not fix or summarize text inside the `quote` field.
- Do not mark a topic `absent` because you could not find a clause quickly. Search the whole text.
- Do not put client or employer documents in this repository.
