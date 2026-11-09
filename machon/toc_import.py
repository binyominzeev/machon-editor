"""Sulchán Áruch héber tartalomjegyzék (témacsoportok + szimáncímek) letöltése a Torat Emet oldalról.

    python -m machon.toc_import [--out data/toc.he.json] [--cache data/.toc-cache] [--only eh,cm]
                                [--delay 1.0] [--allow-incomplete]

Csak a csoportoldalak elején lévő tartalomjegyzéket olvassa (a törzsszöveg letöltését a törzs első
horgonyánál megszakítja), a nyers oldalrészleteket a --cache mappában tárolja, így újrafuttatáskor
nem tölt le újra semmit. Csak a standard könyvtárat használja.
"""
import argparse
import codecs
import html
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .ai import VOLUMES

BASE = "https://www.toratemetfreeware.com/online/"
SOURCE_ROOT = BASE + "d_root__040_halacha1.html"
# Kötet -> a "תצוגה משולבת" kötetoldal fájlja (az SA-főoldalon szereplő azonosítók)
VOLUME_PAGES = {"oc": "f_01975", "yd": "f_01976", "eh": "f_01974", "cm": "f_01977"}
USER_AGENT = "machon-editor toc-import (személyes használat)"
HEAD_LIMIT = 2_000_000
BODY_ANCHOR = re.compile(r'<a name="HtmpReportNum\d+_L\d+"', re.I)

INDEX_RE = re.compile(r'AddIndex\("(?P<title>.*?)",\s*"(?P<file>f_\d+_part_\d+\.html)"')
LINK_RE = re.compile(r'<a href="#HtmpReportNum(?P<id>\d+)_L(?P<level>\d+)">(?P<text>.*?)</a>', re.S)
SIMAN_RE = re.compile(r"^סימן\s+(?P<num>[א-ת\"'׳״]+),?(?:\s*\((?P<part>[א-ת])\))?(?:(?:\s*-\s*|\s+)(?P<title>.*))?$", re.S)

GEMATRIA = {c: v for c, v in zip("אבגדהוזחטיכלמנסעפצקרשת",
                                 [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 200, 300, 400])}
GEMATRIA.update({"ך": 20, "ם": 40, "ן": 50, "ף": 80, "ץ": 90})


def fetch_head(url, limit=HEAD_LIMIT):
    """A lap elejét olvassa a törzs első horgonyáig (windows-1255)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    decoder = codecs.getincrementaldecoder("cp1255")(errors="replace")
    text = ""
    with urllib.request.urlopen(req, timeout=60) as r:
        while len(text) < limit:
            chunk = r.read(32768)
            if not chunk:
                break
            text += decoder.decode(chunk)
            m = BODY_ANCHOR.search(text)
            if m:
                return text[:m.start()]
    return text


def cached(url, cache_dir, delay):
    path = cache_dir / (url.rsplit("/", 1)[-1] + ".head")
    if path.exists():
        return path.read_text("utf8")
    text = fetch_head(url)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(text, "utf8")
    time.sleep(delay)
    return text


def clean(s):
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("\xa0", " ").replace("''", '"')
    return re.sub(r"\s+", " ", s).strip()


def hebrew_number(s):
    s = re.sub(r"[\"'׳״]", "", s)
    if not s or any(c not in GEMATRIA for c in s):
        raise ValueError(f"érvénytelen héber szám: {s!r}")
    return sum(GEMATRIA[c] for c in s)


def is_canonical(s):
    vals = [GEMATRIA[c] for c in re.sub(r"[\"'׳״]", "", s)]
    return all(a >= b for a, b in zip(vals, vals[1:]))


def hebrew_range(s):
    """Egy szám, vagy két egymást követő szám összeírva (pl. קסחקסט -> 168, 169)."""
    n = hebrew_number(s)
    if is_canonical(s):
        return n, n
    # A forrás néhány számot szándékosan nem szabályos sorrendben ír (pl. ער = 270), ezért csak akkor
    # keresünk összevont párt, ha egymást követő szabályos két szám adódik.
    plain = re.sub(r"[\"'׳״]", "", s)
    for i in range(1, len(plain)):
        try:
            a, b = hebrew_number(plain[:i]), hebrew_number(plain[i:])
        except ValueError:
            continue
        if b == a + 1:
            return a, b
    return n, n


def parse_groups(page_html):
    """A csoportoldal tartalomjegyzékéből: (csoport címe, szimánok, egyéb fejezetek, problémák).

    Az egyéb fejezetek (pl. "סדר הגט") nem szimánok, ezért nem számítanak a lefedettségbe."""
    group, simanim, extras, problems = None, [], [], []
    for m in LINK_RE.finditer(page_html):
        text, level = clean(m["text"]), int(m["level"])
        if level == 4 and group is None:
            group = text
            continue
        sm = SIMAN_RE.match(text)
        if level == 2 and sm:
            try:
                n, n_to = hebrew_range(sm["num"])
            except ValueError as e:
                problems.append(f"{text!r}: {e}")
                continue
            entry = {"n": n, "n_he": sm["num"].replace("''", '"'), "title_he": (sm["title"] or "").strip()}
            if n_to != n:
                entry["n_to"] = n_to  # a forrás egy sorban vonja össze (pl. קסחקסט = 168-169)
            if sm["part"]:
                entry["part"] = sm["part"]  # ugyanazon szimán további része (pl. רצז (א))
            simanim.append(entry)
        elif level == 2:
            extras.append(text)
    return group, simanim, extras, problems


def import_volume(vol, cache_dir, delay):
    index_url = f"{BASE}{VOLUME_PAGES[vol]}.html"
    index = cached(index_url, cache_dir, delay)
    parts = [(clean(m["title"]), m["file"]) for m in INDEX_RE.finditer(index)]
    if not parts:
        raise RuntimeError(f"{vol}: nem találhatók csoportoldalak a(z) {index_url} oldalon.")
    groups, problems = [], []
    for i, (title, file) in enumerate(parts, 1):
        print(f"[{vol}] {i}/{len(parts)} {file}", file=sys.stderr, flush=True)
        group, simanim, extras, probs = parse_groups(cached(BASE + file, cache_dir, delay))
        problems += [f"{vol} {file}: {p}" for p in probs]
        if not simanim:
            problems.append(f"{vol} {file}: nincs szimán a csoportban ({title!r}).")
        entry = {"title_he": group or title, "source": file, "simanim": simanim}
        if extras:
            entry["extras_he"] = extras
        groups.append(entry)
    return groups, problems


def check_coverage(vol, groups):
    entries = [s for g in groups for s in g["simanim"]]
    nums = [n for s in entries for n in range(s["n"], s.get("n_to", s["n"]) + 1) if "part" not in s]
    expected = set(range(1, VOLUMES[vol][2] + 1))
    problems = []
    dup = sorted({n for n in nums if nums.count(n) > 1})
    if dup:
        problems.append(f"{vol}: többször szereplő szimánok: {dup}")
    if set(nums) - expected:
        problems.append(f"{vol}: tartományon kívüli szimánok: {sorted(set(nums) - expected)}")
    if expected - set(nums):
        problems.append(f"{vol}: hiányzó szimánok: {sorted(expected - set(nums))}")
    if nums != sorted(nums):
        problems.append(f"{vol}: a szimánok sorrendje nem növekvő.")
    orphan = [s["n"] for s in entries if "part" in s and s["n"] not in nums]
    if orphan:
        problems.append(f"{vol}: rész-szimán alap nélkül: {orphan}")
    return problems


def untitled(groups):
    """Cím nélküli szimánok: a forrásban is üres a cím; csak jelentjük, nem találunk ki címet."""
    return [s["n"] for g in groups for s in g["simanim"] if not s["title_he"]]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="data/toc.he.json")
    ap.add_argument("--cache", default="data/.toc-cache")
    ap.add_argument("--only", help="vesszővel elválasztott kötetek (oc,yd,eh,cm); alapból mind")
    ap.add_argument("--delay", type=float, default=1.0, help="másodperc várakozás két új letöltés között")
    ap.add_argument("--allow-incomplete", action="store_true", help="hiányok esetén is mentsen (a jelentés megmarad)")
    args = ap.parse_args(argv)

    vols = args.only.split(",") if args.only else list(VOLUME_PAGES)
    unknown = [v for v in vols if v not in VOLUME_PAGES]
    if unknown:
        ap.error(f"ismeretlen kötet: {unknown}")

    cache_dir = Path(args.cache)
    result, problems = {}, []
    for vol in vols:
        groups, probs = import_volume(vol, cache_dir, args.delay)
        problems += probs + check_coverage(vol, groups)
        result[vol] = {"gate": VOLUMES[vol][0], "groups": groups}
        if untitled(groups):
            print(f"MEGJEGYZÉS: {vol}: a forrásban cím nélküli szimánok: {untitled(groups)}", file=sys.stderr)

    out = {
        "version": 1,
        "source": SOURCE_ROOT,
        "retrieved": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "volumes": result,
    }
    for p in problems:
        print("FIGYELEM:", p, file=sys.stderr)
    if problems and not args.allow_incomplete:
        print(f"{len(problems)} probléma; nem írtam fájlt (--allow-incomplete-tel mégis menthető).", file=sys.stderr)
        return 1
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", "utf8")
    total = sum(len(g["simanim"]) for v in result.values() for g in v["groups"])
    print(f"Kész: {path} ({len(vols)} kötet, {total} szimán).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
