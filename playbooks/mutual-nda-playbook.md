# Mutual NDA Playbook (commercial services relationship)

> **DRAFT, NOT YET REVIEWED BY THE OWNER.** Drafted 2026-10-05 for owner review. Positions are generic and mainstream. This playbook is a first-pass review aid, not legal advice. A lawyer must review any NDA before signature.

## How to use this playbook

"We" and "the Company" mean the party using this playbook. "The Counterparty" means the other side. The NDA is mutual: each party discloses and each party receives.

For each of the 14 topics below, the reviewer finds the matching clause, compares it with the positions, and assigns exactly one status:

| Status | Meaning |
|---|---|
| `acceptable` | The clause meets the Preferred position, or is a minor wording difference with the same effect. |
| `fallback` | The clause misses the Preferred position but can be fixed by inserting the Acceptable fallback wording as written. No Escalate trigger applies. |
| `escalate` | Any Escalate trigger applies, the clause is ambiguous, or the reviewer is not confident. A lawyer decides. |
| `absent` | No clause covers the topic, and the topic's **If absent** rule says absence is harmless. |

General rules:

1. **When in doubt, escalate.** A missed escalation is the worst outcome. A needless escalation costs a lawyer a few minutes.
2. **Check the definitions.** A clause can read well until a defined term changes its meaning. Read every defined term the clause relies on before classifying it.
3. **Look everywhere.** A deviation can sit in a definitions section, a miscellaneous section, or an exhibit. Classify by what the agreement does, not by where the words appear.
4. **Use fallback wording only as written.** Do not draft new legal language. If the written fallback does not fix the problem, escalate.
5. **One status per topic.** If a topic has one acceptable part and one escalation trigger, the status is `escalate`.
6. **Missing clauses.** Each topic has an **If absent** rule. Where it says "escalate", report `escalate` and say the clause is missing.

Defined terms used in the fallback wording below: "Disclosing Party", "Receiving Party", "Confidential Information", "Purpose", and "Representatives". If the NDA uses different names for these, use the NDA's names when proposing the fallback and change nothing else.

---

## 1. Mutuality

**Severity:** high

**Preferred position.** Every confidentiality obligation applies equally to both parties, each acting as Disclosing Party and Receiving Party. Terms such as duration, permitted disclosure, and remedies are the same in both directions.

**Acceptable fallback.** Where the NDA uses one-way drafting but both parties will in fact exchange information, replace the obligation clause with:

> "Each party (as "Disclosing Party") may disclose Confidential Information to the other party (as "Receiving Party"). Each party, when acting as Receiving Party, shall hold the other party's Confidential Information in confidence and comply with the obligations of this Agreement."

**Escalate if:**
- Only the Company takes on confidentiality obligations, or the Company's obligations are stricter, longer, or carry heavier remedies than the Counterparty's.
- The Counterparty's information is protected but the Company's information is excluded or only partly covered.
- The NDA is labeled mutual but a separate clause, exhibit, or definition makes it one-way in effect.

**If absent:** escalate (an NDA that never states who owes the obligations cannot be relied on).

---

## 2. Definition of Confidential Information

**Severity:** medium

**Preferred position.** Confidential Information means non-public business, technical, and financial information disclosed by either party in any form (written, electronic, oral, or visual) that is marked confidential or that a reasonable person would understand to be confidential from its nature and the circumstances of disclosure. Oral disclosures are covered without a written summary requirement, or with a summary period of at least 30 days.

**Acceptable fallback.** Where the definition requires marking with no reasonable-person standard, add:

> "Confidential Information also includes information that is not marked but that a reasonable person would understand to be confidential given the nature of the information and the circumstances of disclosure."

Where oral disclosures must be confirmed in writing within a short period, replace the period with:

> "Information disclosed orally or visually is Confidential Information if it is identified as confidential at the time of disclosure or summarized in writing as confidential within thirty (30) days after disclosure."

**Escalate if:**
- Oral or visual disclosures are excluded entirely.
- Written confirmation of oral disclosures is required within fewer than 10 days.
- The definition itself carves out categories of information the Company will actually share (for example "technical data", "pricing", or "information shared with Representatives"), whether the carve-out sits in the definition or in a separate defined term the definition relies on.
- The definition is limited to information the Disclosing Party "owns", excluding third-party information the Company is obliged to protect.

**If absent:** escalate.

---

## 3. Standard exclusions

**Severity:** high

**Preferred position.** Obligations do not apply to information that the Receiving Party can show (a) is or becomes publicly available through no breach by the Receiving Party or its Representatives, (b) was known to the Receiving Party without restriction before disclosure, (c) is independently developed by the Receiving Party without use of or reference to the Confidential Information, or (d) is rightfully received from a third party without a duty of confidentiality. A requirement that the Receiving Party show this with written records is acceptable.

**Acceptable fallback.** Where one or more of the four standard exclusions is missing and no Escalate trigger applies, insert the missing item(s) from:

> "(a) is or becomes generally available to the public other than through a breach of this Agreement by the Receiving Party or its Representatives; (b) was known to the Receiving Party without restriction before receipt from the Disclosing Party; (c) is independently developed by the Receiving Party without use of or reference to the Disclosing Party's Confidential Information; or (d) is rightfully received by the Receiving Party from a third party without a duty of confidentiality."

**Escalate if:**
- The exclusions are broader than the four standard items, for example information the Receiving Party "could have" developed, information "known to the industry", or anything retained in memory (see topic 9).
- The public-domain exclusion applies even when the information became public through the Receiving Party's breach.
- The independent-development exclusion does not require development without use of the Confidential Information.
- An exclusion applies automatically without the Receiving Party bearing the burden of showing it.

**If absent:** escalate (owner decision 2026-10-03).

---

## 4. Term of the agreement and survival of obligations

**Severity:** medium

**Preferred position.** The agreement covers disclosures made during a term of one to three years, either party may end it early on written notice, and confidentiality obligations survive for two to five years after the term ends. Trade secrets stay protected for as long as they remain trade secrets under applicable law.

**Acceptable fallback.** Where survival is missing, shorter than two years, or between five and seven years, replace the survival clause with:

> "The Receiving Party's obligations under this Agreement survive for three (3) years after the expiration or termination of this Agreement, except that obligations with respect to trade secrets survive for so long as the information remains a trade secret under applicable law."

**Escalate if:**
- Obligations for all Confidential Information last forever (perpetual), not only for trade secrets.
- Survival is longer than seven years.
- Obligations end at termination with no survival period, or survival is shorter than one year.
- There is no term and no right to terminate.

**If absent:** escalate.

---

## 5. Permitted use (purpose limitation)

**Severity:** medium

**Preferred position.** The Receiving Party may use Confidential Information only for a specific, defined Purpose, such as evaluating, negotiating, or performing the services relationship between the parties.

**Acceptable fallback.** Where the use restriction exists but the Purpose is not defined, add:

> "The Receiving Party shall use the Disclosing Party's Confidential Information solely for the purpose of evaluating, negotiating, and performing a potential services relationship between the parties (the "Purpose")."

**Escalate if:**
- Use is allowed for "any purpose", for the Receiving Party's "business", or for any purpose broader than the relationship.
- Use is allowed to develop, improve, or benchmark competing products or services.
- Use is allowed to train, fine-tune, or evaluate machine learning or AI models, or to build aggregated or derived data sets.
- The Purpose is defined so vaguely that the reviewer cannot say what use is allowed.

**If absent:** escalate.

---

## 6. Permitted disclosure to representatives

**Severity:** medium

**Preferred position.** The Receiving Party may share Confidential Information with its and its affiliates' employees, officers, directors, contractors, and professional advisors (legal, accounting, financial) who need to know it for the Purpose and who are bound by confidentiality obligations at least as protective as the NDA. The Receiving Party is responsible for any breach by its Representatives.

**Acceptable fallback.** Where affiliates, contractors, or professional advisors are left out, replace the representatives clause with:

> "The Receiving Party may disclose Confidential Information to its and its affiliates' employees, officers, directors, contractors, and professional advisors who need to know it for the Purpose and who are bound by confidentiality obligations at least as protective as those in this Agreement (collectively, "Representatives"). The Receiving Party is responsible for any breach of this Agreement by its Representatives."

**Escalate if:**
- Each disclosure to the Receiving Party's own employees needs the Disclosing Party's prior written consent.
- Each Representative must personally sign the NDA or a joinder.
- Disclosure to legal or financial advisors is prohibited.
- Representatives may receive information with no confidentiality obligation, or the Receiving Party is not responsible for their breaches.

**If absent:** escalate.

---

## 7. Compelled disclosure

**Severity:** high

**Preferred position.** The Receiving Party may disclose Confidential Information when required by law, regulation, subpoena, or court order, provided that it gives prompt written notice where legally allowed, reasonably cooperates (at the Disclosing Party's expense) with efforts to obtain a protective order, and discloses only the portion legally required.

**Acceptable fallback.** Where the clause lacks notice, cooperation, or the "only the portion required" limit, replace it with:

> "If the Receiving Party is required by law, regulation, subpoena, or court order to disclose Confidential Information, it shall, to the extent legally permitted, give the Disclosing Party prompt written notice, reasonably cooperate at the Disclosing Party's expense with any effort to obtain a protective order, and disclose only the portion of the Confidential Information that it is legally required to disclose."

**Escalate if:**
- The Receiving Party must refuse to comply, or must contest the demand at its own cost.
- Notice is required even where the law prohibits it.
- The Receiving Party may disclose on any "request" from a government body or third party, not only on a legal requirement.
- There is no notice obligation and no limit on what may be disclosed.

**If absent:** escalate (owner decision 2026-10-03).

---

## 8. Return or destruction of materials

**Severity:** medium

**Preferred position.** On written request or at the end of the relationship, the Receiving Party returns or destroys Confidential Information within 30 days and certifies destruction in writing on request. The Receiving Party may keep copies in automatic electronic backups and copies it must keep to comply with law or its document retention policies. Anything kept stays confidential for as long as it is kept.

**Acceptable fallback.** Where the backup and legal-retention carve-out is missing, add:

> "The Receiving Party is not required to delete Confidential Information held in automatic electronic backup systems or retained to comply with applicable law or bona fide document retention policies, provided that any retained Confidential Information remains subject to this Agreement for as long as it is retained."

**Escalate if:**
- Destruction is required within fewer than 10 days.
- An officer must certify destruction under penalty of perjury, or the Disclosing Party may audit or inspect the Receiving Party's systems.
- Destruction is required with no exception for legal retention and the fallback wording is expressly rejected or contradicted elsewhere in the NDA.
- The Disclosing Party may demand return of the Receiving Party's own work product or analyses that contain no Confidential Information.

**If absent:** escalate (owner decision 2026-10-03).

---

## 9. Residuals clause

**Severity:** high

**Preferred position.** No residuals clause. Information retained in memory gets the same protection as any other Confidential Information.

**Acceptable fallback.** If the Counterparty insists on a residuals clause, it must be no broader than:

> "Neither party is restricted from using general skills, know-how, and experience retained in the unaided memory of its personnel who had access to Confidential Information, provided that this does not apply to information intentionally memorized for the purpose of retaining it, does not grant any license under any patent, copyright, or trade secret, and does not permit disclosure of the source of the information or of any specific Confidential Information."

**Escalate if:**
- A residuals clause covers information intentionally memorized, or does not require "unaided" memory.
- A residuals clause covers trade secrets, source code, pricing, or customer data.
- A residuals clause grants a license or says the Receiving Party owes no royalty.
- A residuals clause runs in favor of the Counterparty only.

**If absent:** report `absent` (absence is the Preferred position; owner decision 2026-10-03).

---

## 10. Non-solicitation or non-compete language

**Severity:** high

**Preferred position.** The NDA contains no non-compete, exclusivity, or non-solicitation obligations. Those belong in a separate, negotiated agreement.

**Acceptable fallback.** If the Counterparty insists on an employee non-solicit, it must be mutual and no broader than:

> "For twelve (12) months after the Effective Date, neither party shall directly solicit for employment any employee of the other party with whom it had material contact in connection with the Purpose, provided that general solicitations not targeted at the other party's employees, and hiring anyone who responds to them, do not breach this section."

**Escalate if:**
- Any non-compete, exclusivity, or restriction on doing business with third parties appears anywhere in the NDA, including in definitions or exhibits.
- A non-solicit covers customers, suppliers, or business partners.
- An employee non-solicit lasts longer than 12 months, covers all employees, prohibits hiring (not only soliciting), or binds only the Company.

**If absent:** report `absent` (absence is the Preferred position; owner decision 2026-10-03).

---

## 11. Remedies and injunctive relief

**Severity:** medium

**Preferred position.** Each party acknowledges that a breach may cause irreparable harm and that the non-breaching party may seek injunctive or other equitable relief, in addition to any other remedy, without proving actual damages. Each party bears its own legal fees, or fees go to the prevailing party in either direction.

**Acceptable fallback.** Where the equitable relief clause runs in one direction only, or requires a bond with no exception, replace it with:

> "Each party acknowledges that unauthorized use or disclosure of the other party's Confidential Information may cause irreparable harm for which monetary damages would be inadequate. Accordingly, the non-breaching party may seek injunctive or other equitable relief, in addition to any other remedy available at law or in equity."

**Escalate if:**
- Only one party may recover legal fees, or the Company must pay the Counterparty's fees in any dispute regardless of outcome.
- Liquidated damages, penalties, or uncapped indemnities for breach.
- The Company waives the right to oppose an injunction or consents to one in advance.
- The Counterparty's liability is capped or excluded while the Company's is not.

**If absent:** report `absent` (equitable relief remains available under general law; a lawyer can add the clause if wanted).

---

## 12. Governing law and venue

**Severity:** low

**Preferred position.** The law of the Company's home state, Delaware, or New York governs, with exclusive venue in the courts of that state.

**Acceptable fallback.** The law and courts of the Counterparty's home state are acceptable if it is a US state. Where venue is exclusive to the Counterparty's county, replace the venue sentence with:

> "Each party submits to the non-exclusive jurisdiction of the state and federal courts located in the state whose law governs this Agreement."

**Escalate if:**
- The governing law is not the law of a US state.
- Disputes must go to binding arbitration, or to arbitration outside the United States.
- The Company waives a jury trial while the Counterparty does not, or the clause otherwise applies to one side only.
- Governing law and venue point to different states with no stated reason.

**If absent:** report `absent` (low risk; a lawyer can add the clause if wanted).

---

## 13. Assignment and change of control

**Severity:** low

**Preferred position.** Neither party may assign the NDA without the other's consent, except to an affiliate or to a successor in a merger, acquisition, or sale of substantially all of its assets, with written notice. The agreement binds permitted successors and assigns.

**Acceptable fallback.** Where the clause bars all assignment, including in a merger or sale, replace it with:

> "Neither party may assign this Agreement without the other party's prior written consent, which shall not be unreasonably withheld, except that either party may assign this Agreement without consent to an affiliate or to a successor in connection with a merger, acquisition, or sale of all or substantially all of its assets, on written notice to the other party."

**Escalate if:**
- The Counterparty may assign freely but the Company may not.
- Assignment to a competitor of the Company is allowed without consent.
- A change of control of the Company terminates the NDA or triggers return of information while the Counterparty has no matching obligation.

**If absent:** report `absent` (low risk; general law applies).

---

## 14. No license, no warranty, no obligation to proceed

**Severity:** low

**Preferred position.** Disclosure grants no license to any intellectual property. Confidential Information is provided "as is" with no warranty of accuracy or completeness. Neither party is obliged to enter into any further agreement or transaction, and either party may end discussions at any time.

**Acceptable fallback.** Where any of the three statements is missing and no Escalate trigger applies, add:

> "No license under any patent, copyright, trade secret, or other intellectual property right is granted by this Agreement. All Confidential Information is provided "as is", without warranty of any kind as to its accuracy or completeness. Neither party is obligated to enter into any further agreement or transaction, and either party may end discussions at any time."

**Escalate if:**
- The Company warrants the accuracy or completeness of its information, or accepts liability for the Counterparty's reliance on it.
- The NDA creates any commitment to proceed, exclusivity, standstill, or "no-shop" obligation.
- The NDA grants any license, or assigns or licenses "feedback", ideas, or improvements to either party.

**If absent:** report `absent` (low risk; a lawyer can add the clause if wanted).

---

*This playbook supports a first-pass review. It is not legal advice, and it does not replace review by a lawyer.*
