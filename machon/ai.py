"""AI preparation of an empty siman: raw Hebrew (Sefaria) -> OpenAI (prompt.md) -> editor document."""
import html
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# prefix -> (gate key used in the documents, Sefaria book name, number of simanim)
VOLUMES = {
    "oc": ("orach_chaim", "Orach_Chayim", 697),
    "yd": ("yore_dea", "Yoreh_De'ah", 403),
    "eh": ("even_haezer", "Even_HaEzer", 178),
    "cm": ("choshen_mishpat", "Choshen_Mishpat", 427),
}


def load_env():
    p = ROOT / ".env"
    if not p.exists():
        return
    for line in p.read_text("utf8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def gematria(n):
    out = ""
    for v, l in [(400, "ת"), (300, "ש"), (200, "ר"), (100, "ק"), (90, "צ"), (80, "פ"), (70, "ע"), (60, "ס"),
                 (50, "נ"), (40, "מ"), (30, "ל"), (20, "כ"), (10, "י"), (9, "ט"), (8, "ח"), (7, "ז"),
                 (6, "ו"), (5, "ה"), (4, "ד"), (3, "ג"), (2, "ב"), (1, "א")]:
        while n >= v:
            if n in (15, 16):
                return out + ("טו" if n == 15 else "טז")
            out += l
            n -= v
    return out


def _clean(s):
    s = re.sub(r"<i [^>]*></i>", "", s)
    s = re.sub(r"<[^>]+>", "", html.unescape(re.sub(r"<br\s*/?>", "\n", s)))
    s = re.sub(r"[\u0591-\u05C7]", "", s)  # nikud, taamim
    return re.sub(r"[ \t]+", " ", s).strip()


def fetch_raw(vol, n):
    """Title line first, then one line per seif (the format prompt.md expects)."""
    book = VOLUMES[vol][1]
    url = ("https://www.sefaria.org/api/texts/"
           + urllib.parse.quote(f"Shulchan_Arukh,_{book}.{n}", safe="") + "?context=0&lang=he&commentary=0")
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.load(r)
    parts = data.get("he") or []
    if not parts:
        raise RuntimeError("A Sefaria nem adott héber szöveget ehhez a szimánhoz.")
    lines = []
    for i, p in enumerate(parts):
        if i == 0:
            m = re.match(r"\s*<b>(.*?)</b>(.*)", p, re.S)
            if m:
                lines += [_clean(m.group(1)), _clean(m.group(2))]
                continue
        lines.append(_clean(p))
    return "\n".join(l.replace("\n", " ") for l in lines if l)


HEBREW = re.compile(r"[\u0590-\u05FF]")
REMINDER = (
    "\n\nEmlékeztető: a `hu_title` és a `hu[].text` mezők KIZÁRÓLAG magyar nyelvűek, héber betű "
    "(\u05D0-\u05EA) egyetlen magyar mezőben sem szerepelhet: a héber szakszavakat magyar helyesírású "
    "átírásban add meg (pl. *tekiá*). Héber szöveg csak a `hebrew[].lines`, a `title` és a `subtitle` mezőben lehet. "
    "A válasz egyetlen JSON-objektum."
)


def build_messages(n, raw, start=1):
    """The rules and the long example go into the system message; the task is a short, separate user message,
    so the Hebrew-heavy example is not the last thing the model reads."""
    tpl = (ROOT / "prompt.md").read_text("utf8")
    head, sep, task = tpl.partition("## A feladat")
    task = (sep + task).replace("{{SIMAN_SZAM}}", str(n)).replace("{{KEZDO_N}}", str(start)).replace("{{NYERS_SZOVEG}}", raw)
    if not sep:
        return [{"role": "user", "content": task + REMINDER}]
    return [{"role": "system", "content": head.strip()}, {"role": "user", "content": task.strip() + REMINDER}]


def validate(ai, expected):
    """Returns a list of problems (Hungarian, shown to the model on retry)."""
    problems = []
    seifim = ai.get("seifim")
    if not isinstance(seifim, list) or not seifim:
        return ["Hiányzik vagy üres a `seifim` lista."]
    if len(seifim) != expected:
        problems.append(f"{len(seifim)} szeif van, de pontosan {expected} kell (a cím sora utáni sorok száma).")
    for i, s in enumerate(seifim, 1):
        n = s.get("n", i)
        hu = [("hu_title", s.get("hu_title") or "")] + [("hu[].text", it.get("text") or "") for it in s.get("hu") or []]
        if not (s.get("hu_title") or "").strip() or not s.get("hu"):
            problems.append(f"{n}. szeif: hiányzik a magyar cím vagy a magyar pontok.")
        for name, txt in hu:
            if HEBREW.search(txt):
                problems.append(f"{n}. szeif, {name}: héber betű van a magyar szövegben ({txt[:50]!r}). Írd át magyar átírással/fordítással.")
        lines = [l for b in s.get("hebrew") or [] for l in b.get("lines") or []]
        if not lines or not any(HEBREW.search(l) for l in lines):
            problems.append(f"{n}. szeif: a `hebrew` sorokban nincs héber szöveg.")
    return problems


def log(msg):
    print(f"[ai] {msg}", flush=True)


def call_openai(messages, on_chars=None):
    """Streams the completion; on_chars(total_text) is called as chunks arrive."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("Hiányzik az OPENAI_API_KEY (.env fájlban vagy környezeti változóban).")
    model = os.environ.get("OPENAI_MODEL", "gpt-4.1")
    body = {
        "model": model,
        "messages": messages,
        "response_format": {"type": "json_object"},
        "stream": True,
    }
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    log(f"POST {base}/chat/completions model={model} üzenet={sum(len(m['content']) for m in messages)} karakter")
    req = urllib.request.Request(
        base + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    text = ""
    last_log = 0
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            log(f"válasz fejléc: HTTP {r.status}, streamelés indul")
            for raw in r:
                line = raw.decode("utf8").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                choices = json.loads(data).get("choices") or []
                if not choices:
                    continue
                text += choices[0].get("delta", {}).get("content") or ""
                if on_chars:
                    on_chars(text)
                if len(text) - last_log >= 1000:
                    last_log = len(text)
                    log(f"... {len(text)} karakter érkezett")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf8", "replace")[:500]
        log(f"OpenAI HTTP {e.code}: {detail}")
        raise RuntimeError(f"OpenAI hiba {e.code}: {detail}")
    log(f"kész: {len(text)} karakter válasz")
    return text


def _he(s):
    return re.sub(r"\{\{(.*?)\}\}", r"\1", s)


def to_doc(vol, n, ai):
    seifim = []
    for s in ai["seifim"]:
        lines = [_he(l) for b in s.get("hebrew", []) for l in b.get("lines", [])]
        items = [{"level": 2 if it.get("level") == 2 else 1, "text": it.get("text", "")} for it in s.get("hu", [])]
        seifim.append({
            "id": int(s["n"]),
            "letter": gematria(int(s["n"])),
            "hebrew": lines,
            "hungarian": {"title": s.get("hu_title", ""), "items": items},
        })
    doc = {
        "version": 1,
        "gate": VOLUMES[vol][0],
        "siman": n,
        "siman_he": gematria(n),
        "title": {"he": ai.get("title", ""), "hu": ""},
        "description": {"he": ai.get("subtitle", ""), "hu": ""},
        "seifim": seifim,
    }
    if ai.get("flags"):
        doc["ai_flags"] = ai["flags"]
    if ai.get("new_terms"):
        doc["ai_new_terms"] = ai["new_terms"]
    return doc


def generate(vol, n, raw=None, progress=None, only_seif=None):
    """progress(step, pct, message) is optional; only_seif regenerates a single seif (title line + that seif)."""
    progress = progress or (lambda *a: None)
    if (raw or "").strip():
        raw = raw.strip()
        log(f"{vol}-{n}: saját nyers szöveg ({len(raw)} karakter)")
    else:
        progress("fetch", 5, "Héber szöveg letöltése a Sefariáról…")
        log(f"{vol}-{n}: Sefaria letöltés")
        raw = fetch_raw(vol, n)
        log(f"{vol}-{n}: {len(raw.splitlines())} sor, {len(raw)} karakter")
    lines = raw.splitlines()
    if only_seif:
        if not 1 <= only_seif < len(lines):
            raise RuntimeError(f"A nyers szövegben nincs {only_seif}. szeif.")
        raw = lines[0] + "\n" + lines[only_seif]
        lines = raw.splitlines()
    expected = max(1, len(lines) - 1)
    progress("prompt", 15, f"Prompt összeállítva ({expected} szeif).")
    messages = build_messages(n, raw, only_seif or 1)
    attempts = int(os.environ.get("AI_ATTEMPTS", "3"))
    ai = None

    for attempt in range(1, attempts + 1):
        def on_chars(text, attempt=attempt):
            done = min(text.count('"n":'), expected)
            pct = 20 + int(70 * done / expected)
            progress("ai", pct, f"AI dolgozik ({attempt}. próba): {done}/{expected} szeif kész ({len(text)} karakter)")

        progress("ai", 20, f"{attempt}. próba: kérés elküldve, várakozás az AI-ra…")
        text = call_openai(messages, on_chars)
        try:
            ai = json.loads(text)
            problems = validate(ai, expected)
        except ValueError as e:
            log("A válasz nem érvényes JSON; eleje: " + text[:300])
            ai, problems = None, [f"A válasz nem érvényes JSON ({e}). Csak egyetlen, teljes JSON-objektumot adj."]
        if not problems:
            break
        for pr in problems[:15]:
            log(f"{vol}-{n}: ellenőrzés ({attempt}. próba): {pr}")
        if attempt == attempts:
            raise RuntimeError(f"Az AI {attempts} próba után sem adott kifogástalan választ: " + " | ".join(problems[:5]))
        progress("ai", 20, f"{attempt}. próba hibás ({len(problems)} gond), javítás kérése…")
        messages = messages + [
            {"role": "assistant", "content": text},
            {"role": "user", "content": "A válaszod hibás. Javítsd, és add vissza a TELJES JSON-objektumot újra:\n- "
             + "\n- ".join(problems[:20]) + REMINDER},
        ]
    progress("convert", 95, "Dokumentum összeállítása…")
    if only_seif:
        ai["seifim"][0]["n"] = only_seif
    doc = to_doc(vol, n, ai)
    log(f"{vol}-{n}: {len(doc['seifim'])} szeif a dokumentumban, flags={ai.get('flags')}")
    return doc
