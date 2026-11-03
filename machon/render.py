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


AUTH_BAR = '<div id="auth-controls" class="authbar" hidden><span id="auth-status"></span> <button id="login-button" type="button">Belépés</button></div>'
AUTH_SCRIPTS = '<script src="/auth-config.js"></script><script src="/static/auth.js"></script>'


def login_html():
    return f"""<!doctype html><html lang="hu"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#2b3a55"><link rel="stylesheet" href="/static/app.css">
<title>Belépés – Machon</title></head>
<body data-login><main class="home"><h1>Machon szerkesztő</h1>
<p id="auth-status">Bejelentkezés…</p>
<button id="login-button" class="primary" type="button" hidden>Belépés</button></main>
{AUTH_SCRIPTS}</body></html>"""


def seif_html(s, editable=True):
    he = "".join(f'<div class="l">{markup.to_html(l) or "<br>"}</div>' for l in s["hebrew"]) or '<div class="l"><br></div>'
    hu = s["hungarian"]
    items = "".join(
        '<div class="p gap" data-level="1"><br></div>' * int(i.get("gap", 0))
        + f'<div class="p" data-level="{int(i.get("level", 1))}">{markup.to_html(i["text"]) or "<br>"}</div>'
        for i in hu["items"]
    )
    tab = ' tabindex="0"' if editable else ""
    return (
        f'<section class="seif" id="s{s["id"]}" data-seif="{s["id"]}">'
        f'<div class="numwrap"><div class="num" dir="rtl">{esc(s["letter"])}</div>'
        + (f'<button class="regen" data-regen="{s["id"]}" title="Széif újragenerálása AI-val" aria-label="Újragenerálás">↻ Újragenerálás</button>' if editable else "")
        + f'</div>'
        f'<div class="col hu" data-field="hu" lang="hu">'
        f'<div class="edit"{tab}><div class="t">{markup.to_html(hu["title"]) or "<br>"}</div>{items}</div></div>'
        f'<div class="col he" data-field="he" dir="rtl" lang="he"><div class="edit"{tab}>{he}</div></div>'
        f"</section>"
    )


def toc_label(s):
    t = markup.to_html(s["hungarian"]["title"])
    return t or '<span class="empty">–</span>'


def doc_html(doc_id, doc, editable=True):
    toc = "".join(
        f'<a href="#s{s["id"]}" data-target="s{s["id"]}"><span class="tl" dir="rtl">{esc(s["letter"])}</span>'
        f'<span class="tt">{toc_label(s)}</span></a>'
        for s in doc["seifim"]
    )
    gate = GATE_NAMES.get(doc.get("gate"), doc.get("gate", ""))
    t, d = doc["title"], doc["description"]
    ce = 'contenteditable="true"' if editable else ""
    regen_all = ('<button class="regen" data-regen="all" title="Az egész szimán újragenerálása AI-val">↻ Szimán újragenerálása</button>'
                 if editable else "")
    head = (
        f'<header class="dochead">'
        f'<div class="meta"><span>{esc(gate)} · {int(doc["siman"])}. szimán</span>'
        f'{regen_all}</div>'
        f'<div class="hdr">'
        f'<div class="hu"><div class="mf" data-meta="title.hu" {ce} spellcheck="false">{markup.to_html(t.get("hu", ""))}</div>'
        f'<div class="mf sub" data-meta="description.hu" {ce}>{markup.to_html(d.get("hu", ""))}</div></div>'
        f'<div class="he" dir="rtl"><div class="mf" data-meta="title.he" {ce} spellcheck="false">{markup.to_html(t.get("he", ""))}</div>'
        f'<div class="mf sub" data-meta="description.he" {ce} spellcheck="false">{markup.to_html(d.get("he", ""))}</div></div>'
        f"</div></header>"
    )
    body = "".join(seif_html(s, editable) for s in doc["seifim"])
    short = f'{doc.get("siman_he", "")} · {doc["siman"]}'
    ro = "" if editable else " data-readonly"
    return page(f'<main id="doc" data-doc="{esc(doc_id)}"{ro}>{head}{body}</main>', toc, short, esc(doc_id), editable)


def page(main, toc, title, doc_id, editable=True):
    ro_cls = "" if editable else " readonly"
    ro_attr = "" if editable else " data-readonly"
    status = '<span id="status" class="sync-status" role="status" aria-live="polite">…</span>' if editable else ""
    help_box = ('<div id="help">Ctrl+B félkövér · Ctrl+I dőlt · Tab/Shift+Tab: szint · Esc: kilép</div>'
                if editable else "")
    return f"""<!doctype html>
<html lang="hu"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#2b3a55">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="icon" href="/static/icon-192.png">
<link rel="apple-touch-icon" href="/static/icon-192.png">
<title>{title} – Machon</title>
<link rel="stylesheet" href="/static/app.css"></head>
<body class="editor{ro_cls}"{ro_attr}>
<div id="bar"><button id="tocBtn" aria-label="Tartalom">☰</button>
<a href="/" class="home">Machon</a><span id="cur"></span>{status}{AUTH_BAR}</div>
<nav id="toc" aria-label="Széifek">{toc}</nav>
<div id="scrim"></div>
<div id="regenbox" hidden><div class="rmsg"></div><div class="bar"><div id="rfill"></div></div></div>
{main}
{help_box}
{AUTH_SCRIPTS}<script src="/static/app.js"></script></body></html>"""


VOL_LABELS = [("oc", "Orách Cháim"), ("yd", "Jore Deá"), ("eh", "Even Háezer"), ("cm", "Chosen Mispát")]
VOL_SIZES = {"oc": 697, "yd": 403, "eh": 178, "cm": 427}


def _head(title):
    return f"""<!doctype html><html lang="hu"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#2b3a55">
<link rel="manifest" href="/manifest.webmanifest"><link rel="stylesheet" href="/static/app.css">
<title>{esc(title)}</title></head>"""


def index_html(entries, editable=True):
    done = {e["id"]: e for e in entries}
    recent = sorted(entries, key=lambda e: -e["mtime"])[:8]
    label = dict(VOL_LABELS)

    def tile(vol, n, extra=""):
        i = f"{vol}-{n}"
        cls = "tile done" if i in done else "tile"
        if not editable and i not in done:
            return f'<span class="tile off">{n}</span>'
        return f'<a class="{cls}" href="/s/{i}"{extra}>{n}</a>'

    recent_html = "".join(
        f'<a class="rtile" href="/d/{e["id"]}"><span class="rv">{esc(label[e["vol"]])} {e["n"]}</span>'
        f'<span class="rt">{esc(e["title"])}</span></a>'
        for e in recent
    )
    recent_sec = f'<h2>Legutóbb szerkesztett</h2><div class="recent">{recent_html}</div>' if recent else ""
    tabs = "".join(f'<button class="vtab" data-vol="{v}">{esc(l)}</button>' for v, l in VOL_LABELS)
    grids = "".join(
        f'<div class="grid" data-vol="{v}" hidden>{"".join(tile(v, n) for n in range(1, VOL_SIZES[v] + 1))}</div>'
        for v, _ in VOL_LABELS
    )
    ro_attr = "" if editable else " data-readonly"
    script = """<script>
(()=>{const tabs=[...document.querySelectorAll('.vtab')],grids=[...document.querySelectorAll('.grid')];
const show=v=>{tabs.forEach(t=>t.classList.toggle('on',t.dataset.vol===v));grids.forEach(g=>g.hidden=g.dataset.vol!==v);localStorage.setItem('vol',v)};
tabs.forEach(t=>t.onclick=()=>show(t.dataset.vol));show(localStorage.getItem('vol')||'oc');
if('serviceWorker' in navigator)navigator.serviceWorker.register('/sw.js').catch(()=>{});})();
</script>"""
    body = (f'<main class="home"><h1>Machon szerkesztő</h1>{recent_sec}'
            f'<h2>Kötet</h2><div class="vtabs">{tabs}</div><h2>Szimán</h2>{grids}</main>')
    return f"{_head('Machon')}<body{ro_attr}>{body}{AUTH_BAR}{AUTH_SCRIPTS}{script}</body></html>"


def generate_html(doc_id, vol, n, has_key):
    name = dict(VOL_LABELS)[vol]
    warn = "" if has_key else '<p class="warn">Az OPENAI_API_KEY nincs beállítva (.env fájl).</p>'
    body = f"""<main class="home gen"><p><a href="/">← Vissza</a></p>
<h1>{esc(name)} · {n}. szimán</h1>
<p>Ehhez a szimánhoz még nincs szerkesztett anyag.</p>{warn}
<button id="go" class="primary"{"" if has_key else " disabled"}>Előkészítés AI-val (héber tördelés + magyar vázlat)</button>
<details><summary>Saját nyers szöveg megadása (alapból a Sefaria szövege)</summary>
<textarea id="raw" dir="rtl" rows="8" placeholder="Első sor: a siman címe, utána soronként egy szeif"></textarea></details>
<div id="prog" hidden><div class="bar"><div id="fill"></div></div><p id="msg"></p></div></main>
<script>
const $=i=>document.getElementById(i);
const show=j=>{{$('fill').style.width=(j.pct||0)+'%';$('msg').textContent=(j.pct||0)+'% – '+(j.message||'')}};
async function poll(){{
 try{{const j=await (await MachonAuth.fetch('/api/generate/{doc_id}')).json();
  if(j.error){{$('msg').textContent='Hiba: '+j.error;$('msg').className='warn';$('go').disabled=false;return}}
  show(j);if(j.done&&j.url){{location.href=j.url;return}}}}catch(e){{$('msg').textContent='Kapcsolati hiba, újrapróbálom… '+e}}
 setTimeout(poll,1000)}}
$('go').onclick=async()=>{{$('go').disabled=true;$('prog').hidden=false;$('msg').className='';show({{pct:1,message:'Indítás…'}});
 const r=await MachonAuth.fetch('/api/generate/{doc_id}',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{text:$('raw').value}})}});
 if(!r.ok){{$('msg').textContent='Hiba: HTTP '+r.status;$('go').disabled=false;return}}poll()}};
// ha közben már fut egy generálás (pl. oldalfrissítés), folytatjuk a követést
MachonAuth.fetch('/api/generate/{doc_id}').then(r=>r.json()).then(j=>{{if(j.step&&j.step!=='idle'&&!j.done){{$('go').disabled=true;$('prog').hidden=false;poll()}}}});
</script>"""
    return f"{_head(f'{name} {n}')}<body>{body}{AUTH_SCRIPTS}</body></html>"
