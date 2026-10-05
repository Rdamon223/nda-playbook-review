"""Render a validated review as a one-page markdown memo: summary table, escalations first,
then fallbacks, then a short list of everything else, and the lawyer-review footer.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

FOOTER = ("*This memo is a first-pass review generated with an AI tool against a written playbook. "
          "It is not legal advice. A lawyer must review the NDA and this memo before anyone relies on "
          "either.*")

STATUS_ORDER = {"escalate": 0, "fallback": 1, "acceptable": 2, "absent": 3}
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _trim(text: str, n: int) -> str:
    return text if len(text) <= n else text[: n - 3].rstrip() + "..."


def render(review: dict, topics: dict, *, today: date | None = None) -> str:
    """review is the review JSON (a dict); topics is playbook.parse() output."""
    today = today or date.today()
    findings = sorted(review["findings"],
                      key=lambda f: (STATUS_ORDER[f["status"]],
                                     SEVERITY_ORDER.get(topics[f["topic_id"]].severity, 3),
                                     f["topic_id"]))
    counts = {s: sum(f["status"] == s for f in findings) for s in STATUS_ORDER}
    name = Path(review["source_file"]).name

    out = [f"# NDA review memo: {name}", ""]
    meta = [f"Reviewed {today.isoformat()} against the mutual NDA playbook"]
    if review.get("playbook_version"):
        meta[0] += f" ({review['playbook_version']})"
    if review.get("company"):
        meta[0] += f" for {review['company']}"
    if review.get("model"):
        meta.append(f"model `{review['model']}`")
    out += [", ".join(meta) + ".", ""]
    out += [f"**{counts['escalate']} escalate, {counts['fallback']} fallback, "
            f"{counts['acceptable']} acceptable, {counts['absent']} absent.**", ""]

    out += ["| # | Topic | Severity | Status | Section | Confidence |",
            "|---|---|---|---|---|---|"]
    for f in findings:
        status = f["status"].upper() if f["status"] == "escalate" else f["status"]
        ref = f["section_ref"] or ("missing" if not f.get("clause_found", True) else "")
        out.append(f"| {f['topic_id']} | {_cell(f['topic_name'])} | {topics[f['topic_id']].severity} | "
                   f"{status} | {_cell(ref)} | {f['confidence']} |")
    out.append("")

    esc = [f for f in findings if f["status"] == "escalate"]
    if esc:
        out += ["## Escalations (a lawyer decides)", ""]
        for f in esc:
            where = f"section {f['section_ref']}" if f["section_ref"] else "clause missing"
            out.append(f"**{f['topic_id']}. {f['topic_name']}** ({where}). {f['rationale']}")
            if f["quote"]:
                out.append(f"> {_trim(f['quote'], 300)}")
            out.append("")

    fb = [f for f in findings if f["status"] == "fallback"]
    if fb:
        out += ["## Fallbacks (playbook wording to propose)", ""]
        for f in fb:
            out.append(f"**{f['topic_id']}. {f['topic_name']}** (section {f['section_ref']}). {f['rationale']}")
            out.append(f"> {_trim(f['quote'], 200)}")
            out.append("")
            out.append(f"Propose: \"{f['proposed_language']}\"")
            out.append("")

    rest = [f for f in findings if f["status"] in ("acceptable", "absent")]
    if rest:
        out += ["## Acceptable or absent", ""]
        for f in rest:
            where = f"section {f['section_ref']}" if f["section_ref"] else "no clause"
            out.append(f"- **{f['topic_id']}. {f['topic_name']}** ({where}): {f['rationale']}")
        out.append("")

    out += ["---", "", FOOTER, ""]
    return "\n".join(out)
