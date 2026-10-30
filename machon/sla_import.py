"""One-off importer: Scribus .sla (Hebrew + Hungarian two-column Shulchan Aruch page) -> JSON.

Usage: python -m machon.sla_import cm-154-hu.sla [out.json]
"""
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from . import markup

GATES = {"oc": "orach_chaim", "yd": "yore_dea", "cm": "choshen_mishpat", "eh": "even_haezer"}
LETTERS = {**{c: i for i, c in enumerate("אבגדהוזחט", 1)},
           **{c: 10 * i for i, c in enumerate("יכלמנסעפצ", 1)},
           "ק": 100, "ר": 200, "ש": 300, "ת": 400,
           "ך": 20, "ם": 40, "ן": 50, "ף": 80, "ץ": 90}


def gematria(s):
    s = s.replace('"', "").replace("'", "").replace("״", "").replace("׳", "")
    return sum(LETTERS[c] for c in s) if s and all(c in LETTERS for c in s) else None


def to_gematria(n):
    if n in (15, 16):
        return "טו" if n == 15 else "טז"
    vals = sorted(((v, c) for c, v in LETTERS.items() if c not in "ךםןףץ"), reverse=True)
    out = ""
    for v, c in vals:
        while n >= v:
            out += c
            n -= v
    return out


def clean(t):
    return (t or "").replace("\u00ad", "")


def paragraphs(story):
    """Yield (style_parent, [(text, bold, italic)]) per paragraph."""
    runs = []
    for e in story:
        if e.tag == "ITEXT":
            f = e.get("FONT") or ""
            runs.append((clean(e.get("CH")), "Bold" in f, "Italic" in f))
        elif e.tag == "para":
            yield e.get("PARENT"), runs
            runs = []
    if runs:
        yield None, runs


def plain(runs):
    return "".join(t for t, _, _ in runs)


def lstrip_first(runs):
    return [(runs[0][0].lstrip(), *runs[0][1:])] + runs[1:] if runs else runs


def import_sla(path):
    root = ET.parse(path).getroot().find("DOCUMENT")
    frames = [o for o in root.findall("PAGEOBJECT") if o.get("PTYPE") == "4" and o.find("StoryText") is not None]
    frames.sort(key=lambda o: (int(o.get("OwnPage")), float(o.get("YPOS"))))
    hu, he, head = [], [], []
    for o in frames:
        paras = list(paragraphs(o.find("StoryText")))
        if float(o.get("HEIGHT")) < 200:
            head.append(paras)
        elif float(o.get("XPOS")) < 300:
            hu += paras
        else:
            he += paras

    head_text = [[plain(r).strip() for _, r in p if plain(r).strip()] for p in head]
    siman_he = head_text[0][0].replace("סימן", "").strip()
    title_he = head_text[1][0]
    desc_he = head_text[1][1] if len(head_text[1]) > 1 else ""

    seifim = []

    def split_marker(runs, n):
        """If the paragraph starts with the bold letter of széif n, return the remaining runs."""
        if not runs or not runs[0][1]:
            return None
        parts = runs[0][0].split(None, 1)
        if not parts or parts[0] != to_gematria(n):
            return None
        rest = parts[1] if len(parts) > 1 else ""
        return lstrip_first(([(rest, True, runs[0][2])] if rest else []) + runs[1:])

    cur = None
    for _, runs in he:
        if not plain(runs).strip():
            continue
        rest = split_marker(runs, len(seifim) + 1)
        if rest is not None:
            cur = {"id": len(seifim) + 1, "letter": to_gematria(len(seifim) + 1), "hebrew": [],
                   "hungarian": {"title": "", "items": []}}
            seifim.append(cur)
            runs = rest
        if cur is not None:
            line = markup.serialize(runs).strip()
            if line:
                cur["hebrew"].append(line)

    # Blank paragraphs between bullets become "gap" (number of empty lines before the next item).
    # Blanks right before a széif title only pad the column, so they are dropped.
    idx, gap = -1, 0
    for style, runs in hu:
        if not plain(runs).strip():
            gap += 1
            continue
        rest = split_marker(runs, idx + 2)
        if rest is not None:
            idx += 1
            rest = [(t, False, i) for t, _, i in rest]
            seifim[idx]["hungarian"]["title"] = markup.serialize(rest).strip()
        elif idx >= 0:
            item = {"level": 2 if style == "lista2" else 1, "text": markup.serialize(runs).strip()}
            if gap:
                item["gap"] = gap
            seifim[idx]["hungarian"]["items"].append(item)
        gap = 0

    prefix = Path(path).stem.split("-")
    return {
        "version": 1,
        "gate": GATES.get(prefix[0], "choshen_mishpat"),
        "siman": gematria(siman_he) or int(prefix[1]),
        "siman_he": siman_he,
        "title": {"he": title_he, "hu": ""},
        "description": {"he": desc_he, "hu": ""},
        "seifim": seifim,
    }


if __name__ == "__main__":
    doc = import_sla(sys.argv[1])
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(f"{len(doc['seifim'])} széif, siman {doc['siman']}", file=sys.stderr)
