# Machon szerkesztő

Sulchán Áruch-fejezetek (szimánok) szerkesztése böngészőből / PWA-ból.

## Futtatás

    pip install flask
    python -m machon.server                # http://<gép-IP>:8000, docs/ mappa
    python -m machon.server --port 8080    # egyedi port
    python -m machon.server --cert c.pem --key k.pem   # HTTPS

Ez a beépített Flask fejlesztői szervere, nem éles környezetre való. Production használathoz
Linuxon telepítsd a Gunicornt, majd indítsd az alkalmazást WSGI szerverként:

    python3 -m venv .venv
    .venv/bin/pip install flask gunicorn
    .venv/bin/gunicorn --bind 0.0.0.0:8080 --workers 1 --threads 4 machon.wsgi:app

Ezek a parancsok a projekt gyökeréből futtatva létrehozzák a `.venv/` könyvtárat, és abba
telepítik a függőségeket. PM2-vel ugyanezt a virtuális környezetet használhatod:

    pm2 start .venv/bin/gunicorn --name machon-editor --interpreter none -- --bind 0.0.0.0:8080 --workers 1 --threads 4 machon.wsgi:app

Ha a PM2-től eltérő felhasználóval fut a szerver, gondoskodj róla, hogy az elérje a projekt
virtuális környezetét és a `docs/` mappát. Internet felől elérhető telepítésnél a Gunicorn elé
tegyél HTTPS-t kezelő reverse proxyt (például Nginxet); a `--cert` és `--key` opciók csak a
beépített fejlesztői szerverhez valók.

A PWA-telepítéshez és a service workerhez a tableten HTTPS (vagy localhost) kell:
pl. `mkcert <gép-IP>` által generált tanúsítvánnyal, vagy Tailscale/`tailscale cert`.
Sima HTTP-n is lehet szerkeszteni, csak telepíthető app / offline gyorsítótár nincs.
A szerver nem kér bejelentkezést: csak megbízható hálózaton futtasd.

## Betűtípusok

A `static/fonts/` mappában részhalmazolt WOFF2 fájlok vannak (David CLM a héberhez, Liberation Serif
a magyarhoz), a `static/app.css` `@font-face` szabályai töltik be, a service worker pedig
előre gyorsítótárazza őket, így telepített fontok nélkül, offline is ugyanúgy jelenik meg.
Licenc: Liberation = SIL OFL, David CLM = GPL-2 + Bitstream (lásd `static/fonts/LICENSE-*.txt`).

## Formátum (`docs/<id>.json`)

    {
      "version": 1,
      "gate": "choshen_mishpat",        // orach_chaim | yore_dea | choshen_mishpat | even_haezer
      "siman": 154, "siman_he": "קנד",
      "title": {"he": "...", "hu": "..."},
      "description": {"he": "...", "hu": "..."},
      "seifim": [{
        "id": 1, "letter": "א",
        "hebrew": ["soronként egy string", "**félkövér** szó"],
        "hungarian": {"title": "Cím", "items": [{"level": 1, "text": "*dőlt* és **félkövér**", "gap": 3}]}
      }]
    }

`gap` (opcionális): ennyi üres sor áll a pont előtt a magyar oszlopban (egy üres sor egy héber sor
magasságú), így a rövid összefoglaló a hosszú héber szöveg megfelelő magasságában folytatódhat.
Szerkesztőben az üres sor = hézag: Enter-rel szúrható be, Backspace-szel törölhető.
A szöveg utáni (utolsó pont alatti) üres sorok nem mentődnek.

Inline jelölés: `**félkövér**`, `*dőlt*`, a `*` és `\` jelek `\`-rel escape-elhetők.
A HTML-t a `machon/render.py` állítja elő (a későbbi PDF-generátor is erre a modellre épülhet).

## Billentyűk szerkesztés közben

Kattintás (vagy fókusz + Enter) a mezőre → szerkesztés. Ctrl/Cmd+B félkövér, Ctrl/Cmd+I dőlt,
Tab / Shift+Tab: vázlatpont szintje (magyar oldal), Esc: kilép. Mentés automatikus
(offline esetén a böngésző sorba állítja, és újra próbálja).

## Import Scribusból

    python -m machon.sla_import cm-154-hu.sla docs/cm-154.json

Mentéskor a korábbi változat `docs/<id>.json.bak` néven megmarad.
