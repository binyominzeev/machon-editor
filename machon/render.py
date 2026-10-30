"""JSON document -> HTML. Kept separate from the server so a PDF generator can reuse the same model."""
import html

from . import markup

GATE_NAMES = {
    "orach_chaim": "Orách Cháim",
    "yore_dea": "Jore Deá",
    "choshen_mishpat": "Chosen Mispát",
    "even_haezer": "Even Háezer",
}


def esc(s):
    return html.escape(s or "", quote=True)


def seif_html(s):
    he = "".join(f'<div class="l">{markup.to_html(l) or "<br>"}</div>' for l in s["hebrew"]) or '<div class="l"><br></div>'
    hu = s["hungarian"]
    items = "".join(
        '<div class="p gap" data-level="1"><br></div>' * int(i.get("gap", 0))
        + f'<div class="p" data-level="{int(i.get("level", 1))}">{markup.to_html(i["text"]) or "<br>"}</div>'
        for i in hu["items"]
    )
    return (
        f'<section class="seif" id="s{s["id"]}" data-seif="{s["id"]}">'
        f'<div class="num" dir="rtl">{esc(s["letter"])}</div>'
        f'<div class="col hu" data-field="hu" lang="hu">'
        f'<div class="edit" tabindex="0"><div class="t">{markup.to_html(hu["title"]) or "<br>"}</div>{items}</div></div>'
        f'<div class="col he" data-field="he" dir="rtl" lang="he"><div class="edit" tabindex="0">{he}</div></div>'
        f"</section>"
    )


def toc_label(s):
    t = markup.to_html(s["hungarian"]["title"])
    return t or '<span class="empty">–</span>'


def doc_html(doc_id, doc):
    toc = "".join(
        f'<a href="#s{s["id"]}" data-target="s{s["id"]}"><span class="tl" dir="rtl">{esc(s["letter"])}</span>'
        f'<span class="tt">{toc_label(s)}</span></a>'
        for s in doc["seifim"]
    )
    gate = GATE_NAMES.get(doc.get("gate"), doc.get("gate", ""))
    t, d = doc["title"], doc["description"]
    head = (
        f'<header class="dochead">'
        f'<div class="meta">{esc(gate)} · {int(doc["siman"])}. szimán</div>'
        f'<div class="hdr">'
        f'<div class="hu"><div class="mf" data-meta="title.hu" contenteditable="true" spellcheck="false">{markup.to_html(t.get("hu", ""))}</div>'
        f'<div class="mf sub" data-meta="description.hu" contenteditable="true">{markup.to_html(d.get("hu", ""))}</div></div>'
        f'<div class="he" dir="rtl"><div class="mf" data-meta="title.he" contenteditable="true" spellcheck="false">{markup.to_html(t.get("he", ""))}</div>'
        f'<div class="mf sub" data-meta="description.he" contenteditable="true" spellcheck="false">{markup.to_html(d.get("he", ""))}</div></div>'
        f"</div></header>"
    )
    body = "".join(seif_html(s) for s in doc["seifim"])
    short = f'{doc.get("siman_he", "")} · {doc["siman"]}'
    return page(f'<main id="doc" data-doc="{esc(doc_id)}">{head}{body}</main>', toc, short, esc(doc_id))


def page(main, toc, title, doc_id):
    return f"""<!doctype html>
<html lang="hu"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#2b3a55">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="icon" href="/static/icon-192.png">
<link rel="apple-touch-icon" href="/static/icon-192.png">
<title>{title} – Machon</title>
<link rel="stylesheet" href="/static/app.css"></head>
<body class="editor">
<div id="bar"><button id="tocBtn" aria-label="Tartalom">☰</button>
<a href="/" class="home">Machon</a><span id="cur"></span><span id="status">✓</span></div>
<nav id="toc" aria-label="Széifek">{toc}</nav>
<div id="scrim"></div>
{main}
<div id="help">Ctrl+B félkövér · Ctrl+I dőlt · Tab/Shift+Tab: szint · Esc: kilép</div>
<script src="/static/app.js"></script></body></html>"""


def index_html(entries):
    rows = "".join(
        f'<li><a href="/d/{esc(i)}"><b>{esc(i)}</b> – {esc(t)}</a></li>' for i, t in entries
    ) or "<li>Nincs dokumentum a docs/ mappában.</li>"
    body = f'<main class="index"><h1>Dokumentumok</h1><ul>{rows}</ul></main>'
    return f"""<!doctype html><html lang="hu"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="manifest" href="/manifest.webmanifest"><link rel="stylesheet" href="/static/app.css">
<title>Machon</title></head><body>{body}<script src="/static/app.js"></script></body></html>"""
