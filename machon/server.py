#!/usr/bin/python
"""Machon editor server.

    python -m machon.server [--host 0.0.0.0] [--port 8000] [--docs docs] [--cert c.pem --key k.pem]
"""
import argparse
import json
import os
import re
import threading
from pathlib import Path

from flask import Flask, abort, jsonify, redirect, request, send_from_directory

from . import ai, auth, markup, render

ROOT = Path(__file__).resolve().parent.parent
ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
lock = threading.Lock()


def create_app(docs_dir):
    docs_dir = Path(docs_dir)
    ai.load_env()
    jobs = {}
    app = Flask(__name__, static_folder=str(ROOT / "static"), static_url_path="/static")
    auth.init_app(app, render.login_html)

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
        return markup.serialize([
            (str(run[0]), bool(run[1]), bool(run[2]),
             bool(run[3]) if len(run) > 3 else False,
             bool(run[4]) if len(run) > 4 else False)
            for run in runs
        ])

    def item(it):
        out = {"level": 2 if it.get("level") == 2 else 1, "text": runs_to_markup(it["runs"])}
        gap = max(0, min(int(it.get("gap", 0)), 100))
        if gap:
            out["gap"] = gap
        return out

    def no_cache(resp):
        resp.headers["Cache-Control"] = "no-cache"
        return resp

    def parse_id(doc_id):
        m = re.match(r"^([a-z]{2})-(\d+)$", doc_id)
        if not m or m.group(1) not in ai.VOLUMES or not 1 <= int(m.group(2)) <= ai.VOLUMES[m.group(1)][2]:
            abort(404)
        return m.group(1), int(m.group(2))

    @app.get("/")
    def index():
        entries = []
        for p in docs_dir.glob("*.json"):
            m = re.match(r"^([a-z]{2})-(\d+)$", p.stem)
            if not m or m.group(1) not in ai.VOLUMES:
                continue
            doc = json.loads(p.read_text("utf8"))
            t = doc.get("title", {})
            entries.append({"id": p.stem, "vol": m.group(1), "n": int(m.group(2)),
                            "title": t.get("hu") or t.get("he", ""), "mtime": p.stat().st_mtime})
        return no_cache(app.response_class(render.index_html(entries, auth.can_edit())))

    @app.get("/s/<doc_id>")
    def open_siman(doc_id):
        vol, n = parse_id(doc_id)
        if path(doc_id).exists():
            return redirect(f"/d/{doc_id}")
        if not auth.can_edit():
            return app.response_class(render.login_html(), status=401)
        return no_cache(app.response_class(render.generate_html(doc_id, vol, n, bool(os.environ.get("OPENAI_API_KEY")))))

    @app.post("/api/generate/<doc_id>")
    def generate(doc_id):
        vol, n = parse_id(doc_id)
        data = request.get_json(silent=True) or {}
        with lock:
            if path(doc_id).exists():
                return jsonify(ok=True, done=True, url=f"/d/{doc_id}")
            job = jobs.get(doc_id)
            if job and not job.get("done"):
                return jsonify(ok=True)
            job = jobs[doc_id] = {"step": "start", "pct": 1, "message": "Indul…", "done": False}

        def progress(step, pct, message):
            job.update(step=step, pct=pct, message=message)

        def work():
            try:
                doc = ai.generate(vol, n, data.get("text"), progress)
                with lock:
                    if not path(doc_id).exists():
                        save(doc_id, doc)
                job.update(step="done", pct=100, message="Kész.", done=True, url=f"/d/{doc_id}")
            except Exception as e:
                ai.log(f"{doc_id}: HIBA: {e}")
                job.update(error=str(e), done=True)

        threading.Thread(target=work, daemon=True).start()
        return jsonify(ok=True)

    @app.post("/api/docs/<doc_id>/regenerate")
    def regenerate(doc_id):
        vol, n = parse_id(doc_id)
        load(doc_id)
        data = request.get_json(silent=True) or {}
        seif = int(data["seif"]) if data.get("seif") else None
        key = f"re:{doc_id}:{seif or 'all'}"
        with lock:
            job = jobs.get(key)
            if job and not job.get("done"):
                return jsonify(ok=True)
            job = jobs[key] = {"step": "start", "pct": 1, "message": "Indul…", "done": False}

        def progress(step, pct, message):
            job.update(step=step, pct=pct, message=message)

        def work():
            try:
                new = ai.generate(vol, n, None, progress, only_seif=seif)
                with lock:
                    doc = load(doc_id)
                    if seif:
                        old = next((i for i, x in enumerate(doc["seifim"]) if x["id"] == seif), None)
                        if old is None:
                            raise RuntimeError(f"Nincs {seif}. széif a dokumentumban.")
                        doc["seifim"][old] = new["seifim"][0]
                    else:
                        doc = new
                    save(doc_id, doc)
                job.update(step="done", pct=100, message="Kész.", done=True)
            except Exception as e:
                ai.log(f"{key}: HIBA: {e}")
                job.update(error=str(e), done=True)

        threading.Thread(target=work, daemon=True).start()
        return jsonify(ok=True)

    @app.get("/api/docs/<doc_id>/regenerate")
    def regenerate_status(doc_id):
        parse_id(doc_id)
        seif = request.args.get("seif") or "all"
        return jsonify(jobs.get(f"re:{doc_id}:{seif}", {"done": False, "step": "idle", "pct": 0, "message": ""}))

    @app.get("/api/generate/<doc_id>")
    def generate_status(doc_id):
        parse_id(doc_id)
        if path(doc_id).exists():
            return jsonify(done=True, pct=100, url=f"/d/{doc_id}")
        return jsonify(jobs.get(doc_id, {"done": False, "step": "idle", "pct": 0, "message": ""}))

    @app.get("/d/<doc_id>")
    def view(doc_id):
        return no_cache(app.response_class(render.doc_html(doc_id, load(doc_id), auth.can_edit())))

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
