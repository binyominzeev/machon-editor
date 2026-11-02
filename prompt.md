## Feladat

A *Máchon Hásulchán* nevű projektem a Sulchán Áruch egy-egy fejezetét két hasábban jeleníti meg:
**jobb oldalon** a héber alapszöveg, olvasásra szerkesztve (rövid, értelmi egységekre tördelt sorok, félkövér kiemelések),
**bal oldalon** szeifenként rövid magyar összefoglaló.

Kapsz egy siman nyers héber szövegét (OC - Orách Cháim 314. fejezete - az első sor a siman címe, utána soronként egy szeif, a szeifek betűjele nélkül).
A feladatod: ebből előállítani **egyetlen JSON-objektumot** az alább leírt szerkezetben. A JSON-t egy script alakítja Scribus-dokumentummá,
ezért **a kimenet csak a JSON legyen**, előtte-utána semmi szöveg, magyarázat vagy kommentár (a bizonytalanságokat a `flags` mezőbe írd).

## Kimeneti szerkezet

```
{
  "siman_number": 590,                 // a siman száma (egész szám); a héber betűket a script számolja
  "title": "…",                        // a siman címe: az első sor, a záró írásjelek (. :) nélkül, a "ובו N סעיפים" nélkül
  "subtitle": "ובו ט סעיפים",          // a cím második fele, ha van ("ובו … סעיפים"), írásjel nélkül; ha nincs, ""
  "seifim": [
    {
      "n": 1,                          // a szeif sorszáma (a héber betűjelet a script adja hozzá – ne írd a szövegbe!)
      "hebrew": [                      // blokkok sorrendben; a blokk a "kind" szerint főszöveg vagy Remo-glossza
        { "kind": "main", "lines": ["…", "…"] },
        { "kind": "rema", "lines": ["…"] }
      ],
      "hu_title": "…",                 // magyar alcím a szeifhez (félkövérrel jelenik meg)
      "hu": [ { "level": 1, "text": "…" } ]   // magyar felsorolás-pontok
    }
  ],
  "flags": ["…"],                      // amit a szerkesztőnek át kell néznie (lásd lent); ha nincs, []
  "new_terms": [ {"hu": "…", "he": "…"} ]  // a szószedeten kívüli, általad bevezetett átírások; ha nincs, []
}
```

Jelölőnyelv a szövegmezőkben:
- Héber sorokban: `**félkövér**`, és `{{forrásmegjelölés}}` (kis betűs hivatkozás, pl. `{{(מרדכי והג"א פי"ט)}}`).
- Magyar szövegben: `*dőlt*` (és ritkán `**félkövér**`). A hu_title eleve félkövér, abban csak a `*dőlt*` használható.
- A héber rövidítések idézőjele **egyenes `"`** (JSON-ban `\"`), ne használj gersájim/typografikus idézőjelet.
- Ne tegyél a szövegbe más jelölést (nincs HTML, nincs markdown-lista, nincs sortörés a stringeken belül).

## A. Héber szöveg: hűség

1. **A szöveg szó szerint marad**: ne hagyj ki, ne adj hozzá, ne cserélj fel szavakat, a sorrend változatlan. Nikud nincs.
2. A nyers szöveg gyakran **csonkított szavakat** tartalmaz aposztróffal (pl. `תקיע'`, `תרוע'`, `תקיעו'`, `נשימו'`, `בטעו'`, `אפי'`).
   Ezeket **írd ki teljes, szabályos alakra** (`תקיעה`, `תרועה`, `תקיעות`, `נשימות`, `בטעות`, `אפילו`).
3. **Maradnak** a hagyományos rövidítések és betűszámok: `ג"פ`, `ר"ה`, `יוה"כ`, `וי"א`, `תר"ת`, `ג'`, `ב'`, `י"ב`, `ולפי"ז`, `ואח"כ`, `הש"ץ`, `(ב"י)`, `פי"ט`, `א'` (mint szám).
   Kétség esetén: ha az aposztróf számot vagy bevett rövidítést jelöl, hagyd; ha csonkított szót, egészítsd ki. A bizonytalan eseteket tedd a `flags`-be.
4. A szeif végi kettőspont és a mondatközi írásjelek maradnak úgy, ahogy a forrásban vannak. A szeif sorszámát (א, ב, ג…) **ne** írd a szövegbe.
5. Hány `seifim` elem legyen: pontosan annyi, ahány szeif-sor van a nyers szövegben (a cím sora után). Ha a cím szerinti szeifszám ("ובו ט סעיפים") eltér, jelezd a `flags`-ben.

## B. Héber szöveg: sortördelés

A cél a gyors, szinoptikus olvasás: **egy sor = egy értelmi egység**, jobbra zárva, soronként új sor (a script minden elemet külön bekezdésbe tesz).

- Átlagosan **~5 szó / sor** (2–8 szó), **legfeljebb ~38 betű szóközökkel** (14 pontos betűméretnél a hasáb kb. 40 betűt bír; a script figyelmeztet, ha túl hosszú).
  A Remo-blokkok 12 pontosak, ott kicsit hosszabb sor is elfér.
- **Törj a kötőszavak előtt, és a kötőszó kerüljön az új sor elejére**: `או`, `אבל`, `וכן`, `ואם`, `אם`, `לפיכך`, `ומיהו`, `ואחר`, `שאם כן`, `אלא`, `וי"א`, `ויש אומרים`, `שהם`, `דהיינו`.
  Példa: `נסתפק לנו אם היא היללה` / `שאנו קורים תרועה` / `או אם היא מה שאנו קורים שברים` / `או אם הם שניהם יחד` / `לפיכך כדי לצאת ידי ספק`.
- Egymás melletti, párhuzamos esetek (feltétel – következmény; „X is, Y is”) kerüljenek külön sorba.
- Képletek, felsorolások (pl. `תשר"ת ג"פ ותש"ת ג"פ ותר"ת ג"פ:`) lehetőleg egy sorba, ha elférnek.
- Ne hagyj árva egyszavas sort, kivéve ha az egy hangsúlyos kötőszó/ítélet előtt áll.

## C. Héber szöveg: félkövér kiemelés

A félkövér szöveg legyen egy **„csontváz”**: ha valaki csak a félkövér részeket olvassa, követni tudja a szeif logikai ívét. Kb. a szavak **egyharmada** félkövér. Mit emelj ki:
1. A **téma/eset** kulcsszavait („ha X-et tett…”: `תר"ת בנשימה אחת`, `האריך בתקיעה אחרונה`, `תקע בצד הרחב`).
2. A **kötőszavakat és az érvelés csomópontjait**: `או`, `אבל`, `וכן`, `לפיכך`, `אלא`, `שאם כן`, `ומיהו`, `ואם נזכר` stb. – ezek mutatják a szerkezetet.
3. A **véleményeket bevezető kifejezéseket**: `י"א`, `וי"א`, `ויש אומרים`, `ויש מי שאומר`, `וירא שמים`.
4. A **döntést/ítéletet**, ha az a szeif lényege (`אין לחוש`, `לא יצא`, `לא הפסיד`, `הפסיד`, `חוזר`, `אין צריך לחזור`, `לא קיים המצוה`).
5. Maradjon sok sor **teljesen kiemelés nélkül** (kiegészítő magyarázat, ismétlés); ne legyen minden sor félkövér.
A kiemelés mindig összefüggő szavakat fogjon át egy soron belül, a `**` jelek ne maradjanak páratlanul.

## D. Remo-glosszák és források

- A Remo (Móse Isserles) glosszái `"kind": "rema"` blokkba kerülnek (a script 12 pontos betűvel szedi). Ha a szövegben szerepel a `הגה` szó, az a glossza elején marad szövegként.
- A glossza a `הגה`-nál kezdődik, és ált. a szeif végéig tart. **Ha nincs `הגה` jelző**, de a szeif közepén Remo-megjegyzés van, az jellemzően egy
  forrásmegjelölésre (`(מרדכי והג"א…)`, `(ב"י)`, `(טור)` stb.) végződik, és a glossza az előtte lévő „ויש אומרים…”-jellegű résszel kezdődik
  – a példa 3. szeifje ilyen. Az ilyen, jelző nélküli döntéseidet írd a `flags`-be.
- A forrásmegjelölés zárójelestül `{{…}}` közé kerül (pl. `וכן נוהגין {{(מרדכי והג"א פי"ט)}}`), mindig a sor végén.
- Egy szeif több blokkra bomolhat: `main` → `rema` → `main` stb., a forrásszöveg sorrendjében.

## E. Magyar összefoglaló

**Szerkezet.** Minden szeifhez: egy `hu_title` (2–6 szavas főnévi cím, pont nélkül) és **1–4 felsorolási pont** (átlag ~3). Az összes magyar szöveg kb. **fele annyi szó**, mint a héber.
`level` legyen 1; a 2. szint (`"level": 2`) csak ritka alpontra való.

**Stílus.**
- Táviratszerű, tömör, **pont nélkül a végén**; pontonként egyetlen állítás (átlag ~60 karakter, legfeljebb ~110).
- A pontok egymásra épülnek, mint egy mini-érvelés; használj logikai kapcsolókat: *Ezért…, Pedig…, De…, Vagy…, Viszont…*.
- Tartalmilag a *halachát* add vissza: mi a szabály, mi a vita (ki mit mond), mi a következmény (jó-e utólag, újra kell-e kezdeni). Számokat számjeggyel írj (`3 x 3 = 9`).
- **Ne találj ki** a szövegben nem szereplő tartalmat, és **ne hivatkozz a nyers szövegen kívüli forrásra** (Misna Berura, más poszekim) csak akkor, ha biztosan tudod a pontos helyet.
  Bizonytalan hivatkozást inkább hagyj ki, vagy jelezd a `flags`-ben. A hivatkozás formája: `(ld. *Misna Berura* :14)`.
- Magyarul, tegező/neutrális hangon, semmi udvariaskodás vagy magyarázkodás.

**Átírás és dőlt betű.** A héber szakszavakat magyar helyesírással írjuk át a már használt mintára (s = ש, sz = ס, ch = ח/כ, á = kamác, ó = cholem, j = י). **Használd az alábbi bevett alakokat**, új szavaknál ugyanezt a logikát kövesd, és vedd fel őket a `new_terms`-be:

| magyar | héber | | magyar | héber |
|---|---|---|---|---|
| *tekiá* | תקיעה | | *tásrát* | תשר"ת |
| *truá* | תרועה | | *tását* | תש"ת |
| *sevárim* | שברים | | *tárát* | תר"ת |
| *trumitin* | טרומיטין | | *tenáj* | תנאי |
| *sájách* | שייך | | *hefszek* | הפסק |
| *Remo* | הרמ"א | | *Misna Berura* | משנה ברורה |
| sófár (nem dőlt) | שופר | | Muszáf (nem dőlt) | מוסף |
| száfék (nem dőlt) | ספק | | máchloket (nem dőlt) | מחלוקת |

- **Dőlt**: a halachikus szakkifejezések átírása és a művek/szerzők nevei. A **ragot ne dönts** a szó mellé: `*tásrát*nál`, `*tekiá*t`, `*sevárim*ot`.
- **Nem dőlt**: a magyar zsidó köznyelvben bevett kölcsönszavak (sófár, Muszáf, száfék, máchloket, Sulchán Áruch).
- A fejezetben többször előforduló szakszó legyen mindenhol azonos alakú és kezelésű.

## Önellenőrzés a válasz előtt

1. Pontosan egy `seifim` elem van minden nyers szeif-sorra, `n` = 1, 2, 3…, a szeifek betűjele nincs a szövegben.
2. A `**`, `{{`, `}}` jelek párban vannak; a JSON érvényes (a `"` jelek escape-elve); semmi a JSON előtt/után.
3. A héber szöveg a rövidítések kiegészítésén kívül karakterre azonos a forrással.
4. Egyetlen héber sor sem hosszabb ~38 betűnél; a kötőszavak az új sor elején állnak.
5. A félkövér „csontváz” önmagában olvasva értelmes; nem minden sor félkövér.
6. A Remo-blokkok és a forráshivatkozások a helyükön; a bizonytalan döntések a `flags`-ben (rövid, magyar mondatok, a szeif számával: „3. szeif: a Remo-glossza kezdete jelző nélkül”).
7. A magyar pontok tömörek, pont nélküliek, nincs kitalált forrás.

---

## Példa (OC 590, a *Máchon Hásulchán* eddigi kidolgozása)

### Bemenet – nyers szöveg

```
סדר הראוי לתקיעת שופר. ובו ט סעיפים:
כמה תקיעות חייב אדם לשמוע בראש השנה תשע לפי שנאמר תרועה ביובל ובר"ה ג"פ וכל תרועה פשוטה לפניה ופשוטה לאחריה ומפי השמועה למדו שכל תרועות של חודש השביעי אחד הן בין בר"ה בין ביוה"כ של יובל תשע תקיעות תוקעין בכל אחד משניהם תר"ת תר"ת תר"ת: 
תרועה זו האמורה בתורה נסתפק לנו אם היא היללה שאנו קורים תרועה או אם היא מה שאנו קורים שברים או אם הם שניהם יחד לפיכך כדי לצאת ידי ספק צריך לתקוע תשר"ת ג"פ ותש"ת ג"פ ותר"ת ג"פ: 
י"א ששיעור תקיע' כתרוע' ושיעור תרוע' כשלשה יבבות דהיינו ג' כוחות בעלמא כל שהוא והם נקראין טרומיטין ולפי"ז צריך ליזהר שלא יאריך בשבר כשלשה טרומיטין שאם כן יצא מכלל שבר ונעשה תקיעה ויש אומרים דאין לחוש אם האריך בשברים קצת ובלבד שלא יאריך יותר מדאי וכן נוהגין (מרדכי והג"א פי"ט) וצריך להאריך בתקיעה של תשר"ת יותר מבשל תש"ת ובשל תש"ת יותר מבשל תר"ת ומיהו אם מאריך הרבה בכל תקיעה אין לחוש שאין לה שיעור למעלה וכן בתרועה יכול להאריך בה כמו שירצה וכן אם מוסיף על ג' שברים ועושה ד' או ה' אין לחוש וי"א ששיעור יבבא ג' טרומיטין ושיעור תרוע' כשלשה יבבות שהם ט' טרומיטין ושיעור תקיע' גם כן ט' טרומיטין כתרועה ולפי זה אין לחוש אם האריך קצת בשברים וצריך להאריך בתקיע' של תשר"ת כשיעור י"ב טרומיטין ומי שלא האריך בתקיעה כשיעור הזה והאריך בשברים לא קיים המצוה לא כמר ולא כמר: 
ג' שברים צריך לעשותם בנשימה אחת אבל ג' שברים ותרועה דתשר"ת י"א שאינו צריך לעשותם בנשימה אחת והוא שלא ישהא בהפסקה יותר מכדי נשימה וי"א שצריך לעשותם בנשימה אחת וירא שמים יצא ידי כולם ובתקיעו' דמיושב יעשה בנשימה אחת ובתקיעו' דמעומד יעשה בב' נשימו': הגה והמנהג הפשוט לעשות הכל בב' נשימות ואין לשנות: 
אם תקע תר"ת בנשימה אחת יצא ויש מי שאומר שלא יצא: 
אם האריך בתקיעה אחרונה של תשר"ת כשיעור ב' תקיעו' כדי שתעלה לשם תקיעה אחרונה של תשר"ת ובשביל הראשונה של תש"ת לא עלתה לו אלא בשביל תקיעה אחת וי"א שאפי' בשביל אחת לא עלתה לו: הגה ואם תקע תקיעה אחת בין ב' סדרים והתנה שאיזה מן הסדרים הוא הנכון תעלה לו אותה תקיעה יצא (ב"י): 
אם טעה בתשר"ת ואחר שתקע ב' שברים טעה והתחיל להריע אם נזכר מיד יתקע שבר אחר ואם לא נזכר עד שגמר התרועה שהתחיל בה בטעו' לא הפסיד התקיעה הראשונה שתקע אלא חוזר ותוקע ג' שברים ומריע ותוקע אבל אם אירע בתש"ת או תר"ת הפסיד גם תקיעה ראשונה: 
אם הפסיק בתרועה בין תקיעה לשברים או שהפסיק בשברים בין תרועה לתקיעה וכן אם הריע שתי תרועו' זו אחר זו או שתקע אחר התרועה תקיעה כמתעסק שלא לשם תקיעה והפסיק בה בין תרועה לתקיעה או לאחר שתקע ג' שברים שתק והפסיק ואח"כ תקע שברים אחרים ואפי' שבר א' בכל אלו הוי הפסק והפסיד גם תקיעה ראשונה: 
אם תקע שני תשר"ת או שני תש"ת או שני תר"ת כהוגן וטעה בשלישי אין צריך לחזור אלא לאחרון שטעה בו אם תקע בצד הרחב של השופר לא יצא: הגה ואחר שתקעו אומר הש"ץ פסוק אשרי העם יודעי תרועה ואשרי ומחזירין הספר למקומו:
```

### Elvárt kimenet (`siman_number`: 590)

```json
{
 "siman_number": 590,
 "title": "סדר הראוי לתקיעת שופר",
 "subtitle": "ובו ט סעיפים",
 "seifim": [
  {
   "n": 1,
   "hebrew": [
    {
     "kind": "main",
     "lines": [
      "כמה תקיעות חייב אדם",
      "לשמוע בראש השנה",
      "**תשע** לפי שנאמר תרועה **ביובל ובר\"ה ג\"פ**",
      "וכל תרועה **פשוטה לפניה ופשוטה לאחריה**",
      "ומפי השמועה למדו",
      "**שכל** תרועות של חודש השביעי אחד הן",
      "בין בר\"ה בין ביוה\"כ של יובל",
      "תשע תקיעות תוקעין בכל אחד משניהם",
      "תר\"ת תר\"ת תר\"ת:"
     ]
    }
   ],
   "hu_title": "Minimum szükséges fújások, forrásaik",
   "hu": [
    {
     "level": 1,
     "text": "Háromszor említ a Tórában *truát*"
    },
    {
     "level": 1,
     "text": "Mindegyik előtt-után kell egyenes fújás (*tekiá*)"
    },
    {
     "level": 1,
     "text": "Ezért 3 x 3 = 9 fújás kötelező"
    }
   ]
  },
  {
   "n": 2,
   "hebrew": [
    {
     "kind": "main",
     "lines": [
      "**תרועה זו** האמורה בתורה",
      "**נסתפק לנו** אם היא היללה",
      "שאנו קורים **תרועה**",
      "**או** אם היא מה שאנו קורים **שברים**",
      "**או** אם הם **שניהם יחד**",
      "**לפיכך** כדי לצאת ידי ספק",
      "צריך לתקוע",
      "**תשר\"ת** ג\"פ **ותש\"ת** ג\"פ **ותר\"ת** ג\"פ:"
     ]
    }
   ],
   "hu_title": "A háromféle *truá* / száfék",
   "hu": [
    {
     "level": 1,
     "text": "Ami a Tórában *truá*, az nálunk vagy *truá*, vagy *sevárim*, vagy a kettő egymás után"
    },
    {
     "level": 1,
     "text": "E kétség miatt az összes kombinációt fújjuk"
    },
    {
     "level": 1,
     "text": "Innen 30 fújás adódik összesen"
    }
   ]
  },
  {
   "n": 3,
   "hebrew": [
    {
     "kind": "main",
     "lines": [
      "**י\"א** ששיעור תקיעה כתרועה",
      "ושיעור תרועה כשלשה יבבות",
      "**דהיינו** ג' כוחות בעלמא כל שהוא",
      "והם נקראין טרומיטין",
      "**ולפי\"ז צריך ליזהר**",
      "**שלא יאריך** בשבר כשלשה טרומיטין",
      "**שאם כן** יצא מכלל שבר **ונעשה תקיעה**"
     ]
    },
    {
     "kind": "rema",
     "lines": [
      "**ויש אומרים** דאין לחוש אם האריך בשברים קצת",
      "ובלבד שלא יאריך יותר מדאי",
      "וכן נוהגין {{(מרדכי והג\"א פי\"ט)}}"
     ]
    },
    {
     "kind": "main",
     "lines": [
      "**וצריך להאריך בתקיעה**",
      "של **תשר\"ת** יותר מבשל תש\"ת",
      "ובשל **תש\"ת** יותר מבשל תר\"ת",
      "**ומיהו** אם מאריך הרבה בכל תקיעה אין לחוש",
      "**שאין לה שיעור למעלה**",
      "**וכן בתרועה** יכול להאריך בה כמו שירצה",
      "**וכן** אם מוסיף על ג' שברים",
      "ועושה ד' או ה' **אין לחוש**",
      "**וי\"א** ששיעור יבבא ג' טרומיטין",
      "ושיעור תרועה כשלשה יבבות",
      "**שהם** ט' טרומיטין",
      "**ושיעור תקיעה** גם כן ט' טרומיטין כתרועה",
      "**ולפי זה** אין לחוש אם האריך קצת בשברים",
      "**וצריך** להאריך בתקיעה של **תשר\"ת**",
      "כשיעור י\"ב טרומיטין",
      "**ומי שלא האריך** בתקיעה כשיעור הזה",
      "והאריך בשברים",
      "**לא קיים המצוה** לא כמר ולא כמר:"
     ]
    }
   ],
   "hu_title": "A fújások hossza",
   "hu": [
    {
     "level": 1,
     "text": "Két vélemény a legrövidebbről: 3 vagy 9 minimális fújás (*trumitin*)"
    },
    {
     "level": 1,
     "text": "A *tekiá* minimum ilyen hosszú kell, hogy legyen, maximum akármilyen hosszú lehet"
    },
    {
     "level": 1,
     "text": "A *sevárim* viszont nem lehetne olyan hosszú, mint egy *tekiá*"
    },
    {
     "level": 1,
     "text": "Ezért a *tásrát*nál a legfontosabb min. 18 hosszúságú *tekiá* (ld. *Misna Berura* :14)"
    }
   ]
  },
  {
   "n": 4,
   "hebrew": [
    {
     "kind": "main",
     "lines": [
      "ג' שברים צריך לעשותם **בנשימה אחת**",
      "**אבל** ג' שברים ותרועה דתשר\"ת",
      "**י\"א** שאינו צריך לעשותם בנשימה אחת",
      "והוא שלא ישהא בהפסקה **יותר מכדי נשימה**",
      "**וי\"א** שצריך לעשותם בנשימה אחת",
      "**וירא שמים** יצא ידי כולם",
      "ובתקיעות **דמיושב** יעשה **בנשימה אחת**",
      "ובתקיעות **דמעומד** יעשה **בב' נשימות:**"
     ]
    },
    {
     "kind": "rema",
     "lines": [
      "הגה והמנהג הפשוט לעשות **הכל בב' נשימות**",
      "ואין לשנות:"
     ]
    }
   ],
   "hu_title": "Levegővétel fújások között",
   "hu": [
    {
     "level": 1,
     "text": "Vita, hogy a *tásrát*ban a kétféle között vegyünk-e levegőt"
    },
    {
     "level": 1,
     "text": "Először nem (Muszáf előtt), azután igen (Muszáf közben)"
    }
   ]
  },
  {
   "n": 5,
   "hebrew": [
    {
     "kind": "main",
     "lines": [
      "אם תקע **תר\"ת בנשימה אחת** יצא",
      "**ויש מי שאומר** שלא יצא:"
     ]
    }
   ],
   "hu_title": "Mindent egy levegővel",
   "hu": [
    {
     "level": 1,
     "text": "Aki a lehető legrövidebbet (*tárát*) egy levegővel letudta – nem minden vélemény szerint megfelelő"
    }
   ]
  },
  {
   "n": 6,
   "hebrew": [
    {
     "kind": "main",
     "lines": [
      "אם **האריך בתקיעה אחרונה** של תשר\"ת",
      "כשיעור ב' תקיעות",
      "**כדי שתעלה** לשם תקיעה אחרונה של תשר\"ת",
      "**ובשביל הראשונה** של תש\"ת",
      "**לא עלתה לו** אלא בשביל תקיעה אחת",
      "**וי\"א** שאפילו בשביל אחת לא עלתה לו:"
     ]
    },
    {
     "kind": "rema",
     "lines": [
      "הגה **ואם תקע** תקיעה אחת בין ב' סדרים",
      "**והתנה** שאיזה מן הסדרים הוא הנכון",
      "**תעלה לו** אותה תקיעה **יצא**{{ (ב\"י): }}"
     ]
    }
   ],
   "hu_title": "Utolsó-első összevonások",
   "hu": [
    {
     "level": 1,
     "text": "Ha két különböző sorozat utolsó és első *tekiá*ját fújta egybe: máchloket, hogy talán egy sem volt, talán egy volt"
    },
    {
     "level": 1,
     "text": "Pedig ugyanez elvileg megfelelő *tenáj*jal működhetne, hiszen csak száfék miatt fújunk különbözőeket (*Remo*)"
    }
   ]
  },
  {
   "n": 7,
   "hebrew": [
    {
     "kind": "main",
     "lines": [
      "אם טעה **בתשר\"ת**",
      "**ואחר** שתקע **ב' שברים** טעה והתחיל להריע",
      "**אם נזכר** מיד יתקע שבר אחר",
      "**ואם לא נזכר** עד שגמר",
      "התרועה שהתחיל בה בטעות",
      "**לא הפסיד** התקיעה הראשונה שתקע",
      "**אלא חוזר** ותוקע ג' שברים ומריע ותוקע",
      "**אבל** אם אירע **בתש\"ת** או **תר\"ת**",
      "**הפסיד** גם תקיעה ראשונה:"
     ]
    }
   ],
   "hu_title": "Tévesztés: középen rövidebb",
   "hu": [
    {
     "level": 1,
     "text": "Két *sevárim* után *truá*"
    },
    {
     "level": 1,
     "text": "Nem kell ismételnie a nyitó *tekiá*t"
    },
    {
     "level": 1,
     "text": "Mivel *tásrát*ban minden fújás *sájách* (releváns)"
    },
    {
     "level": 1,
     "text": "De *tását*ban vagy *tárát*ban, ha véletlenül oda nem illőt fújt, az *hefszek*, és újrakezdi a sort"
    }
   ]
  },
  {
   "n": 8,
   "hebrew": [
    {
     "kind": "main",
     "lines": [
      "**אם הפסיק** בתרועה בין תקיעה לשברים",
      "**או** שהפסיק בשברים בין תרועה לתקיעה",
      "**וכן** אם הריע שתי תרועות זו אחר זו",
      "**או** שתקע אחר התרועה תקיעה",
      "**כמתעסק** שלא לשם תקיעה",
      "**והפסיק** בה בין תרועה לתקיעה",
      "**או** לאחר שתקע ג' שברים שתק והפסיק",
      "**ואח\"כ** תקע שברים אחרים",
      "**ואפילו** שבר א'",
      "**בכל אלו הוי הפסק**",
      "והפסיד גם תקיעה ראשונה:"
     ]
    }
   ],
   "hu_title": "Megszakítások a fújások közben",
   "hu": [
    {
     "level": 1,
     "text": "Ha *tását*ban *truát* fújt, vagy *tárát*ban *sevárim*ot"
    },
    {
     "level": 1,
     "text": "Vagy túl sokat várt két odaillő között (pl. két sorozatnyi *truá* vagy *sevárim*)"
    },
    {
     "level": 1,
     "text": "Az egész sort kezdje elölről, a *tekiá*tól"
    }
   ]
  },
  {
   "n": 9,
   "hebrew": [
    {
     "kind": "main",
     "lines": [
      "אם תקע שני תשר\"ת או שני תש\"ת",
      "**או** שני תר\"ת כהוגן **וטעה בשלישי**",
      "**אין צריך לחזור** אלא לאחרון שטעה בו",
      "**אם תקע בצד הרחב** של השופר **לא יצא**:"
     ]
    },
    {
     "kind": "rema",
     "lines": [
      "הגה **ואחר** שתקעו אומר הש\"ץ פסוק",
      "**אשרי העם** יודעי תרועה ואשרי",
      "**ומחזירין** הספר למקומו:"
     ]
    }
   ],
   "hu_title": "Csak az utolsó sor javítása",
   "hu": [
    {
     "level": 1,
     "text": "Ha egy három soros egység (pl. *tásrát*) közepén téveszt, akkor a sor elejére ugrik vissza"
    },
    {
     "level": 1,
     "text": "Fordítva nem fújhatja meg a sófárt"
    },
    {
     "level": 1,
     "text": "Sófárfújás utáni imarend (*Remo*)"
    }
   ]
  }
 ],
 "flags": [],
 "new_terms": []
}
```

---

## A feladat

**Siman száma:** `{{SIMAN_SZAM}}`
**Folytatás (ha részletekben dolgozunk):** kezdd a(z) `{{KEZDO_N}}`. szeiffel (alapesetben 1).

**Nyers szöveg:**

```
{{NYERS_SZOVEG}}
```
