import copy

import extract_text
import verify_quotes as vq

SOURCE = "3.2 The Receiving Party shall hold all Confidential Information\nin strict confidence for a period of three (3) years."


def test_verbatim_quote_passes():
    assert vq.is_verbatim("hold all Confidential Information in strict confidence", SOURCE)


def test_paraphrase_fails():
    assert not vq.is_verbatim("keep all Confidential Information strictly confidential", SOURCE)
    assert not vq.is_verbatim("hold all confidential information in strict confidence", SOURCE)  # case matters


def test_whitespace_differences_are_handled_consistently():
    # the line break in the source and extra spaces or tabs in the quote all collapse to one space
    assert vq.is_verbatim("Confidential Information in strict", SOURCE)
    assert vq.is_verbatim("Confidential   Information\t\nin  strict", SOURCE)
    assert vq.is_verbatim("  three (3) years.  ", SOURCE)
    # but whitespace cannot be dropped or inserted inside a word
    assert not vq.is_verbatim("ConfidentialInformation", SOURCE)
    assert not vq.is_verbatim("Confi dential Information", SOURCE)


def test_typographic_quotes_match_straight_quotes():
    src = "“Purpose” means the Party’s evaluation."
    assert vq.is_verbatim('"Purpose" means the Party\'s evaluation.', src)


def test_ellipsis_cannot_skip_text():
    assert not vq.is_verbatim("hold all ... strict confidence", SOURCE)


def test_empty_quote_is_not_verbatim():
    assert not vq.is_verbatim("   ", SOURCE)


def test_quote_must_sit_in_cited_section(nda):
    entries = extract_text.extract(nda)
    quote = "Each party may seek injunctive relief for a breach"
    assert vq.ref_contains(quote, "11", entries)
    assert vq.ref_contains(quote, "Section 11", entries)
    assert not vq.ref_contains(quote, "12", entries)


def test_proposed_language_must_come_from_playbook(topics):
    t = next(t for t in topics.values() if t.fallback_wording)
    wording = t.fallback_wording[0]
    assert vq.proposed_from_playbook(wording, t)
    assert vq.proposed_from_playbook(wording.replace(" ", "  "), t)
    assert not vq.proposed_from_playbook(wording + " And also anything else.", t)
    assert not vq.proposed_from_playbook(wording[:20], t)  # too short to be a meaningful excerpt
    other = next(o for o in topics.values() if o.id != t.id and o.fallback_wording)
    assert not vq.proposed_from_playbook(other.fallback_wording[0], t)


def test_verify_review_counts_hallucinations(valid_review, nda, topics):
    entries = extract_text.extract(nda)
    assert vq.all_ok(vq.verify_review(valid_review, entries, topics))

    bad = copy.deepcopy(valid_review)
    bad["findings"][0]["quote"] = "Both parties promise to keep secrets"  # not in the NDA
    results = vq.verify_review(bad, entries, topics)
    assert vq.hallucinations(results) == 1
    assert results[0]["quote_ok"] is False


def test_cli_exit_codes(valid_review, nda, tmp_path):
    import json

    good = tmp_path / "good.json"
    good.write_text(json.dumps(valid_review), encoding="utf8")
    assert vq.main([str(good)]) == 0

    valid_review["findings"][3]["quote"] = "This Agreement lasts forever"
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(valid_review), encoding="utf8")
    assert vq.main([str(bad), "--source", str(nda)]) == 1
