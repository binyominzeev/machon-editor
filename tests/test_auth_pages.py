import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from machon import auth, server


class AuthenticatedPageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        doc = {
            "gate": "orach_chaim", "siman": 1, "siman_he": "א",
            "title": {"hu": "Cím", "he": ""},
            "description": {"hu": "", "he": ""},
            "seifim": [{
                "id": 1, "letter": "א", "hebrew": ["szöveg"],
                "hungarian": {"title": "Cím", "items": []},
            }],
        }
        Path(self.directory.name, "oc-1.json").write_text(json.dumps(doc), encoding="utf8")
        self.env = patch.dict(os.environ, {"OIDC_ISSUER": "https://issuer.example"})
        self.env.start()
        self.addCleanup(self.env.stop)
        with patch.object(server.ai, "load_env"):
            self.client = server.create_app(self.directory.name).test_client()
        self.verifier = patch.object(auth, "verify", side_effect=lambda token: {"sub": "user"} if token == "valid" else None)
        self.verifier.start()
        self.addCleanup(self.verifier.stop)

    def test_guest_cookie_and_bearer_pages(self):
        guest = self.client.get("/d/oc-1")
        self.assertIn(b'data-readonly', guest.data)
        self.assertNotIn("X-Machon-Authenticated-Page", guest.headers)

        bearer = self.client.get("/d/oc-1", headers={"Authorization": "Bearer valid"})
        self.assertNotIn(b'data-readonly', bearer.data)
        self.assertIn(b'contenteditable="true"', bearer.data)
        self.assertEqual(bearer.headers["X-Machon-Authenticated-Page"], "1")
        self.assertEqual(bearer.headers["Cache-Control"], "no-store")

        self.client.set_cookie("machon_at", "valid")
        cookie = self.client.get("/d/oc-1")
        self.assertNotIn(b'data-readonly', cookie.data)
        self.assertNotIn("X-Machon-Authenticated-Page", cookie.headers)

    def test_invalid_bearer_does_not_fall_back_to_cookie(self):
        self.client.set_cookie("machon_at", "valid")
        response = self.client.get("/d/oc-1", headers={"Authorization": "Bearer invalid"})
        self.assertEqual(response.status_code, 401)
        self.assertNotIn("X-Machon-Authenticated-Page", response.headers)

    def test_home_and_new_siman_accept_bearer_but_writes_require_it(self):
        headers = {"Authorization": "Bearer valid"}
        self.assertNotIn(b'data-readonly', self.client.get("/", headers=headers).data)
        self.assertEqual(self.client.get("/s/oc-2", headers=headers).status_code, 200)
        self.client.set_cookie("machon_at", "valid")
        self.assertEqual(self.client.put("/api/docs/oc-1/meta", json={}).status_code, 401)
        self.assertEqual(self.client.put("/api/docs/oc-1/meta", json={}, headers=headers).status_code, 200)


if __name__ == "__main__":
    unittest.main()
