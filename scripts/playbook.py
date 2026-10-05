"""Parse playbooks/mutual-nda-playbook.md into structured topics.

The markdown file is the single source of truth. Every script that needs playbook content
(review prompts, proposed-language checks, the memo) reads it through this module.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAYBOOK = ROOT / "playbooks" / "mutual-nda-playbook.md"

TOPIC_RE = re.compile(r"^## (\d+)\. (.+)$", re.M)


@dataclass
class Topic:
    id: int
    name: str
    severity: str
    preferred: str
    fallback_intro: list[str] = field(default_factory=list)
    fallback_wording: list[str] = field(default_factory=list)
    escalate_if: list[str] = field(default_factory=list)
    if_absent: str = "escalate"       # "escalate" or "absent"
    if_absent_note: str = ""
    body: str = ""                    # the topic's full markdown, for prompts


def _strip_outer_quotes(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        return text[1:-1]
    return text


def version(path: Path = PLAYBOOK) -> str:
    """The playbook's version label from its banner, e.g. "Version 1"."""
    m = re.search(r"\*\*(Version [^,*]+)", path.read_text(encoding="utf8"))
    return m.group(1).strip() if m else ""


def parse(path: Path = PLAYBOOK) -> dict[int, Topic]:
    text = path.read_text(encoding="utf8")
    heads = list(TOPIC_RE.finditer(text))
    topics: dict[int, Topic] = {}
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = text[h.end():end]
        body = body.split("\n---")[0].strip()  # topic sections end at a horizontal rule

        sev = re.search(r"\*\*Severity:\*\*\s*(\w+)", body)
        pref = re.search(r"\*\*Preferred position\.\*\*\s*(.+)", body)
        absent = re.search(r"\*\*If absent:\*\*\s*(.+)", body)

        fb_block = re.search(r"\*\*Acceptable fallback\.\*\*(.*?)(?=\*\*Escalate if:\*\*)", body, re.S)
        intro, wording = [], []
        if fb_block:
            for para in re.split(r"\n\s*\n", fb_block.group(1).strip()):
                lines = para.strip().splitlines()
                if lines and all(l.startswith(">") for l in lines):
                    wording.append(_strip_outer_quotes(" ".join(l.lstrip("> ").strip() for l in lines)))
                elif para.strip():
                    intro.append(para.strip())

        esc_block = re.search(r"\*\*Escalate if:\*\*(.*?)(?=\*\*If absent:\*\*)", body, re.S)
        escalate = [m.group(1).strip() for m in re.finditer(r"^- (.+)$", esc_block.group(1), re.M)] if esc_block else []

        absent_text = absent.group(1).strip() if absent else "escalate"
        topics[int(h.group(1))] = Topic(
            id=int(h.group(1)),
            name=h.group(2).strip(),
            severity=sev.group(1).lower() if sev else "",
            preferred=pref.group(1).strip() if pref else "",
            fallback_intro=intro,
            fallback_wording=wording,
            escalate_if=escalate,
            if_absent="absent" if absent_text.lower().startswith("report") else "escalate",
            if_absent_note=absent_text,
            body=body,
        )
    return topics
