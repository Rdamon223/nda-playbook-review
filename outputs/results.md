# Evaluation results

Model `claude-sonnet-5-5`, effort medium, playbook Version 1. 15 synthetic NDAs, skill run 3 times each, baseline once.

## Accuracy

| Measure | Skill | Baseline |
|---|---|---|
| Topic decisions scored | 630 | 210 |
| Status accuracy | 97.1% | 24.8% |
| Accuracy, absent and acceptable treated as one | 97.5% | 32.4% |
| Escalation recall | 100.0% (45/45) | 93.3% (14/15) |
| False escalation rate | 1.3% (6/477) | 28.3% (45/159) |
| Quote validity | 100.0% (547/547) | 46/96 quoted passages verbatim |
| Hallucinations (quotes or wording not traceable) | 0 | not measured |

Skill reviews that failed validation after repairs: 0. Reviews that needed at least one repair round: 0. First drafts with a quote or proposed-wording problem caught by the validator: 0. Quotes in the cited section: 547/547. Proposed language from the playbook: 28/28.

### Accuracy by topic

| # | Topic | Skill | Baseline |
|---|---|---|---|
| 1 | Mutuality | 93.3% | 86.7% |
| 2 | Definition of Confidential Information | 93.3% | 6.7% |
| 3 | Standard exclusions | 100.0% | 6.7% |
| 4 | Term of the agreement and survival of obligations | 100.0% | 13.3% |
| 5 | Permitted use (purpose limitation) | 100.0% | 60.0% |
| 6 | Permitted disclosure to representatives | 95.6% | 6.7% |
| 7 | Compelled disclosure | 100.0% | 20.0% |
| 8 | Return or destruction of materials | 100.0% | 6.7% |
| 9 | Residuals clause | 95.6% | 26.7% |
| 10 | Non-solicitation or non-compete language | 100.0% | 40.0% |
| 11 | Remedies and injunctive relief | 95.6% | 6.7% |
| 12 | Governing law and venue | 86.7% | 20.0% |
| 13 | Assignment and change of control | 100.0% | 6.7% |
| 14 | No license, no warranty, no obligation to proceed | 100.0% | 40.0% |

### Skill confusion (rows gold, columns predicted, all runs)

| gold \ predicted | acceptable | fallback | escalate | absent | none |
|---|---|---|---|---|---|
| acceptable | 465 | 4 | 6 | 2 | 0 |
| fallback | 2 | 24 | 4 | 0 | 0 |
| escalate | 0 | 0 | 45 | 0 | 0 |
| absent | 0 | 0 | 0 | 78 | 0 |

## Consistency

Across 3 skill runs, 7 of 210 topic decisions (3.3%) changed status between runs.

- nda_01.docx topic 12: acceptable, fallback, acceptable
- nda_08.docx topic 9: acceptable, absent, absent
- nda_09.docx topic 12: acceptable, fallback, acceptable
- nda_11.docx topic 6: escalate, fallback, escalate
- nda_13.docx topic 11: escalate, fallback, escalate
- nda_13.docx topic 12: acceptable, acceptable, fallback
- nda_14.docx topic 12: fallback, fallback, acceptable

## Turnaround

| Measure | Skill (per review) | Baseline (per review, incl. grader tokens) |
|---|---|---|
| Mean wall-clock seconds | 15.2 | 23.2 |
| Max wall-clock seconds | 28.7 | 30.1 |
| Mean input tokens | 12440 | 5993 |
| Mean output tokens | 2954 | 3452 |
| Mean estimated cost (USD) | 0.036 | 0.0465 |
| Total estimated cost (USD) | 1.6179 | 0.6975 |

Skill seconds cover extraction through memo, including any repair calls. Baseline seconds cover the review call only. Costs use config/rates.json.

### Human review time (minutes, from data/manual_timing.csv)

| File | Manual review | Review of AI output |
|---|---|---|
| nda_01.docx | 4.0 | 1.0 |
| nda_02.docx | 4.0 | 1.0 |
| nda_03.docx | 4.0 | 1.0 |
| nda_04.docx | 4.0 | 1.0 |
| nda_05.docx | 4.0 | 1.0 |

## Skill misses (every run)

| File | Run | Topic | Gold | Predicted |
|---|---|---|---|---|
| nda_01.docx | 1 | 12. Governing law and venue | fallback | acceptable |
| nda_01.docx | 3 | 12. Governing law and venue | fallback | acceptable |
| nda_08.docx | 2 | 9. Residuals clause | acceptable | absent |
| nda_08.docx | 3 | 9. Residuals clause | acceptable | absent |
| nda_09.docx | 2 | 12. Governing law and venue | acceptable | fallback |
| nda_10.docx | 1 | 2. Definition of Confidential Information | acceptable | escalate |
| nda_10.docx | 2 | 2. Definition of Confidential Information | acceptable | escalate |
| nda_10.docx | 3 | 2. Definition of Confidential Information | acceptable | escalate |
| nda_11.docx | 1 | 6. Permitted disclosure to representatives | fallback | escalate |
| nda_11.docx | 3 | 6. Permitted disclosure to representatives | fallback | escalate |
| nda_13.docx | 1 | 1. Mutuality | acceptable | escalate |
| nda_13.docx | 1 | 11. Remedies and injunctive relief | fallback | escalate |
| nda_13.docx | 2 | 1. Mutuality | acceptable | escalate |
| nda_13.docx | 3 | 1. Mutuality | acceptable | escalate |
| nda_13.docx | 3 | 11. Remedies and injunctive relief | fallback | escalate |
| nda_13.docx | 3 | 12. Governing law and venue | acceptable | fallback |
| nda_14.docx | 1 | 12. Governing law and venue | acceptable | fallback |
| nda_14.docx | 2 | 12. Governing law and venue | acceptable | fallback |
