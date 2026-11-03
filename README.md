# Machon szerkesztő

Sulchán Áruch-fejezetek (szimánok) szerkesztése böngészőből / PWA-ból.

## Futtatás

Első használat előtt hozz létre egy virtuális környezetet, és telepítsd bele a projekt
függőségeit:

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt

Windows PowerShellben az aktiválás parancsa:

    .venv\Scripts\Activate.ps1

Az aktivált környezetben a fejlesztői szerver és az importáló is ugyanazt a Python-környezetet
használja:

    python -m machon.server                # http://<gép-IP>:8000, docs/ mappa
    python -m machon.server --port 8080    # egyedi port
    python -m machon.server --cert c.pem --key k.pem   # HTTPS

Ez a beépített Flask fejlesztői szervere, nem éles környezetre való. Production használathoz
Linuxon indítsd az alkalmazást WSGI szerverként a telepített Gunicornnal:

    gunicorn --bind 0.0.0.0:8080 --workers 1 --threads 4 machon.wsgi:app

PM2-vel ugyanezt a virtuális környezetet használhatod:

    pm2 start .venv/bin/gunicorn --name machon-editor --interpreter none -- --bind 0.0.0.0:8080 --workers 1 --threads 4 machon.wsgi:app

Az aktivált környezetből kilépni a `deactivate` paranccsal lehet. Új függőség esetén add hozzá a
`requirements.txt`-hez, majd futtasd újra a `python -m pip install -r requirements.txt`
parancsot; ne telepíts csomagot külön a rendszer-Pythonba. A `.venv/` helyi, nem verziókezelt
könyvtár. Ha újra kell építeni, töröld ezt a könyvtárat, majd futtasd újra a fenti létrehozási
és telepítési parancsokat.

Ha a PM2-től eltérő felhasználóval fut a szerver, gondoskodj róla, hogy az elérje a projekt
virtuális környezetét és a `docs/` mappát. Internet felől elérhető telepítésnél a Gunicorn elé
tegyél HTTPS-t kezelő reverse proxyt (például Nginxet); a `--cert` és `--key` opciók csak a
beépített fejlesztői szerverhez valók.

A PWA-telepítéshez és a service workerhez a tableten HTTPS (vagy localhost) kell:
pl. `mkcert <gép-IP>` által generált tanúsítvánnyal, vagy Tailscale/`tailscale cert`.
Sima HTTP-n is lehet szerkeszteni, csak telepíthető app / offline gyorsítótár nincs.
Bejelentkezés nélkül (alapállapot) a szerver nem kér azonosítást: ilyenkor csak megbízható hálózaton futtasd; internet felé a lenti Pocket ID bejelentkezést kapcsold be.

## Bejelentkezés (Pocket ID / OIDC)

Opcionális: ha a `.env`-ben az `OIDC_ISSUER` be van állítva, a szerkesztés bejelentkezéshez kötött (Pocket ID, Authorization Code + PKCE). Aki be tud lépni,
mindenki ugyanazokat a dokumentumokat látja és szerkesztheti (nincs felhasználónkénti adat).
Bejelentkezés nélkül a meglévő szimánok csak olvasható módban, a szerkesztővel azonos
kinézettel megnyithatók (nincs szerkesztés, újragenerálás, AI-előkészítés; az új szimán csempék
inaktívak). Az írási API-k (PUT/POST) és az `/s/<új szimán>` oldal belépést kér. Ha az
`OIDC_ISSUER` üres vagy hiányzik, a hitelesítés ki van kapcsolva.

1. Pocket ID adminban hozz létre egy OIDC klienst. A **Redirect URI** pontosan `https://<domain>/`
   legyen (záró perjellel, ugyanaz a séma és host, mint amin az app elérhető). Jegyezd fel a
   Client ID-t és a Client Secretet.
2. Add meg a `.env` fájlban (lásd `.env.example`):

       OIDC_ISSUER=https://auth.example.com
       OIDC_CLIENT_ID=...
       OIDC_CLIENT_SECRET=...          # csak a szerver ismeri, a böngészőbe nem kerül
       OIDC_REDIRECT_URI=https://<domain>/   # karakterre egyezzen a Pocket ID-ban megadottal
       # OIDC_AUDIENCE=...             # opcionális `aud` ellenőrzés

3. Az OIDC-hez szükséges csomagok már a `requirements.txt`-ben vannak; ellenőrizd, hogy
   telepítetted őket az aktív virtuális környezetbe (`python -m pip install -r requirements.txt`).
4. Indítsd újra a szervert. A bejelentkezéshez HTTPS (vagy localhost) ajánlott, reverse proxy mögött.

Működés: a böngésző PKCE-vel a Pocket ID-hoz irányít, a `code`→token cserét és a refresh-t a
szerver `/api/auth/token` és `/api/auth/refresh` végpontja végzi (itt adódik hozzá a
`client_secret`; a Pocket ID token endpointja `/api/oidc/token`). Az `/api/*` hívások
`Authorization: Bearer` fejlécet kapnak, amit a szerver a Pocket ID JWKS-e alapján ellenőriz;
az oldalak betöltését ugyanennek az access tokennek a `machon_at` sütije védi (`static/auth.js`
állítja be). Bejelentkezés nélkül egy belépőoldal jelenik meg. A refresh token a böngésző
`localStorage`-ában van (egyszerű, dokumentált kompromisszum). Lejáratkor a token magától
megújul; sikertelen megújításnál kijelentkeztet.

Hibakeresés: token cserénél 400 → a `redirect_uri` nem egyezik pontosan; nincs refresh token →
a Pocket ID kliensnél engedélyezett-e az `offline_access`; naplók: a szerver stdout-ján `[auth] …`
sorok (PM2 naplóba kerülnek).

## Nyitóképernyő és AI-előkészítés

A kezdőlap a 4 kötet szimán-csempéit mutatja (a már létező dokumentumok kiemelve), fent a
legutóbb szerkesztettekkel. Dokumentum-azonosító: `oc-590`, `yd-…`, `eh-…`, `cm-154`.
Új szimánnál az „Előkészítés AI-val” gomb a Sefaria héber szövegéből és a `prompt.md`-ből az
OpenAI API-val létrehozza a kezdeti tördelést és magyar vázlatot. Kell hozzá egy `.env` fájl
(lásd `.env.example`): `OPENAI_API_KEY=…`, opcionálisan `OPENAI_MODEL` (alapértelmezett: gpt-4.1).

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

Az offline szerkesztéshez előbb online nyisd meg a dokumentumot, hogy a böngésző eltárolhassa
az oldalát és a szükséges fájlokat. A módosított mezők helyi másolata és a feltöltésre váró
mentések automatikusan megmaradnak; kapcsolat nélkül is szerkeszthetsz, visszatéréskor pedig
automatikusan szinkronizálódnak. A fejléc diszkrét állapotjelzése mutatja a kapcsolatot és a
mentést. Bejelentkezéses módban a helyi piszkozatok felhasználónként elkülönülnek. Ha a szerver
ütközésre utaló HTTP 409/412 választ ad, a kliens jelzi a lehetséges ütközést, de annak feloldása
egyelőre kézi feladat.

## Import Scribusból

    python -m machon.sla_import cm-154-hu.sla docs/cm-154.json

Az importálót is az aktivált `.venv`-ből futtasd.
Mentéskor a korábbi változat `docs/<id>.json.bak` néven megmarad.
