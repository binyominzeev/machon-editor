"""Pocket ID (OIDC) bejelentkezés: JWT-ellenőrzés és token-proxy (a client_secret csak itt él).

A böngésző Authorization-fejlécet küld az /api/* hívásokhoz; az oldalak (HTML) navigációját a
`machon_at` süti védi, amit a static/auth.js az access tokenből állít be. Ugyanazt a JWT-t
ellenőrizzük mindkét esetben. Bejelentkezés nélkül csak olvasás (GET /, /d/*, /s/*, /api/docs/*). Ha az OIDC_ISSUER nincs beállítva, a hitelesítés ki van kapcsolva.
"""
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

import jwt
from flask import g, jsonify, request

COOKIE = "machon_at"
ALGORITHMS = ["RS256", "RS384", "RS512", "PS256", "ES256", "EdDSA"]
PUBLIC_PREFIXES = ("/static/", "/api/auth/")
PUBLIC_PATHS = {"/sw.js", "/manifest.webmanifest", "/auth-config.js"}
# Bejelentkezés nélkül ezek (csak olvasásra, GET) elérhetők.
READONLY_PREFIXES = ("/d/", "/s/", "/api/docs/")

_jwks = {}


def log(event, **details):
    print(f"[auth] {event} {json.dumps(details)}", flush=True)


def issuer():
    return os.environ.get("OIDC_ISSUER", "").strip().rstrip("/")


def enabled():
    return bool(issuer())


def client_config():
    return {"enabled": enabled(), "oidcIssuer": issuer(), "oidcClientId": os.environ.get("OIDC_CLIENT_ID", "")}


def verify(token):
    """A token claimjei, vagy None, ha érvénytelen."""
    iss = issuer()
    if not iss or not token:
        return None
    try:
        client = _jwks.get(iss)
        if client is None:
            client = _jwks[iss] = jwt.PyJWKClient(f"{iss}/.well-known/jwks.json", cache_keys=True)
        key = client.get_signing_key_from_jwt(token).key
        audience = os.environ.get("OIDC_AUDIENCE") or None
        claims = jwt.decode(
            token, key, algorithms=ALGORITHMS, issuer=iss, audience=audience,
            options={"require": ["exp", "iss", "sub"], "verify_aud": audience is not None},
        )
    except Exception as e:
        log("verify.failed", error=type(e).__name__)
        return None
    return claims if isinstance(claims.get("sub"), str) and claims["sub"] else None


def bearer():
    m = re.match(r"^Bearer\s+(.+)$", request.headers.get("Authorization", ""), re.I)
    return m.group(1) if m else None


def exchange(grant):
    """Token endpoint hívása Pocket ID felé; (status, body)."""
    cid, secret = os.environ.get("OIDC_CLIENT_ID"), os.environ.get("OIDC_CLIENT_SECRET")
    if not (issuer() and cid and secret):
        return 503, json.dumps({"error": "OIDC server configuration is incomplete"})
    data = urllib.parse.urlencode({"client_id": cid, "client_secret": secret, **grant}).encode()
    req = urllib.request.Request(f"{issuer()}/api/oidc/token", data=data,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.read().decode("utf8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf8", "replace")
    except Exception as e:
        log("exchange.error", error=str(e))
        return 502, json.dumps({"error": "Pocket ID unreachable"})


def init_app(app, login_page):
    @app.get("/auth-config.js")
    def auth_config():
        resp = app.response_class("window.MACHON_CONFIG=" + json.dumps(client_config()) + ";",
                                  mimetype="text/javascript")
        resp.headers["Cache-Control"] = "no-cache"
        return resp

    @app.post("/api/auth/token")
    def auth_token():
        code, verifier, redirect_uri = (request.form.get(k) for k in ("code", "code_verifier", "redirect_uri"))
        configured = os.environ.get("OIDC_REDIRECT_URI")
        if not configured:
            log("token.config_missing")
            return jsonify(error="OIDC server configuration is incomplete"), 503
        if not code or not verifier or redirect_uri != configured:
            log("token.invalid_request", redirectUriMatches=redirect_uri == configured)
            return jsonify(error="Invalid OIDC token request"), 400
        status, body = exchange({"grant_type": "authorization_code", "code": code,
                                 "redirect_uri": configured, "code_verifier": verifier})
        log("token.success" if status == 200 else "token.failed", status=status)
        return app.response_class(body, status=status, mimetype="application/json")

    @app.post("/api/auth/refresh")
    def auth_refresh():
        refresh = request.form.get("refresh_token")
        if not refresh:
            return jsonify(error="Invalid refresh request"), 400
        status, body = exchange({"grant_type": "refresh_token", "refresh_token": refresh})
        log("refresh.success" if status == 200 else "refresh.failed", status=status)
        return app.response_class(body, status=status, mimetype="application/json")

    @app.before_request
    def require_login():
        g.user = None
        if not enabled():
            return None
        p = request.path
        if request.method == "OPTIONS" or p in PUBLIC_PATHS or p.startswith(PUBLIC_PREFIXES):
            return None
        # API: csak Authorization-fejléc (a süti nem, így CSRF-mentes); oldalak: süti.
        g.user = verify(bearer() if p.startswith("/api/") else request.cookies.get(COOKIE))
        if g.user:
            return None
        if request.method in ("GET", "HEAD") and (p == "/" or p.startswith(READONLY_PREFIXES)):
            return None
        if p.startswith("/api/"):
            return jsonify(error="Authentication required"), 401
        resp = app.response_class(login_page(), status=401)
        resp.headers["Cache-Control"] = "no-store"
        return resp


def can_edit():
    """Szerkeszthet-e az aktuális kérés (hitelesítés kikapcsolva = igen)."""
    return not enabled() or bool(getattr(g, "user", None))
