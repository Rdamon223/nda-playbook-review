"""Check that every quote in a review is a verbatim substring of the NDA, and that every piece of
proposed language comes word for word from the playbook's fallback wording.

    python scripts/verify_quotes.py outputs/nda_01.json [--source data/synthetic_ndas/nda_01.docx]

This check is deterministic. The model never grades its own quotes.

Normalization, applied to both sides before comparing:
- every run of whitespace (spaces, tabs, line breaks, non-breaking spaces) becomes one space;
- curly quotes and apostrophes become straight ones.
Nothing else is normalized: case, punctuation, and words must match exactly. Ellipses are not
allowed to skip text, so a quote must be one contiguous passage.

Exit code 0 when every quote and every proposed language entry verifies, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_text  # noqa: E402
import playbook as pb  # noqa: E402

QUOTE_MAP = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', " ": " "})
MIN_PARTIAL_FALLBACK = 40   # a partial fallback (one list item, one sentence) must be at least this long


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.translate(QUOTE_MAP)).strip()


def is_verbatim(quote: str, source: str) -> bool:
    q = normalize(quote)
    return bool(q) and q in normalize(source)


def _norm_ref(ref: str) -> str:
    ref = re.sub(r"^(?:section|sec\.|article|clause|§)\s*", "", ref.strip(), flags=re.I)
    return ref.rstrip(".").replace(" ", "")


def ref_contains(quote: str, section_ref: str, entries: list[dict]) -> bool:
    """True when the quote sits inside the cited section (or one of its sub-clauses)."""
    want = _norm_ref(section_ref)
    if not want:
        return False
    scoped = [e["text"] for e in entries
              if _norm_ref(e["ref"]) == want or _norm_ref(e["ref"]).startswith((want + ".", want + "("))]
    return bool(scoped) and is_verbatim(quote, "\n".join(scoped))


def proposed_from_playbook(proposed: str, topic: pb.Topic) -> bool:
    p = normalize(proposed)
    if not p:
        return False
    for wording in topic.fallback_wording:
        w = normalize(wording)
        if p == w or (p in w and len(p) >= MIN_PARTIAL_FALLBACK):
            return True
    return False


def verify_review(review: dict, entries: list[dict], topics: dict[int, pb.Topic]) -> list[dict]:
    source = extract_text.full_text(entries)
    results = []
    for f in review["findings"]:
        topic = topics.get(f["topic_id"])
        r = {"topic_id": f["topic_id"], "status": f["status"],
             "quote_ok": None, "ref_ok": None, "proposed_ok": None, "problems": []}
        if f.get("quote"):
            r["quote_ok"] = is_verbatim(f["quote"], source)
            if not r["quote_ok"]:
                r["problems"].append("quote is not a verbatim passage of the NDA")
            else:
                r["ref_ok"] = ref_contains(f["quote"], f.get("section_ref", ""), entries)
                if not r["ref_ok"]:
                    r["problems"].append(f"quote found, but not in section {f.get('section_ref')!r}")
        if f.get("proposed_language"):
            r["proposed_ok"] = bool(topic) and proposed_from_playbook(f["proposed_language"], topic)
            if not r["proposed_ok"]:
                r["problems"].append("proposed language is not the playbook's fallback wording for this topic")
        results.append(r)
    return results


def hallucinations(results: list[dict]) -> int:
    """Quotes or proposed language that do not trace to the NDA or the playbook."""
    return sum((r["quote_ok"] is False) + (r["proposed_ok"] is False) for r in results)


def all_ok(results: list[dict]) -> bool:
    return hallucinations(results) == 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Verify quotes and proposed language in a review JSON.")
    ap.add_argument("review", type=Path)
    ap.add_argument("--source", type=Path, help="the NDA file (default: source_file in the review)")
    args = ap.parse_args(argv)

    review = json.loads(args.review.read_text(encoding="utf8"))
    source = args.source or Path(review["source_file"])
    results = verify_review(review, extract_text.extract(source), pb.parse())
    sys.stdout.reconfigure(encoding="utf8")
    for r in results:
        flag = "OK " if not r["problems"] else "BAD"
        print(f"{flag} topic {r['topic_id']:>2} {r['status']:<10} {'; '.join(r['problems'])}")
    n_quotes = sum(r["quote_ok"] is not None for r in results)
    n_valid = sum(bool(r["quote_ok"]) for r in results)
    print(f"\nQuotes verified: {n_valid}/{n_quotes}. Not traceable: {hallucinations(results)}. "
          f"Quotes outside the cited section: {sum(r['ref_ok'] is False for r in results)}.")
    return 0 if all_ok(results) else 1


if __name__ == "__main__":
    sys.exit(main())
