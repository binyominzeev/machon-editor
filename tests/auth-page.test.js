const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const script = fs.readFileSync("static/auth.js", "utf8");
const jwt = (exp) => `x.${Buffer.from(JSON.stringify({ sub: "user", exp })).toString("base64url")}.x`;

function runAuth({ responses, token = jwt(Math.floor(Date.now() / 1000) + 3600), refresh = null }) {
  const values = new Map([["machon.accessToken", token], ["machon.userName", "Teszt"]]);
  if (refresh) values.set("machon.refreshToken", refresh);
  const localStorage = {
    getItem: (key) => values.get(key) || null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  };
  const status = { textContent: "" };
  const button = {};
  const calls = [];
  let written = "";
  let replaced = "";
  const document = {
    body: { hasAttribute: (name) => name === "data-readonly" },
    getElementById: (id) => ({ "auth-status": status, "login-button": button })[id] || null,
    addEventListener() {},
    dispatchEvent() {},
    open() {},
    write: (html) => { written = html; },
    close() {},
    cookie: "",
  };
  const window = {
    MACHON_CONFIG: { enabled: true },
    location: { origin: "https://editor.example", pathname: "/d/oc-1", search: "?x=1", hash: "#s1", protocol: "https:" },
    history: { replaceState: (_state, _title, url) => { replaced = url; } },
    addEventListener() {},
  };
  const fetch = async (url, options) => {
    calls.push({ url, options });
    const response = responses.shift();
    if (response instanceof Error) throw response;
    return response;
  };
  const context = {
    window, document, localStorage, sessionStorage: localStorage, fetch, URL, URLSearchParams,
    navigator: { onLine: true }, setTimeout: () => 1, clearTimeout() {},
    atob: (value) => Buffer.from(value, "base64").toString("binary"),
    CustomEvent: class {},
  };
  vm.runInNewContext(script, context);
  return { window, status, calls, get written() { return written; }, get replaced() { return replaced; } };
}

function response(status, html, authenticated = true) {
  return {
    status, ok: status >= 200 && status < 300,
    url: "https://editor.example/d/oc-1?x=1",
    headers: { get: () => authenticated ? "1" : null },
    text: async () => html,
  };
}

test("readonly iframe loads authenticated HTML without relying on cookies", async () => {
  const token = jwt(Math.floor(Date.now() / 1000) + 3600);
  const app = runAuth({ token, responses: [response(200, "<html>editor</html>")] });
  await app.window.MachonAuth.ready;
  assert.equal(app.calls[0].options.headers.Authorization, `Bearer ${token}`);
  assert.equal(app.calls[0].options.cache, "no-store");
  assert.equal(app.written, "<html>editor</html>");
  assert.equal(app.replaced, "/d/oc-1?x=1#s1");
});

test("failed or unauthenticated HTML is not installed", async () => {
  for (const result of [response(401, "no"), response(200, "guest", false), new Error("offline")]) {
    const app = runAuth({ responses: [result] });
    await app.window.MachonAuth.ready;
    assert.equal(app.written, "");
    assert.match(app.status.textContent, /Bejelentkezési hiba/);
  }
});

test("expired server token is refreshed and the page request retried", async () => {
  const newToken = jwt(Math.floor(Date.now() / 1000) + 7200);
  const app = runAuth({
    refresh: "refresh-token",
    responses: [
      response(401, "no"),
      response(200, JSON.stringify({ access_token: newToken })),
      response(200, "editor"),
    ],
  });
  await app.window.MachonAuth.ready;
  assert.equal(app.calls.length, 3);
  assert.equal(app.calls[1].url, "/api/auth/refresh");
  assert.equal(app.calls[2].options.headers.Authorization, `Bearer ${newToken}`);
  assert.equal(app.written, "editor");
});
