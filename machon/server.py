"""Machon editor server.

    python -m machon.server [--host 0.0.0.0] [--port 8000] [--docs docs] [--cert c.pem --key k.pem]
"""
import argparse
import json
import os
import re
import threading
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory

from . import markup, render

ROOT = Path(__file__).resolve().parent.parent
ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
lock = threading.Lock()


def create_app(docs_dir):
    docs_dir = Path(docs_dir)
    app = Flask(__name__, static_folder=str(ROOT / "static"), static_url_path="/static")

    def path(doc_id):
        if not ID_RE.match(doc_id):
            abort(404)
        return docs_dir / f"{doc_id}.json"

    def load(doc_id):
        p = path(doc_id)
        if not p.exists():
            abort(404)
        return json.loads(p.read_text("utf8"))

    def save(doc_id, doc):
        p = path(doc_id)
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", "utf8")
        if p.exists():
            os.replace(p, p.with_suffix(".json.bak"))
        os.replace(tmp, p)

    def runs_to_markup(runs):
        return markup.serialize([(str(t), bool(b), bool(i)) for t, b, i in runs])

    def item(it):
        out = {"level": 2 if it.get("level") == 2 else 1, "text": runs_to_markup(it["runs"])}
        gap = max(0, min(int(it.get("gap", 0)), 100))
        if gap:
            out["gap"] = gap
        return out

    def no_cache(resp):
        resp.headers["Cache-Control"] = "no-cache"
        return resp

    @app.get("/")
    def index():
        entries = []
        for p in sorted(docs_dir.glob("*.json")):
            t = json.loads(p.read_text("utf8")).get("title", {})
            entries.append((p.stem, t.get("hu") or t.get("he", "")))
        return no_cache(app.response_class(render.index_html(entries)))

    @app.get("/d/<doc_id>")
    def view(doc_id):
        return no_cache(app.response_class(render.doc_html(doc_id, load(doc_id))))

    @app.get("/api/docs/<doc_id>")
    def get_doc(doc_id):
        return jsonify(load(doc_id))

    @app.put("/api/docs/<doc_id>/seif/<int:n>")
    def put_seif(doc_id, n):
        data = request.get_json(force=True)
        with lock:
            doc = load(doc_id)
            seif = next((s for s in doc["seifim"] if s["id"] == n), None)
            if seif is None:
                abort(404)
            if "hebrew" in data:
                seif["hebrew"] = [runs_to_markup(l) for l in data["hebrew"]]
            if "hungarian" in data:
                hu = data["hungarian"]
                seif["hungarian"] = {
                    "title": runs_to_markup(hu["title"]),
                    "items": [item(it) for it in hu["items"]],
                }
            save(doc_id, doc)
            return jsonify(ok=True)

    @app.put("/api/docs/<doc_id>/meta")
    def put_meta(doc_id):
        data = request.get_json(force=True)  # {"title.hu": runs, ...}
        with lock:
            doc = load(doc_id)
            for key, runs in data.items():
                field, _, lang = key.partition(".")
                if field not in ("title", "description") or lang not in ("he", "hu"):
                    abort(400)
                doc[field][lang] = runs_to_markup(runs)
            save(doc_id, doc)
            return jsonify(ok=True)

    @app.get("/manifest.webmanifest")
    def manifest():
        return app.response_class(
            json.dumps({
                "name": "Machon szerkesztő", "short_name": "Machon", "start_url": "/", "scope": "/",
                "display": "standalone", "background_color": "#f4f1ea", "theme_color": "#2b3a55",
                "icons": [{"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png"},
                          {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png"}],
            }), mimetype="application/manifest+json")

    @app.get("/sw.js")
    def sw():
        return no_cache(send_from_directory(app.static_folder, "sw.js", mimetype="text/javascript"))

    return app


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--docs", default=str(ROOT / "docs"))
    ap.add_argument("--cert")
    ap.add_argument("--key")
    a = ap.parse_args()
    ctx = (a.cert, a.key) if a.cert and a.key else None
    create_app(a.docs).run(host=a.host, port=a.port, ssl_context=ctx, threaded=True)


if __name__ == "__main__":
    main()
