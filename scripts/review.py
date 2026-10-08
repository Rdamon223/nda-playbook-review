"""Review one NDA against the playbook with the Claude API, then write the review JSON and memo.

    python scripts/review.py data/synthetic_ndas/nda_01.docx [--company "Fernhollow Analytics LLC"] [--out-dir outputs]

This is the skill workflow run outside Claude Code. The script does the mechanical steps itself
(extract the text, validate, write the memo) and asks the model for the judgment steps (segment,
compare, classify, quote, propose). The model gets SKILL.md, the playbook, and schema.json as its
instructions. Every reply is checked by finalize.check: schema rules, playbook rules, and the
deterministic quote check. If the check fails, the problems go back to the model and it tries again,
up to MAX_REPAIRS times, just as the skill tells Claude to fix the JSON and rerun finalize.py.

Settings (environment or .env, see env.py):
    ANTHROPIC_API_KEY   required
    NDA_REVIEW_MODEL    required, no default
    NDA_REVIEW_EFFORT   optional: low, medium, high, or max. Unset means the API default.

The company the review is done for comes from --company, or from data/seeded_deviations.json for the
synthetic NDAs. The script will not guess it.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env  # noqa: E402
import extract_text  # noqa: E402
import finalize  # noqa: E402
import memo  # noqa: E402
import playbook as pb  # noqa: E402
import schema  # noqa: E402

SKILL_DIR = pb.ROOT / ".claude" / "skills" / "nda-review"
MANIFEST = pb.ROOT / "data" / "seeded_deviations.json"
MAX_REPAIRS = 2
MAX_TOKENS = 32000
EFFORTS = ("low", "medium", "high", "max")

API_NOTE = """You are running the nda-review skill below through the API, not inside Claude Code.
What changes:
- Step 0: the Company is named in the user message.
- Step 1: the extraction has been done for you. The numbered text is in the user message.
- Step 8: reply with the review JSON object only, no other text and no code fence. The caller
  validates it and writes the memo. If the caller sends back problems, reply with the full
  corrected JSON object.
Everything else in the skill applies exactly as written."""


def system_prompt() -> str:
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf8")
    playbook_text = (SKILL_DIR / "playbook.md").read_text(encoding="utf8")
    schema_json = (SKILL_DIR / "schema.json").read_text(encoding="utf8")
    return (f"{API_NOTE}\n\n<skill>\n{skill}\n</skill>\n\n<playbook>\n{playbook_text}\n</playbook>\n\n"
            f"<schema>\n{schema_json}\n</schema>")


def user_prompt(source_file: str, company: str, numbered: str) -> str:
    return (f"Review this NDA. You act for the Company: {company}.\n"
            f"source_file: {source_file}\n\n<nda>\n{numbered}\n</nda>")


def company_from_manifest(path: Path) -> str:
    if not MANIFEST.exists():
        return ""
    for e in json.loads(MANIFEST.read_text(encoding="utf8"))["ndas"]:
        if e["file"] == path.name:
            return e["company"]
    return ""


def settings() -> dict:
    env.require("ANTHROPIC_API_KEY")  # checked here so the error is clear; the SDK reads it itself
    effort = env.optional("NDA_REVIEW_EFFORT").lower()
    if effort and effort not in EFFORTS:
        raise env.SettingError(f"NDA_REVIEW_EFFORT must be one of {', '.join(EFFORTS)}")
    return {"model": env.require("NDA_REVIEW_MODEL"), "effort": effort}


def make_client():
    import anthropic

    env.load_dotenv()
    return anthropic.Anthropic(max_retries=4)


def call_model(client, model: str, effort: str, system: str, messages: list, max_tokens: int = MAX_TOKENS):
    """One Messages API call. Returns (reply text, assistant content to send back, usage dict)."""
    kwargs = {"model": model, "max_tokens": max_tokens, "messages": messages}
    if system:
        kwargs["system"] = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
    if effort:
        kwargs["thinking"] = {"type": "adaptive"}
        kwargs["output_config"] = {"effort": effort}
    with client.messages.stream(**kwargs) as stream:
        msg = stream.get_final_message()
    text = "".join(b.text for b in msg.content if b.type == "text")
    u = msg.usage
    usage = {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
             "cache_creation_input_tokens": u.cache_creation_input_tokens or 0,
             "cache_read_input_tokens": u.cache_read_input_tokens or 0}
    return text, msg.content, usage


def add_usage(total: dict, usage: dict) -> None:
    for k, v in usage.items():
        total[k] = total.get(k, 0) + v


def parse_json(text: str) -> dict | None:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(pb.ROOT).as_posix()
    except ValueError:
        return path.name


def review(path: Path, company: str, *, client=None, model: str, effort: str = "",
           topics: dict | None = None) -> dict:
    """Run the review. Returns a result dict; result['review'] is the final JSON (valid or not)."""
    t0 = time.perf_counter()
    topics = topics or pb.parse()
    client = client or make_client()
    entries = extract_text.extract(path)
    source_file = rel(path)
    system = system_prompt()
    messages = [{"role": "user", "content": user_prompt(source_file, company, extract_text.format_numbered(entries))}]
    usage: dict = {}
    attempts, first_problems, data, problems, text = 0, None, None, [], ""

    while attempts <= MAX_REPAIRS:
        attempts += 1
        text, content, u = call_model(client, model, effort, system, messages)
        add_usage(usage, u)
        data = parse_json(text)
        if data is None:
            problems = ["reply was not a JSON object"]
        else:
            data.update({"source_file": source_file, "company": company,
                         "playbook_version": pb.version(), "model": model})
            problems = finalize.check(data, path, topics)
        if first_problems is None:
            first_problems = problems
        if not problems:
            break
        messages += [{"role": "assistant", "content": content},
                     {"role": "user", "content": "The validator found these problems. Fix them and reply "
                                                 "with the full corrected JSON object only:\n"
                                                 + "\n".join(f"- {p}" for p in problems)}]

    result = {"file": path.name, "company": company, "model": model, "effort": effort,
              "valid": not problems, "problems": problems, "first_attempt_problems": first_problems,
              "attempts": attempts, "usage": usage, "review": data,
              "raw_reply": None if data is not None else text}
    if not problems:
        result["memo"] = memo.render(data, topics)
    result["seconds"] = round(time.perf_counter() - t0, 1)
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Review one NDA against the playbook with the Claude API.")
    ap.add_argument("nda", type=Path)
    ap.add_argument("--company", help="the party the review is for (default: from the synthetic manifest)")
    ap.add_argument("--out-dir", type=Path, default=pb.ROOT / "outputs")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf8")

    if not args.nda.exists():
        print(f"NDA not found: {args.nda}")
        return 1
    company = args.company or company_from_manifest(args.nda)
    if not company:
        print("Say which party the review is for: --company \"Name as it appears in the NDA\"")
        return 1
    try:
        s = settings()
    except env.SettingError as e:
        print(e)
        return 1

    result = review(args.nda, company, model=s["model"], effort=s["effort"])
    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = args.nda.stem
    u = result["usage"]
    print(f"{result['attempts']} call(s), {result['seconds']} s, "
          f"{u.get('input_tokens', 0) + u.get('cache_read_input_tokens', 0) + u.get('cache_creation_input_tokens', 0)} "
          f"input tokens, {u.get('output_tokens', 0)} output tokens")
    if not result["valid"]:
        bad = args.out_dir / f"{stem}.invalid.json"
        bad.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf8", newline="\n")
        print(f"review did not validate after {result['attempts']} attempt(s); details in {bad}")
        for p in result["problems"]:
            print(f"  - {p}")
        return 1
    out_json = args.out_dir / f"{stem}.json"
    out_json.write_text(json.dumps(result["review"], indent=2, ensure_ascii=False) + "\n",
                        encoding="utf8", newline="\n")
    out_md = out_json.with_suffix(".md")
    out_md.write_text(result["memo"], encoding="utf8", newline="\n")
    print(f"valid; wrote {out_json} and {out_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
