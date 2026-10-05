"""Consistency of the synthetic test set: files, manifest, and draft gold labels agree."""

import json

import pytest

import extract_text
import playbook as pb

DATA = pb.ROOT / "data"
MANIFEST = json.loads((DATA / "seeded_deviations.json").read_text(encoding="utf8"))
GOLD = json.loads((DATA / "gold_labels.json").read_text(encoding="utf8"))
NDAS = MANIFEST["ndas"]


def test_fifteen_ndas_with_spec_mix():
    assert len(NDAS) == 15
    kinds = [e["kind"] for e in NDAS]
    assert kinds.count("clean") == 3 and kinds.count("deviation") == 9 and kinds.count("hard") == 3
    for e in NDAS:
        counted = sum(d["counted"] for d in e["deviations"])
        if e["kind"] == "clean":
            assert counted == 0, e["file"]
        elif e["kind"] == "deviation":
            assert 1 <= counted <= 4, e["file"]
        assert (DATA / "synthetic_ndas" / e["file"]).exists()


@pytest.mark.parametrize("entry", NDAS, ids=lambda e: e["file"])
def test_deviation_locations_exist_in_extracted_text(entry):
    refs = {x["ref"] for x in extract_text.extract(DATA / "synthetic_ndas" / entry["file"])}
    for d in entry["deviations"]:
        if d["where"] == "clause removed":
            continue
        ref = d["where"].split()[1]
        assert ref in refs, (entry["file"], d)


def test_gold_labels_match_manifest_and_playbook():
    topics = pb.parse()
    assert GOLD["reviewed"] in (False, True)
    assert set(GOLD["ndas"]) == {e["file"] for e in NDAS}
    for e in NDAS:
        labels = GOLD["ndas"][e["file"]]["labels"]
        assert sorted(labels, key=int) == [str(i) for i in range(1, 15)]
        assert set(labels.values()) <= {"acceptable", "fallback", "escalate", "absent"}
        for tid, status in labels.items():
            if status == "absent":
                assert topics[int(tid)].if_absent == "absent", (e["file"], tid)
        if not GOLD["reviewed"]:  # once the owner edits labels, the manifest is no longer the source
            for d in e["deviations"]:
                assert labels[str(d["topic_id"])] == d["expected_status"], (e["file"], d)


def test_timing_sheet_has_every_nda():
    lines = (DATA / "manual_timing.csv").read_text(encoding="utf8").splitlines()
    assert lines[0] == "file,minutes_manual_review,minutes_review_of_ai_output"
    assert [line.split(",")[0] for line in lines[1:]] == [e["file"] for e in NDAS]


def test_no_dashes_in_generated_documents():
    for e in NDAS:
        text = extract_text.full_text(extract_text.extract(DATA / "synthetic_ndas" / e["file"]))
        assert "\u2014" not in text and "\u2013" not in text, e["file"]
