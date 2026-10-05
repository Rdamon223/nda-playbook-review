"""Playbook parsing, text extraction, memo rendering, and the finalize step."""

import copy
import json
from datetime import date

import extract_text
import finalize
import memo
import playbook as pb


def test_playbook_has_14_complete_topics(topics):
    assert sorted(topics) == list(range(1, 15))
    for t in topics.values():
        assert t.severity in ("high", "medium", "low"), t.id
        assert t.preferred, t.id
        assert t.fallback_wording, t.id
        assert t.escalate_if, t.id
    assert [t.if_absent for t in topics.values()] == ["escalate"] * 8 + ["absent"] * 6


def test_skill_playbook_copy_matches_source():
    copy_path = pb.ROOT / ".claude" / "skills" / "nda-review" / "playbook.md"
    assert copy_path.read_bytes() == pb.PLAYBOOK.read_bytes(), "run: cp playbooks/mutual-nda-playbook.md .claude/skills/nda-review/playbook.md"


def test_playbook_version():
    assert pb.version().startswith("Version ")


def test_extract_docx_numbers_sections(nda):
    entries = extract_text.extract(nda)
    assert entries[0]["ref"] == "Preamble"
    refs = [e["ref"] for e in entries if e["ref"] != "Preamble"]
    assert refs == [str(i) for i in range(1, 15)]
    assert entries[-1]["text"].startswith("14. No license is granted")


def test_extract_sub_clauses_and_unnumbered_paragraphs():
    raw = [("1. Definitions.", None), ("(a) \"Purpose\" means the evaluation.", None),
           ("(i) first item", None), ("(b) \"Affiliate\" means a controlled entity.", None),
           ("A continuation paragraph.", None), ("Section 2. Term.", None), ("Two years.", None),
           ("30 days after notice, the obligations end.", None), ("2.1. Survival.", None)]
    refs = [e["ref"] for e in extract_text.number_paragraphs(raw)]
    assert refs == ["1", "1(a)", "1(a)(i)", "1(b)", "1(b)", "2", "2", "2", "2.1"]


def test_extract_auto_numbered_docx_paragraphs():
    raw = [("Definitions", ("5", 0)), ("Purpose means x.", ("5", 1)), ("Affiliate means y.", ("5", 1)),
           ("Obligations", ("5", 0)), ("Keep it secret.", ("5", 1))]
    refs = [e["ref"] for e in extract_text.number_paragraphs(raw)]
    assert refs == ["1", "1.1", "1.2", "2", "2.1"]


def test_extract_collapses_whitespace():
    entries = extract_text.number_paragraphs([("3.2   The  Receiving\tParty shall", None)])
    assert entries == [{"ref": "3.2", "text": "3.2 The Receiving Party shall"}]


def test_memo_orders_escalations_first_and_has_footer(valid_review, topics):
    r = copy.deepcopy(valid_review)
    r["findings"][10].update(status="escalate", confidence="medium", rationale="One-sided fee shifting.")
    r["findings"][2].update(status="escalate", clause_found=False, quote="", section_ref="",
                            rationale="No exclusions clause.")
    text = memo.render(r, topics, today=date(2026, 10, 5))
    assert "**2 escalate, 0 fallback, 12 acceptable, 0 absent.**" in text
    rows = [line for line in text.splitlines() if line.startswith("| ") and "Topic" not in line]
    assert rows[0].startswith("| 3 |") and rows[1].startswith("| 11 |")  # escalations first, high severity first
    assert text.index("## Escalations") < text.index("## Acceptable")
    assert "clause missing" in text
    assert "A lawyer must review" in text.splitlines()[-1]
    assert "\u2014" not in text and "\u2013" not in text


def test_finalize_writes_memo_for_valid_review(valid_review, tmp_path):
    path = tmp_path / "review.json"
    path.write_text(json.dumps(valid_review), encoding="utf8")
    assert finalize.main([str(path)]) == 0
    assert "A lawyer must review" in path.with_suffix(".md").read_text(encoding="utf8")


def test_finalize_rejects_bad_review(valid_review, nda, tmp_path, capsys):
    r = copy.deepcopy(valid_review)
    r["findings"][4]["quote"] = "The Receiving Party may use the information for any purpose"
    r["findings"][5]["section_ref"] = "9"
    path = tmp_path / "review.json"
    path.write_text(json.dumps(r), encoding="utf8")
    assert finalize.main([str(path)]) == 1
    out = capsys.readouterr().out
    assert "topic 5: quote is not a verbatim passage" in out
    assert "topic 6: quote found, but not in section '9'" in out
    assert not path.with_suffix(".md").exists()
