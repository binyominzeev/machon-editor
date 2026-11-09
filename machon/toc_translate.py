"""A héber tartalomjegyzék (data/toc.he.json) magyar fordítása OpenAI-jal -> data/toc.hu.json.

    python -m machon.toc_translate [--he data/toc.he.json] [--out data/toc.hu.json] [--batch 40] [--only eh,cm]

Inkrementális: ami már szerepel a kimenetben, azt nem fordítja újra (a kézzel javított
fordítások megmaradnak). Fordítandó: csoportcímek és szimáncímek; csak ezek a rövid címek
kerülnek az AI-szolgáltatóhoz. A .env-ből olvassa az OPENAI_API_KEY-t (lásd machon/ai.py).
Kimenet: {"version":1,"model":...,"groups":{"oc|<csoport héber címe>":"..."},"simanim":{"oc-12":"..."}}
A fordítások AI-val készültek, szakmai átnézést igényelnek.
"""
import argparse
import json
import os
import sys
from pathlib import Path

from . import ai

SYSTEM = (
    "Te a Sulchán Áruch (Joszéf Káro) fejezetcímeinek magyar fordítója vagy. A héber címeket tömören, "
    "természetes magyar nyelven fordítsd (a „דין” = „törvény/szabályok”, „הלכות” = „törvények”). A halachikus "
    "szakszavakat (pl. cicit, tefilin, kidusin, get) magyar helyesírású átírással add meg, kis betűvel, ahol "
    "nem tulajdonnév; az első szó kezdőbetűje nagy. Héber betű a válaszban nem szerepelhet. "
    "A bemenet JSON-objektum: kulcs -> héber cím. Válaszolj egyetlen JSON-objektummal, amelynek "
    "pontosan ugyanezek a kulcsai vannak, értékük a magyar fordítás."
)


def collect(toc, only):
    groups, simanim = {}, {}
    for vol, v in toc["volumes"].items():
        if only and vol not in only:
            continue
        for g in v["groups"]:
            groups[f"{vol}|{g['title_he']}"] = g["title_he"]
            for s in g["simanim"]:
                if s["title_he"]:
                    simanim[siman_key(vol, s)] = s["title_he"]
    return groups, simanim


def siman_key(vol, s):
    return f"{vol}-{s['n']}" + (f"-{s['part']}" if s.get("part") else "")


def translate(items, batch, attempts=3):
    out = {}
    keys = list(items)
    for i in range(0, len(keys), batch):
        part = {k: items[k] for k in keys[i:i + batch]}
        # a kulcsok az AI-nak rövid számok, hogy a hosszú csoportkulcsok ne zavarják
        ids = {str(n): k for n, k in enumerate(part, 1)}
        payload = {n: part[k] for n, k in ids.items()}
        messages = [{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]
        for attempt in range(1, attempts + 1):
            resp = json.loads(ai.call_openai(messages))
            bad = [n for n in payload if not isinstance(resp.get(n), str) or not resp[n].strip()
                   or ai.HEBREW.search(resp[n])]
            if not bad:
                break
            ai.log(f"fordítás: {len(bad)} hibás tétel ({attempt}. próba): {bad[:10]}")
            if attempt == attempts:
                raise RuntimeError(f"A fordítás {attempts} próba után is hibás: {bad[:10]}")
            messages += [{"role": "assistant", "content": json.dumps(resp, ensure_ascii=False)},
                         {"role": "user", "content": f"Hibás vagy hiányzó kulcsok: {bad}. Add vissza a TELJES JSON-t, "
                          "héber betű nélkül, minden kulccsal."}]
        for n, k in ids.items():
            out[k] = resp[n].strip()
        print(f"  {min(i + batch, len(keys))}/{len(keys)}", file=sys.stderr, flush=True)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--he", default="data/toc.he.json")
    ap.add_argument("--out", default="data/toc.hu.json")
    ap.add_argument("--batch", type=int, default=40)
    ap.add_argument("--only")
    args = ap.parse_args(argv)
    ai.load_env()

    toc = json.loads(Path(args.he).read_text("utf8"))
    out_path = Path(args.out)
    hu = (json.loads(out_path.read_text("utf8")) if out_path.exists()
          else {"version": 1, "groups": {}, "simanim": {}})
    hu["model"] = os.environ.get("OPENAI_MODEL", "gpt-4.1")
    groups, simanim = collect(toc, set(args.only.split(",")) if args.only else None)

    for name, items in (("groups", groups), ("simanim", simanim)):
        todo = {k: v for k, v in items.items() if k not in hu[name]}
        print(f"{name}: {len(todo)} fordítandó ({len(items) - len(todo)} már megvan)", file=sys.stderr)
        if todo:
            hu[name].update(translate(todo, args.batch))
            out_path.write_text(json.dumps(hu, ensure_ascii=False, indent=1) + "\n", "utf8")
    print(f"Kész: {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
