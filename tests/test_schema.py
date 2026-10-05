import copy
import json

import pytest
from pydantic import ValidationError

import schema

BASE = {
    "topic_id": 4,
    "topic_name": "Term of the agreement and survival of confidentiality obligations",
    "status": "acceptable",
    "clause_found": True,
    "quote": "This Agreement lasts two years",
    "section_ref": "4",
    "rationale": "Meets the preferred position.",
    "proposed_language": "",
    "confidence": "high",
}


def finding(**kw):
    return {**BASE, **kw}


def test_valid_findings_pass(topics):
    schema.Finding.model_validate(finding())
    schema.Finding.model_validate(finding(status="escalate", confidence="low"))
    wording = topics[4].fallback_wording[0]
    schema.Finding.model_validate(finding(status="fallback", proposed_language=wording, confidence="medium"))
    # a missing clause: absent where harmless, escalate where the playbook says so
    schema.Finding.model_validate(finding(topic_id=9, status="absent", clause_found=False, quote="", section_ref=""))
    schema.Finding.model_validate(finding(status="escalate", clause_found=False, quote="", section_ref=""))


def test_fallback_without_proposed_language_fails():
    with pytest.raises(ValidationError, match="proposed_language"):
        schema.Finding.model_validate(finding(status="fallback", proposed_language=""))
    with pytest.raises(ValidationError, match="proposed_language"):
        schema.Finding.model_validate(finding(status="fallback", proposed_language="   "))


def test_non_absent_finding_without_quote_fails():
    for status in ("acceptable", "fallback", "escalate"):
        with pytest.raises(ValidationError, match="quote"):
            schema.Finding.model_validate(finding(status=status, quote="", proposed_language="x" if status == "fallback" else ""))


def test_other_finding_rules():
    with pytest.raises(ValidationError, match="proposed_language must be empty"):
        schema.Finding.model_validate(finding(proposed_language="Some wording"))
    with pytest.raises(ValidationError, match="low confidence"):
        schema.Finding.model_validate(finding(confidence="low"))
    with pytest.raises(ValidationError, match="clause_found false"):
        schema.Finding.model_validate(finding(status="absent", quote=""))
    with pytest.raises(ValidationError, match="missing clause"):
        schema.Finding.model_validate(finding(status="acceptable", clause_found=False, quote="", section_ref=""))
    with pytest.raises(ValidationError, match="section_ref"):
        schema.Finding.model_validate(finding(section_ref=""))
    with pytest.raises(ValidationError, match="ellipses"):
        schema.Finding.model_validate(finding(quote="This Agreement ... two years"))
    with pytest.raises(ValidationError):
        schema.Finding.model_validate(finding(status="maybe"))
    with pytest.raises(ValidationError):
        schema.Finding.model_validate(finding(extra_field=1))


def test_review_needs_exactly_one_finding_per_topic(valid_review):
    schema.Review.model_validate(valid_review)
    short = copy.deepcopy(valid_review)
    short["findings"].pop()
    with pytest.raises(ValidationError, match="exactly one finding per topic"):
        schema.Review.model_validate(short)
    dup = copy.deepcopy(valid_review)
    dup["findings"][1]["topic_id"] = 1
    with pytest.raises(ValidationError, match="exactly one finding per topic"):
        schema.Review.model_validate(dup)


def test_playbook_checks(valid_review, topics):
    r = copy.deepcopy(valid_review)
    r["findings"][0]["topic_name"] = "Mutual"
    r["findings"][2].update(status="absent", clause_found=False, quote="", section_ref="")
    problems = schema.check_against_playbook(schema.Review.model_validate(r), topics)
    assert len(problems) == 2
    assert "does not match playbook" in problems[0]
    assert "must escalate" in problems[1]


def test_schema_json_is_current():
    assert schema.SCHEMA_PATH.read_text(encoding="utf8") == schema.schema_text()
    s = json.loads(schema.SCHEMA_PATH.read_text(encoding="utf8"))
    assert set(s["$defs"]["Finding"]["properties"]) >= {
        "topic_id", "topic_name", "status", "quote", "section_ref", "rationale", "proposed_language", "confidence"}
