"""review.py and eval.py without the API: a fake client stands in for Claude."""

import json
from types import SimpleNamespace

import pytest

import env
import eval as ev
import memo
import review as rv


class FakeClient:
    """Returns the queued replies in order and records every request."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []
        self.messages = self

    def stream(self, **kwargs):
        self.requests.append(json.loads(json.dumps(kwargs, default=str)))
        text = self.replies.pop(0)
        msg = SimpleNamespace(
            content=[SimpleNamespace(type="text", text=text)],
            usage=SimpleNamespace(input_tokens=100, output_tokens=50,
                                  cache_creation_input_tokens=0, cache_read_input_tokens=0))
        return _Stream(msg)


class _Stream:
    def __init__(self, msg):
        self.msg = msg

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self.msg


def reply_for(review):
    return json.dumps({"findings": review["findings"]})


def test_review_valid_first_time(nda, valid_review, topics):
    client = FakeClient([reply_for(valid_review)])
    res = rv.review(nda, "Fernhollow Analytics LLC", client=client, model="test-model", effort="medium",
                    topics=topics)
    assert res["valid"] and res["attempts"] == 1 and res["first_attempt_problems"] == []
    assert res["review"]["company"] == "Fernhollow Analytics LLC"
    assert memo.FOOTER in res["memo"]
    req = client.requests[0]
    assert req["model"] == "test-model" and req["output_config"] == {"effort": "medium"}
    assert "Fernhollow Analytics LLC" in req["messages"][0]["content"]
    assert "<playbook>" in req["system"][0]["text"]


def test_review_repairs_a_bad_quote(nda, valid_review, topics):
    bad = json.loads(json.dumps(valid_review))
    bad["findings"][0]["quote"] = "Each party promises to keep secrets"
    client = FakeClient([reply_for(bad), reply_for(valid_review)])
    res = rv.review(nda, "Fernhollow Analytics LLC", client=client, model="m", topics=topics)
    assert res["valid"] and res["attempts"] == 2
    assert any("verbatim" in p for p in res["first_attempt_problems"])
    assert "verbatim" in client.requests[1]["messages"][-1]["content"]
    assert "output_config" not in client.requests[0]   # no effort set, nothing sent


def test_review_gives_up_after_max_repairs(nda, topics):
    client = FakeClient(["not json"] * (rv.MAX_REPAIRS + 1))
    res = rv.review(nda, "X", client=client, model="m", topics=topics)
    assert not res["valid"] and res["attempts"] == rv.MAX_REPAIRS + 1
    assert res["raw_reply"] == "not json" and "memo" not in res


def test_parse_json_handles_fences():
    assert rv.parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert rv.parse_json("no object here") is None


def test_settings_require_model(monkeypatch, tmp_path):
    monkeypatch.setattr(env, "ENV_FILE", tmp_path / "missing.env")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "placeholder")
    monkeypatch.delenv("NDA_REVIEW_MODEL", raising=False)
    with pytest.raises(env.SettingError, match="NDA_REVIEW_MODEL"):
        rv.settings()
    monkeypatch.setenv("NDA_REVIEW_MODEL", "some-model")
    monkeypatch.setenv("NDA_REVIEW_EFFORT", "extreme")
    with pytest.raises(env.SettingError, match="NDA_REVIEW_EFFORT"):
        rv.settings()


def test_dotenv_does_not_override_environment(monkeypatch, tmp_path):
    f = tmp_path / ".env"
    f.write_text('# comment\nNDA_TEST_A="from file"\nNDA_TEST_B=from file\n', encoding="utf8")
    monkeypatch.setenv("NDA_TEST_B", "from environment")
    monkeypatch.delenv("NDA_TEST_A", raising=False)
    env.load_dotenv(f)
    import os
    assert os.environ["NDA_TEST_A"] == "from file"
    assert os.environ["NDA_TEST_B"] == "from environment"
    monkeypatch.delenv("NDA_TEST_A")


def test_eval_refuses_until_gold_reviewed(monkeypatch, tmp_path, capsys):
    gold = json.loads(ev.GOLD.read_text(encoding="utf8"))
    gold["reviewed"] = False
    f = tmp_path / "gold.json"
    f.write_text(json.dumps(gold), encoding="utf8")
    monkeypatch.setattr(ev, "GOLD", f)
    monkeypatch.setattr(ev, "run_all", lambda *a, **k: pytest.fail("must not run"))
    assert ev.main(["--run"]) == 1
    assert ev.main(["--report"]) == 1
    assert "reviewed" in capsys.readouterr().out


def test_score_counts_escalation_recall_and_false_escalations(topics):
    labels = {str(t): "acceptable" for t in topics}
    labels["1"] = "escalate"
    labels["2"] = "escalate"
    gold = {"ndas": {"a.docx": {"labels": labels}}}
    pred = {t: "acceptable" for t in topics}
    pred[1] = "escalate"          # caught
    pred[2] = "fallback"          # missed escalation
    pred[3] = "escalate"          # false escalation
    del pred[4]                   # topic missing from the review counts as wrong
    s = ev.score({"a.docx": [pred]}, gold, topics)
    assert s["decisions"] == 14
    assert s["escalation_recall"] == 0.5 and s["escalations_caught"] == 1
    assert s["false_escalations"] == 1 and s["acceptable_gold"] == 12
    assert s["accuracy"] == round(11 / 14, 4)
    assert {(m["topic_id"], m["predicted"]) for m in s["misses"]} == {(2, "fallback"), (3, "escalate"), (4, "none")}


def test_baseline_mapping_uses_playbook_absent_rule(topics):
    grades = {"1": {"label": "serious"}, "2": {"label": "minor"}, "3": {"label": "missing"},
              "9": {"label": "missing"}, "10": {"label": "not_flagged"}}
    got = ev.baseline_statuses(grades, topics)
    assert got[1] == "escalate" and got[2] == "fallback" and got[10] == "acceptable"
    assert got[3] == "escalate"   # missing exclusions must escalate
    assert got[9] == "absent"     # missing residuals clause is fine
    assert 4 not in got           # ungraded topic stays unscored (counts as wrong)


def test_consistency_counts_changed_topics(topics):
    run1 = {t: "acceptable" for t in topics}
    run2 = {**run1, 5: "escalate"}
    c = ev.consistency({"a.docx": [run1, run2, run1]}, topics)
    assert c["topic_decisions"] == 14 and c["changed"] == 1
    assert c["details"][0]["statuses"] == ["acceptable", "escalate", "acceptable"]


def test_baseline_quotes_checked_against_source():
    source = "The Receiving Party will use Confidential Information only to evaluate the deal."
    answer = ('Section 5 says "will use Confidential Information only to evaluate the deal" which is fine, '
              'but "the Receiving Party may disclose anything it likes" is a concern. "short".')
    assert ev.baseline_quotes(answer, source) == (1, 2)


def test_cost_uses_rate_table():
    table = {"m": {"input": 2.0, "output": 10.0, "cache_write": 2.5, "cache_read": 0.1}}
    usage = {"input_tokens": 1_000_000, "output_tokens": 100_000, "cache_read_input_tokens": 1_000_000}
    assert ev.cost(usage, "m", table) == pytest.approx(2.0 + 1.0 + 0.1)
    assert ev.cost(usage, "unknown", table) is None
