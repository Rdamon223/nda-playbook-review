"""Validate a review JSON and render its memo. Used by the in-Claude-Code skill (step 8) and by review.py.

    python scripts/finalize.py outputs/nda_01.json [--source data/synthetic_ndas/nda_01.docx] [--memo out.md]

Checks, in order:
1. The JSON matches the schema (pydantic): one finding per topic, quote rules, fallback rules.
2. Topic names match the playbook, and `absent` is only used where the playbook allows it.
3. Every quote is a verbatim passage of the NDA in the cited section, and every proposed language
   entry is the playbook's fallback wording (verify_quotes.py).

If everything passes, the memo is written next to the JSON (same name, .md). Exit 0 on success,
1 on any failure, with each problem printed so the reviewer can fix the JSON and rerun.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_text  # noqa: E402
import memo  # noqa: E402
import playbook as pb  # noqa: E402
import schema  # noqa: E402
import verify_quotes  # noqa: E402


def check(review_data: dict, source: Path, topics: dict | None = None) -> list[str]:
    topics = topics or pb.parse()
    try:
        review = schema.Review.model_validate(review_data)
    except ValidationError as e:
        return [f"schema: {err['loc']}: {err['msg']}" for err in e.errors()]
    problems = [f"playbook: {p}" for p in schema.check_against_playbook(review, topics)]
    results = verify_quotes.verify_review(review.model_dump(mode="json"), extract_text.extract(source), topics)
    for r in results:
        problems += [f"topic {r['topic_id']}: {p}" for p in r["problems"]]
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Validate a review JSON and write its memo.")
    ap.add_argument("review", type=Path)
    ap.add_argument("--source", type=Path, help="the NDA file (default: source_file in the review)")
    ap.add_argument("--memo", type=Path, help="memo path (default: the review path with .md)")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf8")

    data = json.loads(args.review.read_text(encoding="utf8"))
    source = args.source or Path(data.get("source_file", ""))
    if not source.exists():
        print(f"source NDA not found: {source}")
        return 1
    topics = pb.parse()
    problems = check(data, source, topics)
    if problems:
        print(f"{len(problems)} problem(s); memo not written:")
        for p in problems:
            print(f"  - {p}")
        return 1
    memo_path = args.memo or args.review.with_suffix(".md")
    memo_path.write_text(memo.render(data, topics), encoding="utf8", newline="\n")
    print(f"valid; memo written to {memo_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
