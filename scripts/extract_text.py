"""Extract clean, section-numbered text from an NDA (.docx or .pdf).

    python scripts/extract_text.py data/synthetic_ndas/nda_01.docx [--json] [-o out.txt]

Each paragraph becomes one entry {"ref": "3.2", "text": "..."}. The text is the paragraph exactly as
written (numbering included), with runs of whitespace collapsed. The ref is the section number the
paragraph belongs to, so a finding can cite it. Paragraphs before the first numbered section get the
ref "Preamble"; unnumbered paragraphs inherit the ref of the section they sit in.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROMAN_RE = r"[IVXLC]+"
SECTION_WORD_RE = re.compile(rf"^(?:Section|SECTION|Article|ARTICLE|Clause|CLAUSE)\s+(\d+(?:\.\d+)*|{ROMAN_RE})\b\.?")
# "3." / "3)" / "3.2" / "3.2." starts a section; a bare "30 days" does not
NUMBER_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,2})+\.?|\d{1,2}[.)])\s+(?=\S)")
SUB_RE = re.compile(r"^\(([a-z]{1,2}|[ivx]+)\)\s+")
PAGE_NOISE_RE = re.compile(r"^(?:Page\s+\d+(?:\s+of\s+\d+)?|\d+|-\s*\d+\s*-)$", re.I)


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace(" ", " ")).strip()


def _docx_paragraphs(path: Path) -> list[tuple[str, tuple | None]]:
    """(text, auto_number) in document order, including table cells.

    auto_number is (numId, ilvl) for Word auto-numbered paragraphs, whose numbers are not in the text.
    """
    import docx
    from docx.oxml.ns import qn

    d = docx.Document(str(path))
    out = []

    def para(p_el):
        text = "".join(t.text or "" for t in p_el.iter(qn("w:t")))
        num = None
        ppr = p_el.find(qn("w:pPr"))
        if ppr is not None:
            numpr = ppr.find(qn("w:numPr"))
            if numpr is not None:
                nid, lvl = numpr.find(qn("w:numId")), numpr.find(qn("w:ilvl"))
                num = (nid.get(qn("w:val")) if nid is not None else "0",
                       int(lvl.get(qn("w:val"))) if lvl is not None else 0)
        out.append((text, num))

    for el in d.element.body.iterchildren():
        if el.tag == qn("w:p"):
            para(el)
        elif el.tag == qn("w:tbl"):
            for p_el in el.iter(qn("w:p")):
                para(p_el)
    return out


def _pdf_paragraphs(path: Path) -> list[tuple[str, None]]:
    import pdfplumber

    paras, cur = [], []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            for line in (page.extract_text() or "").splitlines():
                line = line.strip()
                if not line:
                    if cur:
                        paras.append(" ".join(cur))
                        cur = []
                    continue
                if PAGE_NOISE_RE.match(line):
                    continue
                starts_new = bool(SECTION_WORD_RE.match(line) or NUMBER_RE.match(line) or SUB_RE.match(line))
                if starts_new and cur:
                    paras.append(" ".join(cur))
                    cur = []
                cur.append(line)
    if cur:
        paras.append(" ".join(cur))
    return [(p, None) for p in paras]


def number_paragraphs(raw: list[tuple[str, tuple | None]]) -> list[dict]:
    entries = []
    section = "Preamble"          # last top-level or dotted section number
    sub_ref = None                # last (a)-style sub-clause under it
    counters: dict[str, list[int]] = {}

    for text, auto in raw:
        text = clean(text)
        if not text:
            continue
        m = SECTION_WORD_RE.match(text) or NUMBER_RE.match(text)
        s = SUB_RE.match(text)
        if m:
            section, sub_ref = m.group(1).rstrip(".)"), None
            ref = section
        elif s:
            label = s.group(1)
            is_roman = re.fullmatch(r"[ivx]+", label) and not (label == "i" and sub_ref and sub_ref.endswith("(h)"))
            if is_roman and sub_ref:
                ref = f"{sub_ref}({label})"
            else:
                sub_ref = f"{section}({label})"
                ref = sub_ref
        elif auto is not None:
            nid, lvl = auto
            c = counters.setdefault(nid, [0] * 9)
            c[lvl] += 1
            for deeper in range(lvl + 1, 9):
                c[deeper] = 0
            section, sub_ref = ".".join(str(n) for n in c[: lvl + 1] if n), None
            ref = section
        else:
            ref = sub_ref or section
        entries.append({"ref": ref, "text": text})
    return entries


def extract(path: str | Path) -> list[dict]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".docx":
        raw = _docx_paragraphs(path)
    elif suffix == ".pdf":
        raw = _pdf_paragraphs(path)
    elif suffix in (".txt", ".md"):
        raw = [(p, None) for p in re.split(r"\n\s*\n|\n(?=\s*(?:\d+\.|\(|Section|Article))", path.read_text(encoding="utf8"))]
    else:
        raise ValueError(f"unsupported file type: {path.suffix}")
    return number_paragraphs(raw)


def full_text(entries: list[dict]) -> str:
    return "\n".join(e["text"] for e in entries)


def format_numbered(entries: list[dict]) -> str:
    return "\n".join(f"[{e['ref']}] {e['text']}" for e in entries)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Extract numbered text from an NDA.")
    ap.add_argument("file", type=Path)
    ap.add_argument("--json", action="store_true", help="print entries as JSON")
    ap.add_argument("-o", "--output", type=Path)
    args = ap.parse_args(argv)
    entries = extract(args.file)
    out = json.dumps(entries, indent=2, ensure_ascii=False) if args.json else format_numbered(entries)
    if args.output:
        args.output.write_text(out + "\n", encoding="utf8")
    else:
        sys.stdout.reconfigure(encoding="utf8")
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
