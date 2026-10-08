"""Evaluate the skill against the gold labels, with a no-playbook baseline for comparison.

    python scripts/eval.py --estimate            # counts calls and estimates cost; no API calls
    python scripts/eval.py --run                 # runs everything not already cached, then reports
    python scripts/eval.py --report              # recomputes outputs/results.* from cached runs

Refuses --run and --report until data/gold_labels.json has "reviewed": true.

Conditions, per NDA:
- Skill: review.py's workflow (SKILL.md + playbook + validator loop), RUNS times (default 3), for
  accuracy and consistency.
- Baseline: one plain prompt, "Review this NDA and list any problems.", with no playbook. It is told
  which party it acts for, so both conditions judge one-sided terms from the same side.

Mapping the baseline to topics. The baseline answers in free text, so a second, separate call
(the grader) reads only the baseline's answer and the 14 topic names. It does not see the NDA, the
playbook positions, or the gold labels. For each topic it picks one label:
    serious      the answer flags a problem it treats as significant, one-sided, or needing a lawyer
    minor        the answer suggests a change but treats it as negotiable or minor
    missing      the answer says the NDA lacks a clause on the topic
    not_flagged  the answer does not raise the topic, or says it is fine
Then code (not the grader) maps labels to statuses: serious -> escalate, minor -> fallback,
not_flagged -> acceptable, missing -> the playbook's If absent rule for that topic.

Every model output is cached under outputs/eval/raw/, so a rerun only pays for what is missing.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env  # noqa: E402
import extract_text  # noqa: E402
import playbook as pb  # noqa: E402
import review as rv  # noqa: E402
import verify_quotes  # noqa: E402

DATA = pb.ROOT / "data"
NDA_DIR = DATA / "synthetic_ndas"
GOLD = DATA / "gold_labels.json"
MANIFEST = DATA / "seeded_deviations.json"
TIMING = DATA / "manual_timing.csv"
RATES = pb.ROOT / "config" / "rates.json"
OUT = pb.ROOT / "outputs"
RAW = OUT / "eval" / "raw"
RUNS = 3
STATUSES = ("acceptable", "fallback", "escalate", "absent")
GRADE_TO_STATUS = {"serious": "escalate", "minor": "fallback", "not_flagged": "acceptable"}
DASHES = (chr(0x2014), chr(0x2013))
BASELINE_QUOTE_MIN = 30   # quoted passages in the baseline answer at least this long are checked

BASELINE_PROMPT = "Review this NDA and list any problems. You act for {company}.\n\n<nda>\n{text}\n</nda>"

GRADER_SYSTEM = """You map a lawyer-style NDA review, written in free text, onto a fixed list of topics.
You see only the review, not the NDA. Do not judge the NDA yourself. Report only what the review says.

For each topic, pick one label:
- "serious": the review flags a problem on this topic and treats it as significant, one-sided,
  unusual, high risk, or something a lawyer should look at.
- "minor": the review suggests a change on this topic but treats it as minor or negotiable.
- "missing": the review says the NDA has no clause on this topic.
- "not_flagged": the review does not raise this topic, or says it is fine.

Reply with a JSON object only, keyed by topic number as a string:
{"1": {"label": "not_flagged", "evidence": "short phrase from the review, or empty"}, ...}
Include all topics."""


# ---------------------------------------------------------------- inputs

class NotReviewed(RuntimeError):
    pass


def load_gold(require_reviewed: bool = True) -> dict:
    gold = json.loads(GOLD.read_text(encoding="utf8"))
    if require_reviewed and gold.get("reviewed") is not True:
        raise NotReviewed('data/gold_labels.json is not marked "reviewed": true. The repo owner must '
                          "review the gold labels before the evaluation runs.")
    return gold


def manifest() -> list[dict]:
    return json.loads(MANIFEST.read_text(encoding="utf8"))["ndas"]


def rates() -> dict:
    return json.loads(RATES.read_text(encoding="utf8"))


def cost(usage: dict, model: str, table: dict | None = None) -> float | None:
    r = (table or rates()).get(model)
    if not r:
        return None
    return (usage.get("input_tokens", 0) * r["input"] + usage.get("output_tokens", 0) * r["output"]
            + usage.get("cache_creation_input_tokens", 0) * r["cache_write"]
            + usage.get("cache_read_input_tokens", 0) * r["cache_read"]) / 1e6


def manual_timing() -> list[dict]:
    rows = []
    with TIMING.open(encoding="utf8") as fh:
        for row in csv.DictReader(fh):
            def num(v):
                try:
                    return float(v)
                except (TypeError, ValueError):
                    return None
            rows.append({"file": row["file"], "manual": num(row["minutes_manual_review"]),
                         "ai": num(row["minutes_review_of_ai_output"])})
    return rows


# ---------------------------------------------------------------- running

def raw_path(kind: str, stem: str) -> Path:
    return RAW / kind / f"{stem}.json"


def save(path: Path, obj: dict) -> None:
    """The repo bans em and en dashes, so any the model writes are saved as hyphens. The NDAs have
    none, so this never changes a quote."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, indent=2, ensure_ascii=False).replace(DASHES[0], "-").replace(DASHES[1], "-")
    path.write_text(text + "\n", encoding="utf8", newline="\n")


def run_skill(entry: dict, run: int, client, s: dict, topics: dict) -> dict:
    path = NDA_DIR / entry["file"]
    result = rv.review(path, entry["company"], client=client, model=s["model"], effort=s["effort"], topics=topics)
    result["run"] = run
    save(raw_path(f"skill_r{run}", path.stem), result)
    return result


def run_baseline(entry: dict, client, s: dict, topics: dict) -> dict:
    path = NDA_DIR / entry["file"]
    t0 = time.perf_counter()
    text = extract_text.format_numbered(extract_text.extract(path))
    answer, _, usage = rv.call_model(
        client, s["model"], s["effort"], "",
        [{"role": "user", "content": BASELINE_PROMPT.format(company=entry["company"], text=text)}])
    seconds = round(time.perf_counter() - t0, 1)
    topic_list = "\n".join(f"{t.id}. {t.name}" for t in topics.values())
    grade_text, _, grade_usage = rv.call_model(
        client, s["model"], s["effort"], GRADER_SYSTEM,
        [{"role": "user", "content": f"Topics:\n{topic_list}\n\n<review>\n{answer}\n</review>"}])
    grades = rv.parse_json(grade_text) or {}
    result = {"file": entry["file"], "company": entry["company"], "model": s["model"], "effort": s["effort"],
              "answer": answer, "seconds": seconds, "usage": usage,
              "grades": grades, "grade_usage": grade_usage, "grade_raw": None if grades else grade_text}
    save(raw_path("baseline", path.stem), result)
    return result


def run_all(runs: int, workers: int, only: list[str] | None) -> None:
    s = rv.settings()
    topics = pb.parse()
    client = rv.make_client()
    jobs = []
    for entry in manifest():
        if only and entry["file"] not in only:
            continue
        stem = Path(entry["file"]).stem
        for r in range(1, runs + 1):
            if not raw_path(f"skill_r{r}", stem).exists():
                jobs.append(("skill", entry, r))
        if not raw_path("baseline", stem).exists():
            jobs.append(("baseline", entry, 0))
    print(f"model {s['model']}, effort {s['effort'] or 'API default'}; {len(jobs)} job(s) to run, "
          f"{workers} at a time")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {}
        for kind, entry, r in jobs:
            fn = (lambda e=entry, r=r: run_skill(e, r, client, s, topics)) if kind == "skill" else \
                 (lambda e=entry: run_baseline(e, client, s, topics))
            futures[pool.submit(fn)] = (kind, entry["file"], r)
        for fut in as_completed(futures):
            kind, file, r = futures[fut]
            label = f"{kind}{' run ' + str(r) if r else ''} {file}"
            try:
                res = fut.result()
                flag = "" if kind == "baseline" or res["valid"] else "  INVALID"
                print(f"done {label} ({res['seconds']} s){flag}", flush=True)
            except Exception as e:  # keep going; the report shows what is missing
                print(f"FAILED {label}: {type(e).__name__}: {e}", flush=True)


# ---------------------------------------------------------------- estimate

def estimate(runs: int) -> dict:
    """Rough cost estimate without calling the API: about 4 characters per token."""
    topics = pb.parse()
    sys_tokens = len(rv.system_prompt()) / 4
    nda_tokens = [len(extract_text.format_numbered(extract_text.extract(NDA_DIR / e["file"]))) / 4
                  for e in manifest()]
    n = len(nda_tokens)
    out_skill, out_base, out_grade = 8000, 3000, 1500     # assumed output tokens, thinking included
    repair_share = 0.3                                    # assumed share of reviews needing one repair
    skill_calls = n * runs * (1 + repair_share)
    usage = {
        "input_tokens": sum(nda_tokens) * runs * (1 + 2 * repair_share)
                        + sum(nda_tokens) + n * (len(topics) * 10 + out_base),
        "cache_creation_input_tokens": sys_tokens * 4,
        "cache_read_input_tokens": sys_tokens * skill_calls,
        "output_tokens": skill_calls * out_skill + n * (out_base + out_grade),
    }
    return {"ndas": n, "skill_calls": round(skill_calls), "baseline_calls": n, "grader_calls": n,
            "usage": {k: round(v) for k, v in usage.items()}}


# ---------------------------------------------------------------- scoring

def statuses(review: dict | None) -> dict[int, str]:
    if not review or not isinstance(review.get("findings"), list):
        return {}
    out = {}
    for f in review["findings"]:
        if isinstance(f, dict) and f.get("status") in STATUSES and isinstance(f.get("topic_id"), int):
            out[f["topic_id"]] = f["status"]
    return out


def baseline_statuses(grades: dict, topics: dict) -> dict[int, str]:
    out = {}
    for tid, t in topics.items():
        g = grades.get(str(tid), {})
        label = g.get("label") if isinstance(g, dict) else None
        if label == "missing":
            out[tid] = t.if_absent
        elif label in GRADE_TO_STATUS:
            out[tid] = GRADE_TO_STATUS[label]
    return out


def baseline_quotes(answer: str, source: str) -> tuple[int, int]:
    found = [q for q in re.findall(r"[\"“]([^\"“”]+)[\"”]", answer)
             if len(q) >= BASELINE_QUOTE_MIN]
    return sum(verify_quotes.is_verbatim(q, source) for q in found), len(found)


def score(pred_by_nda: dict[str, list[dict[int, str]]], gold: dict, topics: dict) -> dict:
    """pred_by_nda: file -> list of {topic_id: status} (one per run; a missing topic counts as wrong)."""
    total = correct = loose = 0
    esc_total = esc_hit = 0
    acc_total = acc_escalated = 0
    per_topic = {tid: [0, 0] for tid in topics}
    confusion = {g: Counter() for g in STATUSES}
    misses = []
    for file, runs in pred_by_nda.items():
        labels = gold["ndas"][file]["labels"]
        for run_i, pred in enumerate(runs, 1):
            for tid in topics:
                g, p = labels[str(tid)], pred.get(tid, "none")
                total += 1
                per_topic[tid][1] += 1
                confusion[g][p] += 1
                loose += p == g or {p, g} == {"acceptable", "absent"}
                if p == g:
                    correct += 1
                    per_topic[tid][0] += 1
                else:
                    misses.append({"file": file, "run": run_i, "topic_id": tid,
                                   "topic_name": topics[tid].name, "gold": g, "predicted": p})
                if g == "escalate":
                    esc_total += 1
                    esc_hit += p == "escalate"
                if g == "acceptable":
                    acc_total += 1
                    acc_escalated += p == "escalate"

    def ratio(a, b):
        return round(a / b, 4) if b else None

    return {"decisions": total, "accuracy": ratio(correct, total),
            "accuracy_absent_as_acceptable": ratio(loose, total),
            "escalation_recall": ratio(esc_hit, esc_total), "escalations_gold": esc_total,
            "escalations_caught": esc_hit,
            "false_escalation_rate": ratio(acc_escalated, acc_total), "acceptable_gold": acc_total,
            "false_escalations": acc_escalated,
            "per_topic_accuracy": {tid: ratio(c, n) for tid, (c, n) in per_topic.items()},
            "confusion": {g: dict(c) for g, c in confusion.items()},
            "misses": misses}


def consistency(pred_by_nda: dict[str, list[dict[int, str]]], topics: dict) -> dict:
    changed = []
    n = 0
    for file, runs in pred_by_nda.items():
        if len(runs) < 2:
            continue
        for tid in topics:
            n += 1
            seen = [r.get(tid, "none") for r in runs]
            if len(set(seen)) > 1:
                changed.append({"file": file, "topic_id": tid, "statuses": seen})
    return {"topic_decisions": n, "changed": len(changed),
            "changed_rate": round(len(changed) / n, 4) if n else None, "details": changed}


def quote_stats(reviews: list[dict], topics: dict) -> dict:
    """Quote validity and hallucinations, checked by verify_quotes.py, over the final reviews."""
    quotes = valid = in_section = proposed = proposed_ok = 0
    for rev in reviews:
        if not rev or not isinstance(rev.get("findings"), list):
            continue
        entries = extract_text.extract(NDA_DIR / Path(rev["source_file"]).name)
        try:
            results = verify_quotes.verify_review(rev, entries, topics)
        except (KeyError, TypeError):
            continue
        for r in results:
            if r["quote_ok"] is not None:
                quotes += 1
                valid += bool(r["quote_ok"])
                in_section += bool(r["ref_ok"])
            if r["proposed_ok"] is not None:
                proposed += 1
                proposed_ok += bool(r["proposed_ok"])
    return {"quotes": quotes, "verbatim": valid, "in_cited_section": in_section,
            "quote_validity": round(valid / quotes, 4) if quotes else None,
            "proposed": proposed, "proposed_from_playbook": proposed_ok,
            "hallucinations": (quotes - valid) + (proposed - proposed_ok)}


def report(runs: int = RUNS) -> dict:
    gold = load_gold()
    topics = pb.parse()
    table = rates()
    entries = manifest()
    skill_runs: dict[str, list[dict]] = defaultdict(list)
    base: dict[str, dict] = {}
    missing = []
    for e in entries:
        stem = Path(e["file"]).stem
        for r in range(1, runs + 1):
            p = raw_path(f"skill_r{r}", stem)
            if p.exists():
                skill_runs[e["file"]].append(json.loads(p.read_text(encoding="utf8")))
            else:
                missing.append(f"skill run {r} {e['file']}")
        p = raw_path("baseline", stem)
        if p.exists():
            base[e["file"]] = json.loads(p.read_text(encoding="utf8"))
        else:
            missing.append(f"baseline {e['file']}")

    skill_pred = {f: [statuses(r["review"]) for r in rs] for f, rs in skill_runs.items()}
    base_pred = {f: [baseline_statuses(b["grades"], topics)] for f, b in base.items()}
    skill_results = [r for rs in skill_runs.values() for r in rs]

    # quote checks: final reviews, and how many first drafts had a quote or wording problem
    final_reviews = [r["review"] for r in skill_results]
    first_draft_problem = sum(
        any("verbatim" in p or "not in section" in p or "found, but" in p or "fallback wording" in p
            for p in (r.get("first_attempt_problems") or []))
        for r in skill_results)

    base_q_ok = base_q_n = 0
    for f, b in base.items():
        ok, n = baseline_quotes(b["answer"], extract_text.full_text(extract_text.extract(NDA_DIR / f)))
        base_q_ok += ok
        base_q_n += n

    def turnaround(results, usage_key="usage", extra_key=None):
        if not results:
            return {}
        secs = [r["seconds"] for r in results]
        usages = []
        for r in results:
            u = dict(r[usage_key])
            if extra_key and r.get(extra_key):
                rv.add_usage(u, r[extra_key])
            usages.append(u)
        costs = [cost(u, r["model"], table) for u, r in zip(usages, results)]
        return {"reviews": len(results), "mean_seconds": round(statistics.mean(secs), 1),
                "max_seconds": max(secs),
                "mean_input_tokens": round(statistics.mean(
                    u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
                    + u.get("cache_read_input_tokens", 0) for u in usages)),
                "mean_output_tokens": round(statistics.mean(u.get("output_tokens", 0) for u in usages)),
                "mean_cost_usd": round(statistics.mean(costs), 4) if None not in costs else None,
                "total_cost_usd": round(sum(costs), 4) if None not in costs else None}

    model = next((r["model"] for r in skill_results), next((b["model"] for b in base.values()), ""))
    effort = next((r["effort"] for r in skill_results), "")
    results = {
        "model": model, "effort": effort or "API default", "playbook_version": pb.version(),
        "ndas": len(entries), "skill_runs_per_nda": runs, "missing_runs": missing,
        "skill": {
            **score(skill_pred, gold, topics),
            "invalid_reviews": sum(not r["valid"] for r in skill_results),
            "reviews_needing_repair": sum(r["attempts"] > 1 for r in skill_results),
            "first_drafts_with_quote_or_wording_problem": first_draft_problem,
            "quotes": quote_stats(final_reviews, topics),
            "turnaround": turnaround(skill_results),
            "consistency": consistency(skill_pred, topics),
        },
        "baseline": {
            **score(base_pred, gold, topics),
            "ungraded": sum(not b["grades"] for b in base.values()),
            "quoted_passages": base_q_n, "quoted_passages_verbatim": base_q_ok,
            "turnaround": turnaround(list(base.values()), extra_key="grade_usage"),
        },
        "human": manual_timing(),
    }
    OUT.mkdir(exist_ok=True)
    save(OUT / "results.json", results)
    (OUT / "results.md").write_text(render_md(results, topics), encoding="utf8", newline="\n")
    return results


def pct(x) -> str:
    return "n/a" if x is None else f"{x * 100:.1f}%"


def render_md(res: dict, topics: dict) -> str:
    s, b = res["skill"], res["baseline"]
    q = s["quotes"]
    lines = ["# Evaluation results", "",
             f"Model `{res['model']}`, effort {res['effort']}, playbook {res['playbook_version']}. "
             f"{res['ndas']} synthetic NDAs, skill run {res['skill_runs_per_nda']} times each, baseline once.",
             ""]
    if res["missing_runs"]:
        lines += [f"**Missing runs ({len(res['missing_runs'])}):** " + ", ".join(res["missing_runs"]), ""]
    lines += ["## Accuracy", "",
              "| Measure | Skill | Baseline |", "|---|---|---|",
              f"| Topic decisions scored | {s['decisions']} | {b['decisions']} |",
              f"| Status accuracy | {pct(s['accuracy'])} | {pct(b['accuracy'])} |",
              f"| Accuracy, absent and acceptable treated as one | {pct(s['accuracy_absent_as_acceptable'])} "
              f"| {pct(b['accuracy_absent_as_acceptable'])} |",
              f"| Escalation recall | {pct(s['escalation_recall'])} ({s['escalations_caught']}/{s['escalations_gold']}) "
              f"| {pct(b['escalation_recall'])} ({b['escalations_caught']}/{b['escalations_gold']}) |",
              f"| False escalation rate | {pct(s['false_escalation_rate'])} ({s['false_escalations']}/{s['acceptable_gold']}) "
              f"| {pct(b['false_escalation_rate'])} ({b['false_escalations']}/{b['acceptable_gold']}) |",
              f"| Quote validity | {pct(q['quote_validity'])} ({q['verbatim']}/{q['quotes']}) "
              f"| {b['quoted_passages_verbatim']}/{b['quoted_passages']} quoted passages verbatim |",
              f"| Hallucinations (quotes or wording not traceable) | {q['hallucinations']} | not measured |",
              "",
              f"Skill reviews that failed validation after repairs: {s['invalid_reviews']}. "
              f"Reviews that needed at least one repair round: {s['reviews_needing_repair']}. "
              f"First drafts with a quote or proposed-wording problem caught by the validator: "
              f"{s['first_drafts_with_quote_or_wording_problem']}. "
              f"Quotes in the cited section: {q['in_cited_section']}/{q['quotes']}. "
              f"Proposed language from the playbook: {q['proposed_from_playbook']}/{q['proposed']}.",
              ""]
    if b["ungraded"]:
        lines += [f"Baseline answers the grader could not map: {b['ungraded']}.", ""]

    lines += ["### Accuracy by topic", "", "| # | Topic | Skill | Baseline |", "|---|---|---|---|"]
    for tid, t in topics.items():
        lines.append(f"| {tid} | {t.name} | {pct(s['per_topic_accuracy'][tid])} | {pct(b['per_topic_accuracy'][tid])} |")
    lines.append("")

    lines += ["### Skill confusion (rows gold, columns predicted, all runs)", "",
              "| gold \\ predicted | " + " | ".join(STATUSES) + " | none |",
              "|---" * (len(STATUSES) + 2) + "|"]
    for g in STATUSES:
        row = s["confusion"][g]
        lines.append(f"| {g} | " + " | ".join(str(row.get(p, 0)) for p in (*STATUSES, "none")) + " |")
    lines.append("")

    c = s["consistency"]
    lines += ["## Consistency", "",
              f"Across {res['skill_runs_per_nda']} skill runs, {c['changed']} of {c['topic_decisions']} "
              f"topic decisions ({pct(c['changed_rate'])}) changed status between runs.", ""]
    for d in c["details"]:
        lines.append(f"- {d['file']} topic {d['topic_id']}: {', '.join(d['statuses'])}")
    if c["details"]:
        lines.append("")

    st, bt = s["turnaround"], b["turnaround"]
    lines += ["## Turnaround", "", "| Measure | Skill (per review) | Baseline (per review, incl. grader tokens) |",
              "|---|---|---|"]
    for key, label in (("mean_seconds", "Mean wall-clock seconds"), ("max_seconds", "Max wall-clock seconds"),
                       ("mean_input_tokens", "Mean input tokens"), ("mean_output_tokens", "Mean output tokens"),
                       ("mean_cost_usd", "Mean estimated cost (USD)"), ("total_cost_usd", "Total estimated cost (USD)")):
        lines.append(f"| {label} | {st.get(key, 'n/a')} | {bt.get(key, 'n/a')} |")
    lines += ["", "Skill seconds cover extraction through memo, including any repair calls. "
              "Baseline seconds cover the review call only. Costs use config/rates.json.", ""]

    lines += ["### Human review time (minutes, from data/manual_timing.csv)", "",
              "| File | Manual review | Review of AI output |", "|---|---|---|"]
    rows = [h for h in res["human"] if h["manual"] is not None or h["ai"] is not None]
    for h in rows:
        lines.append(f"| {h['file']} | {h['manual'] if h['manual'] is not None else ''} "
                     f"| {h['ai'] if h['ai'] is not None else ''} |")
    if not rows:
        lines.append("| (none recorded) | | |")
    lines.append("")

    lines += ["## Skill misses (every run)", "", "| File | Run | Topic | Gold | Predicted |", "|---|---|---|---|---|"]
    for m in s["misses"]:
        lines.append(f"| {m['file']} | {m['run']} | {m['topic_id']}. {m['topic_name']} | {m['gold']} | {m['predicted']} |")
    if not s["misses"]:
        lines.append("| (none) | | | | |")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------- CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Evaluate the NDA review skill.")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--estimate", action="store_true", help="estimate calls and cost; no API calls")
    mode.add_argument("--run", action="store_true", help="run missing evaluations, then report")
    mode.add_argument("--report", action="store_true", help="recompute results from cached runs")
    ap.add_argument("--runs", type=int, default=RUNS)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--only", nargs="*", help="limit --run to these files, e.g. nda_01.docx")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf8")

    if args.estimate:
        est = estimate(args.runs)
        model = env.optional("NDA_REVIEW_MODEL")
        c = cost(est["usage"], model) if model else None
        print(f"{est['ndas']} NDAs: about {est['skill_calls']} skill calls (including repairs), "
              f"{est['baseline_calls']} baseline calls, {est['grader_calls']} grader calls.")
        print("Estimated tokens: " + ", ".join(f"{k} {v:,}" for k, v in est["usage"].items()))
        print(f"Model: {model or '(NDA_REVIEW_MODEL not set)'}; effort: "
              f"{env.optional('NDA_REVIEW_EFFORT') or 'API default'}")
        print(f"Estimated cost: {'$%.2f' % c if c is not None else 'no rate for this model in config/rates.json'} "
              "(rough: 4 characters per token, assumed output sizes)")
        return 0

    try:
        load_gold()
        if args.run:
            run_all(args.runs, args.workers, args.only)
        res = report(args.runs)
    except (NotReviewed, env.SettingError) as e:
        print(e)
        return 1
    s = res["skill"]
    print(f"skill: accuracy {pct(s['accuracy'])}, escalation recall {pct(s['escalation_recall'])}, "
          f"false escalation {pct(s['false_escalation_rate'])}, quote validity {pct(s['quotes']['quote_validity'])}")
    print(f"wrote {OUT / 'results.json'} and {OUT / 'results.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
