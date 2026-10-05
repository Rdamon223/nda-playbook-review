"""Pydantic models for a review. schema.json in the skill folder is generated from these.

    python scripts/schema.py          # rewrite .claude/skills/nda-review/schema.json
    python scripts/schema.py --check  # exit 1 if schema.json is out of date

One field goes beyond the spec's finding schema: `clause_found`. The playbook says a missing
exclusions, compelled-disclosure, or return-or-destruction clause must escalate, so a finding can be
`escalate` with no quote. `clause_found: false` says so explicitly, which lets the validator still
require a quote for every clause that is actually present.
"""

from __future__ import annotations

import argparse
import json
import sys
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

sys.path.insert(0, str(Path(__file__).resolve().parent))
import playbook as pb  # noqa: E402

SCHEMA_PATH = pb.ROOT / ".claude" / "skills" / "nda-review" / "schema.json"
N_TOPICS = 14


class Status(str, Enum):
    acceptable = "acceptable"
    fallback = "fallback"
    escalate = "escalate"
    absent = "absent"


class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    topic_id: int = Field(ge=1, le=N_TOPICS)
    topic_name: str = Field(min_length=1)
    status: Status
    clause_found: bool = Field(True, description="false only when the NDA has no clause on this topic")
    quote: str = Field("", description="verbatim text from the NDA; empty only when clause_found is false")
    section_ref: str = Field("", description="e.g. 3.2; empty only when clause_found is false")
    rationale: str = Field(min_length=1, description="one or two sentences")
    proposed_language: str = Field("", description="playbook fallback wording; empty unless status is fallback")
    confidence: Confidence

    @model_validator(mode="after")
    def _rules(self):
        quote = self.quote.strip()
        if self.status == "absent" and self.clause_found:
            raise ValueError("status 'absent' requires clause_found false")
        if not self.clause_found:
            if self.status not in ("absent", "escalate"):
                raise ValueError("a missing clause must be 'absent' or 'escalate'")
            if quote or self.section_ref.strip():
                raise ValueError("a missing clause cannot have a quote or section_ref")
        else:
            if not quote:
                raise ValueError("a finding for a clause that is present requires a verbatim quote")
            if not self.section_ref.strip():
                raise ValueError("a finding for a clause that is present requires a section_ref")
            if "..." in quote or "…" in quote:
                raise ValueError("quotes must be one contiguous passage; ellipses are not allowed")
        if self.status == "fallback" and not self.proposed_language.strip():
            raise ValueError("a 'fallback' finding requires proposed_language from the playbook")
        if self.status != "fallback" and self.proposed_language.strip():
            raise ValueError("proposed_language must be empty unless status is 'fallback'")
        if self.confidence == "low" and self.status != "escalate":
            raise ValueError("low confidence must be reported as 'escalate'")
        return self


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_file: str
    playbook_version: str = ""
    model: str = Field("", description="model id, or 'claude-code' for an in-session review")
    findings: list[Finding]

    @model_validator(mode="after")
    def _one_per_topic(self):
        ids = [f.topic_id for f in self.findings]
        if sorted(ids) != list(range(1, N_TOPICS + 1)):
            raise ValueError(f"need exactly one finding per topic 1-{N_TOPICS}, got ids {ids}")
        return self


def check_against_playbook(review: Review, topics: dict[int, pb.Topic] | None = None) -> list[str]:
    """Rules that need the playbook: topic names match and absent is only used where the playbook allows it."""
    topics = topics or pb.parse()
    problems = []
    for f in review.findings:
        t = topics[f.topic_id]
        if f.topic_name.strip() != t.name:
            problems.append(f"topic {f.topic_id}: name {f.topic_name!r} does not match playbook {t.name!r}")
        if f.status == "absent" and t.if_absent != "absent":
            problems.append(f"topic {f.topic_id}: playbook says a missing clause must escalate, not 'absent'")
    return problems


def json_schema() -> dict:
    s = Review.model_json_schema()
    s["title"] = "NDA playbook review"
    s["description"] = ("One finding per playbook topic (1-14). Rules not expressible in JSON Schema are "
                        "enforced by scripts/schema.py: quote required when clause_found, proposed_language "
                        "only and always for fallback, low confidence means escalate.")
    return s


def schema_text() -> str:
    return json.dumps(json_schema(), indent=2) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Generate or check schema.json.")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    if args.check:
        current = SCHEMA_PATH.read_text(encoding="utf8") if SCHEMA_PATH.exists() else ""
        if current != schema_text():
            print(f"{SCHEMA_PATH} is out of date; run python scripts/schema.py")
            return 1
        print("schema.json is up to date")
        return 0
    SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEMA_PATH.write_text(schema_text(), encoding="utf8", newline="\n")
    print(f"wrote {SCHEMA_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
