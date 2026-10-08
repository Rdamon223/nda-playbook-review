# NDA playbook review: accuracy and turnaround

Run on 2026-10-08. Full numbers in `outputs/results.md`; every model output is in `outputs/eval/raw/`.

## 1. What was tested

The skill reviewed 15 synthetic mutual NDAs (3 to 4 pages, three drafting styles) against a 14-topic playbook and gave each topic one status: acceptable, fallback, escalate, or absent. Each NDA was reviewed 3 times with `claude-sonnet-5-5` at medium effort, giving 630 topic decisions. A baseline used the same model with a plain prompt ("Review this NDA and list any problems") and no playbook, once per NDA. A separate grading call mapped the baseline's free-text answer to topics without seeing the NDA, playbook, or gold labels. Both were scored against gold labels set by one human reviewer, and every quote was checked by code, not by the model.

## 2. Results

| Measure | Skill | Baseline |
|---|---|---|
| Status accuracy (all four statuses) | 97.1% (612/630) | 24.8% (52/210) |
| Escalation recall | **100% (45/45)** | 93.3% (14/15) |
| False escalation rate (gold acceptable, escalated) | 1.3% (6/477) | 28.3% (45/159) |
| Quote validity (verbatim and in the cited section) | 100% (547/547) | 46 of 96 quoted passages verbatim |
| Proposed language traced to the playbook | 28/28 | not applicable |
| Hallucinated quotes or wording | 0 | not measured |
| Topic decisions that changed across 3 runs | 7 of 210 (3.3%) | single run |

All three hard cases (a deviation buried in a definition, a defined-term trap, an ambiguous clause) were escalated in every run. No skill review needed a repair round: every first draft passed the schema and quote checks.

The baseline found most serious problems but flagged almost everything: it treated 128 of 159 acceptable clauses as needing a change (83 as minor, 45 as serious). Its one missed escalation was nda_15 topic 8, a five-business-day destruction deadline certified under penalty of perjury, which it called minor. The baseline was not asked to quote exactly, so its quote figure shows only that its quotations cannot be trusted as written.

## 3. Turnaround

| | Skill | Baseline |
|---|---|---|
| Mean wall-clock time per review | 15.2 s (max 28.7 s) | 23.2 s |
| Mean tokens per review (input / output) | 12,440 / 2,954 | 5,993 / 3,452 incl. grading |
| Estimated cost per review | $0.036 | $0.047 incl. grading |

The skill's time covers text extraction through the finished memo. The whole evaluation (60 reviews plus 15 grading calls) cost about $2.30 at the rates in `config/rates.json`.

Human time, NDAs 01 to 05, recorded by the repo owner: **4 minutes** to review each NDA from scratch and **1 minute** to check the skill's memo against the NDA. Treat this as an upper bound on the saving. The owner reviewed the gold labels, which list every planted deviation, before timing, so knew where to look; the times are whole minutes; and five short synthetic NDAs are not a workload sample.

## 4. Where it failed

Eighteen of 630 decisions were wrong. None was a missed escalation. Grouped by cause:

- **Governing law (topic 12), 6 misses across nda_01, 09, 13, 14.** The playbook's fallback both accepts the Counterparty's state as is and replaces exclusive county venue, so the line between acceptable and fallback is blurred. The model went both ways, and 4 of the 7 run-to-run changes are on this topic.
- **nda_10 topic 2, 3 false escalations.** The defined-term trap ("Disclosing Party" means only the Counterparty) was escalated under Definition as well as under Mutuality, where gold puts it. Arguably defensible. The owner kept the gold label.
- **nda_13 topic 1, 3 false escalations.** Equitable relief that protects only the Counterparty was read as making the NDA one-way, which triggers the Mutuality escalation. Gold treats it as a Remedies fallback only.
- **nda_13 topic 11, 2 over-escalations (fallback to escalate).** The same clause, escalated because of its mutuality effect.
- **nda_11 topic 6, 2 over-escalations.** A consent requirement for other third parties was read as barring disclosure to advisors.
- **nda_08 topic 9, 2 misses (acceptable reported as absent).** A clause denying residuals rights was reported as no clause. Low impact: both statuses mean no action.

## 5. What still needs a lawyer

- Every escalation, by design: the skill flags these, it does not resolve them.
- Every fallback before it is sent, since the playbook wording may not fit the deal.
- Anything the playbook does not cover, such as industry rules, deal context, or whether a restrictive covenant is enforceable in a given state.
- Confirming which party is the Company, because one-sided terms are judged from that side.
- Documents unlike the test set: scanned PDFs, tracked changes, exhibits, or heavily negotiated drafts.

## 6. Limitations

- **Synthetic documents.** All 15 NDAs come from one generator with three drafting styles, so real NDAs will be messier.
- **Small sample.** 15 NDAs and 15 gold escalations per run, so one more miss would move recall by about 7 points.
- **One labeler, who worked from a draft generated from the planted-deviation list.** The gold labels and the human times share that person's knowledge of the answers.
- **One playbook and mutual NDAs only.**
- **One model version and setting** (`claude-sonnet-5-5`, medium effort, October 2026). Results may change with another model or a later version.
- **The baseline mapping relies on a model grader.** It was not checked by hand.

## 7. What I would change next

- **Rewrite topic 12** so that exclusive single-county venue is clearly acceptable in a preferred state and clearly a fallback in the Counterparty's state, then rerun.
- **Add a playbook rule for issues that touch two topics**, for example one-way remedies and one-way definitions, so the expected status is not left to judgment.
- **Get a second, independent labeler** for the gold labels, and time reviewers who have not seen the planted deviations.
- **Add NDAs written by other people**, and test privately on redacted real NDAs kept in the git-ignored `private/` folder.
- **Repeat the evaluation with other models and effort levels** to see whether recall holds at lower cost.
