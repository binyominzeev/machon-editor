(() => {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];

  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});

  const main = $("#doc");
  if (!main) return;
  const docId = main.dataset.doc;
  const narrow = () => matchMedia("(max-width:900px)").matches;
  function createOfflinePageHtml() {
    const copy = document.documentElement.cloneNode(true);
    copy.querySelector("#auth-status")?.replaceChildren();
    const loginButton = copy.querySelector("#login-button");
    if (loginButton) loginButton.textContent = "Belépés";
    copy.querySelectorAll(".edit").forEach((edit) => {
      edit.removeAttribute("contenteditable");
      edit.classList.remove("editing");
    });
    const status = copy.querySelector("#status");
    if (status) { status.className = "sync-status offline"; status.textContent = "● offline · helyben mentve"; }
    return `<!doctype html>\n${copy.outerHTML}`;
  }
  const offlinePageHtml = main.hasAttribute("data-readonly") ? null : createOfflinePageHtml();
  function cacheOfflinePage(worker = navigator.serviceWorker?.controller) {
    if (!worker || !offlinePageHtml) return;
    worker.postMessage({ type: "CACHE_PAGE", url: location.href, html: offlinePageHtml });
  }
  function cacheOfflinePageWhenReady() {
    if (!("serviceWorker" in navigator)) return;
    navigator.serviceWorker.ready.then((registration) => {
      cacheOfflinePage(registration.active);
    }).catch(() => {});
  }

  /* ---------- sidebar / TOC ---------- */
  const setToc = (open) => {
    document.body.classList.toggle("toc-closed", !open);
    if (!narrow()) localStorage.setItem("toc-open", open ? "1" : "0");
  };
  setToc(narrow() ? false : localStorage.getItem("toc-open") !== "0");
  $("#tocBtn").onclick = () => setToc(document.body.classList.contains("toc-closed"));
  $("#scrim").onclick = () => setToc(false);
  $("#toc").addEventListener("click", (e) => {
    const a = e.target.closest("a");
    if (!a) return;
    e.preventDefault();
    document.getElementById(a.dataset.target).scrollIntoView({ behavior: "smooth", block: "start" });
    if (narrow()) setToc(false);
  });

  const seifs = $$(".seif");
  const tocLinks = new Map($$("#toc a").map((a) => [a.dataset.target, a]));
  let active = null;
  const updateActive = () => {
    const line = 80 + 20;
    let cur = null;
    for (const s of seifs) {
      if (s.getBoundingClientRect().top <= line) cur = s;
      else break;
    }
    if (cur === active) return;
    active = cur;
    seifs.forEach((s) => s.classList.toggle("current", s === cur));
    tocLinks.forEach((a, id) => a.classList.toggle("active", cur && cur.id === id));
    $("#cur").textContent = cur ? cur.querySelector(".num").textContent + " – " + cur.querySelector(".t").textContent : "";
    const a = cur && tocLinks.get(cur.id);
    if (a) {
      const toc = $("#toc"), r = a.getBoundingClientRect(), tr = toc.getBoundingClientRect();
      if (r.top < tr.top || r.bottom > tr.bottom) toc.scrollTop += r.top - tr.top - tr.height / 2;
    }
  };
  let raf = 0;
  addEventListener("scroll", () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(updateActive); }, { passive: true });
  updateActive();

  if (main.hasAttribute("data-readonly")) return; // olvasó mód: nincs szerkesztés
  if (window.MACHON_CONFIG?.enabled && !MachonAuth.isAuthenticated()) return;

  /* ---------- serialization (DOM -> runs) ---------- */
  const isBold = (el) => /^(B|STRONG)$/.test(el.tagName) || /^(bold|[6-9]00)$/.test(el.style.fontWeight);
  const isItalic = (el) => /^(I|EM)$/.test(el.tagName) || el.style.fontStyle === "italic";

  function walk(node, b, i, out) {
    if (node.nodeType === 3) {
      const t = node.nodeValue.replace(/\u00a0/g, " ").replace(/[\r\n]+/g, " ");
      if (t) out.push([t, b, i]);
    } else if (node.nodeType === 1 && node.tagName !== "BR") {
      const nb = b || isBold(node), ni = i || isItalic(node);
      node.childNodes.forEach((c) => walk(c, nb, ni, out));
    }
  }
  const runsOf = (el) => { const out = []; walk(el, false, false, out); return out; };
  const isEmpty = (runs) => !runs.some((r) => r[0].trim());

  // Wrap stray inline content into block divs and return all leaf block elements.
  function blocksOf(root) {
    let run = [];
    const flush = (before) => {
      if (!run.length) return;
      const d = document.createElement("div");
      root.insertBefore(d, before);
      run.forEach((n) => d.appendChild(n));
      run = [];
    };
    [...root.childNodes].forEach((n) => {
      if (n.nodeType === 1 && n.tagName === "DIV") { flush(n); }
      else run.push(n);
    });
    flush(null);
    const out = [];
    const rec = (el) => {
      const kids = [...el.children].filter((c) => c.tagName === "DIV");
      if (kids.length) kids.forEach(rec); else out.push(el);
    };
    [...root.children].forEach(rec);
    return out;
  }

  function normalize(edit) {
    const field = edit.parentElement.dataset.field;
    const bl = blocksOf(edit);
    if (!bl.length) {
      const d = document.createElement("div");
      d.innerHTML = "<br>";
      edit.appendChild(d);
      bl.push(d);
    }
    bl.forEach((d, idx) => {
      if (d.parentElement !== edit) edit.appendChild(d);
      if (field === "he") { d.className = "l"; d.removeAttribute("data-level"); }
      else if (idx === 0) { d.className = "t"; d.removeAttribute("data-level"); }
      else {
        d.className = runsOf(d).some((r) => r[0].trim()) ? "p" : "p gap"; // empty line = spacer
        if (d.dataset.level !== "2") d.dataset.level = "1";
      }
    });
    return bl;
  }

  function payload(sec, field) {
    const edit = $(".edit", $(`[data-field="${field}"]`, sec));
    const bl = normalize(edit);
    if (field === "he") {
      return { hebrew: bl.map(runsOf).filter((r) => !isEmpty(r)) };
    }
    const [title, ...rest] = bl;
    const items = [];
    let gap = 0;
    for (const d of rest) {
      const runs = runsOf(d);
      if (isEmpty(runs)) { gap++; continue; }
      const it = { level: d.dataset.level === "2" ? 2 : 1, runs };
      if (gap) it.gap = gap;
      items.push(it);
      gap = 0;
    }
    return { hungarian: { title: runsOf(title), items } };
  }

  /* ---------- saving with offline queue ---------- */
  const userId = MachonAuth.getUserId();
  const PEND = `pending-saves:${userId}:${docId}`;
  const LOCAL = `local-doc:${userId}:${docId}`;
  const pending = () => JSON.parse(localStorage.getItem(PEND) || "{}");
  const setPending = (p) => localStorage.setItem(PEND, JSON.stringify(p));
  const localCopy = () => JSON.parse(localStorage.getItem(LOCAL) || "{}");
  const setLocalCopy = (p) => localStorage.setItem(LOCAL, JSON.stringify(p));
  const statusEl = $("#status");
  const setStatus = (state) => {
    const messages = {
      offline: "● offline · helyben mentve",
      edited: "✎ szerkesztve",
      syncing: "↻ szinkronizálás…",
      synced: "✓ szinkronizálva",
      conflict: "⚠ lehetséges ütközés",
      error: "⚠ nincs szinkronizálva"
    };
    statusEl.className = `sync-status ${state}`;
    statusEl.textContent = messages[state];
    statusEl.title = state === "conflict"
      ? "A szerver elutasította a mentést; ellenőrizd a helyi és a szerverpéldányt."
      : messages[state];
  };
  const renderRuns = (runs) => {
    const fragment = document.createDocumentFragment();
    if (!Array.isArray(runs)) return fragment;
    for (const [text, bold, italic] of runs) {
      let node = document.createTextNode(text);
      if (italic) { const el = document.createElement("i"); el.append(node); node = el; }
      if (bold) { const el = document.createElement("b"); el.append(node); node = el; }
      fragment.append(node);
    }
    return fragment;
  };
  function applyLocalEntry(key, body) {
    const seifMatch = /^s(\d+)\.(he|hu)$/.exec(key);
    if (seifMatch) {
      const sec = $(`[data-seif="${seifMatch[1]}"]`, main);
      const field = seifMatch[2];
      const edit = sec && $(".edit", $(`[data-field="${field}"]`, sec));
      if (!edit) return;
      edit.replaceChildren();
      if (field === "he") {
        (body.hebrew || []).forEach((runs) => {
          const line = document.createElement("div");
          line.className = "l";
          line.append(renderRuns(runs));
          if (!line.textContent) line.append(document.createElement("br"));
          edit.append(line);
        });
        if (!edit.childElementCount) edit.innerHTML = '<div class="l"><br></div>';
      } else {
        const title = document.createElement("div");
        title.className = "t";
        title.append(renderRuns(body.hungarian.title));
        if (!title.textContent) title.append(document.createElement("br"));
        edit.append(title);
        (body.hungarian.items || []).forEach((item) => {
          for (let i = 0; i < (item.gap || 0); i++) {
            const gap = document.createElement("div");
            gap.className = "p gap";
            gap.dataset.level = "1";
            gap.append(document.createElement("br"));
            edit.append(gap);
          }
          const point = document.createElement("div");
          point.className = "p";
          point.dataset.level = item.level === 2 ? "2" : "1";
          point.append(renderRuns(item.runs));
          if (!point.textContent) point.append(document.createElement("br"));
          edit.append(point);
        });
        const link = tocLinks.get(sec.id);
        if (link) $(".tt", link).textContent = title.textContent || "–";
      }
      return;
    }
    const metaKey = /^meta\.(title|description)\.(he|hu)$/.exec(key);
    if (metaKey) {
      const field = $$(".mf", main).find((el) => el.dataset.meta === `${metaKey[1]}.${metaKey[2]}`);
      const runs = body[`${metaKey[1]}.${metaKey[2]}`];
      if (field && Array.isArray(runs)) field.replaceChildren(renderRuns(runs));
    }
  }
  function restoreLocalCopy() {
    const saved = localCopy();
    const queued = pending();
    if (!navigator.onLine || Object.keys(queued).length) {
      Object.entries(saved).forEach(([key, body]) => applyLocalEntry(key, body));
      Object.entries(queued).forEach(([key, entry]) => {
        if (!saved[key]) applyLocalEntry(key, entry.body);
      });
    } else if (Object.keys(saved).length) {
      setLocalCopy({});
    }
  }

  /* ---------- AI regeneration ---------- */
  let regenBusy = false;
  async function regenerate(which) {
    if (regenBusy) return;
    const label = which === "all" ? "Az egész szimán" : "A(z) " + which + ". széif";
    if (!confirm(label + " tartalmát felülírja az AI új változata (a szerkesztéseid elvesznek; az előző állapot a .bak fájlban megmarad). Folytatod?")) return;
    regenBusy = true;
    const box = $("#regenbox"), msg = $(".rmsg", box), fill = $("#rfill");
    box.hidden = false; box.classList.remove("err"); fill.style.width = "1%"; msg.textContent = "Indítás…";
    try {
      saveNow();
      const base = "/api/docs/" + docId + "/regenerate";
      const r = await MachonAuth.fetch(base, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ seif: which === "all" ? null : +which }) });
      if (!r.ok) throw new Error("HTTP " + r.status);
      for (;;) {
        await new Promise((res) => setTimeout(res, 1000));
        const j = await (await MachonAuth.fetch(base + "?seif=" + which)).json();
        if (j.error) throw new Error(j.error);
        fill.style.width = (j.pct || 0) + "%";
        msg.textContent = (j.pct || 0) + "% – " + (j.message || "");
        if (j.done) { location.reload(); return; }
      }
    } catch (e) {
      box.classList.add("err"); msg.textContent = "Hiba: " + e.message;
      setTimeout(() => { box.hidden = true; }, 8000);
      regenBusy = false;
    }
  }
  main.addEventListener("click", (e) => {
    const b = e.target.closest(".regen");
    if (b) { e.preventDefault(); e.stopPropagation(); regenerate(b.dataset.regen); }
  });

  const timers = new Map();
  let flushing = false;
  let conflictDetected = false;

  async function flush() {
    if (flushing || conflictDetected) return;
    if (!navigator.onLine) return setStatus("offline");
    flushing = true;
    try {
      while (true) {
        const p = pending();
        const keys = Object.keys(p);
        if (!keys.length) return setStatus("synced");
        setStatus("syncing");
        for (const k of keys) {
          try {
            const r = await MachonAuth.fetch(p[k].url, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(p[k].body), keepalive: true });
            if (r.status === 409 || r.status === 412) {
              conflictDetected = true;
              return setStatus("conflict");
            }
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            const now = pending();
            if (JSON.stringify(now[k]) === JSON.stringify(p[k])) { delete now[k]; setPending(now); }
          } catch (e) {
            setStatus(!navigator.onLine || e instanceof TypeError ? "offline" : "error");
            return;
          }
        }
      }
    } finally {
      flushing = false;
    }
  }

  function queue(key, url, body, delay = 900) {
    const p = pending();
    const saved = localCopy();
    saved[key] = body;
    setLocalCopy(saved);
    p[key] = { url, body };
    setPending(p);
    setStatus(navigator.onLine ? "edited" : "offline");
    clearTimeout(timers.get(key));
    timers.set(key, setTimeout(flush, delay));
  }
  const saveNow = () => { timers.forEach(clearTimeout); flush(); };
  addEventListener("online", flush);
  addEventListener("offline", () => setStatus("offline"));
  addEventListener("pagehide", saveNow);
  document.addEventListener("visibilitychange", () => document.hidden && saveNow());
  setInterval(() => Object.keys(pending()).length && flush(), 15000);
  restoreLocalCopy();
  cacheOfflinePageWhenReady();
  flush();

  const queueSeif = (sec, field) => queue(`s${sec.dataset.seif}.${field}`, `/api/docs/${docId}/seif/${sec.dataset.seif}`, payload(sec, field));

  /* ---------- editing széifs ---------- */
  function caretAt(x, y) {
    if (document.caretPositionFromPoint) {
      const p = document.caretPositionFromPoint(x, y);
      if (p) { const r = document.createRange(); r.setStart(p.offsetNode, p.offset); r.collapse(true); return r; }
    }
    return document.caretRangeFromPoint ? document.caretRangeFromPoint(x, y) : null;
  }

  function startEdit(edit, range) {
    if (edit.isContentEditable) return;
    edit.contentEditable = "true";
    edit.spellcheck = edit.closest(".he") === null;
    edit.classList.add("editing");
    document.body.classList.add("is-editing");
    edit.focus({ preventScroll: true });
    const sel = getSelection();
    if (range && edit.contains(range.startContainer)) { sel.removeAllRanges(); sel.addRange(range); }
    else { const r = document.createRange(); r.selectNodeContents(edit); r.collapse(false); sel.removeAllRanges(); sel.addRange(r); }
  }

  function stopEdit(edit) {
    edit.contentEditable = "false";
    edit.removeAttribute("contenteditable");
    edit.classList.remove("editing");
    document.body.classList.remove("is-editing");
    const sec = edit.closest(".seif"), field = edit.parentElement.dataset.field;
    clearTimeout(timers.get(`s${sec.dataset.seif}.${field}`));
    queueSeif(sec, field);
    flush();
    if (field === "hu") {
      const t = $(".t", edit);
      const a = tocLinks.get(sec.id);
      if (a) $(".tt", a).textContent = t.textContent || "–";
    }
  }

  main.addEventListener("click", (e) => {
    const edit = e.target.closest(".seif .edit");
    if (edit && !edit.isContentEditable) startEdit(edit, caretAt(e.clientX, e.clientY));
  });
  main.addEventListener("keydown", (e) => {
    const edit = e.target.closest && e.target.closest(".seif .edit");
    if (!edit) return;
    if (!edit.isContentEditable) {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); startEdit(edit); }
      return;
    }
    if (e.key === "Escape") { edit.blur(); return; }
    if ((e.ctrlKey || e.metaKey) && !e.altKey && /^[bi]$/i.test(e.key)) {
      e.preventDefault();
      document.execCommand(e.key.toLowerCase() === "b" ? "bold" : "italic");
      return;
    }
    if (e.key === "Tab" && edit.parentElement.dataset.field === "hu") {
      e.preventDefault();
      const n = getSelection().anchorNode;
      const el = n && (n.nodeType === 3 ? n.parentElement : n);
      let blk = el;
      while (blk && blk.parentElement !== edit) blk = blk.parentElement;
      if (blk && blk !== edit.firstElementChild) {
        blk.dataset.level = e.shiftKey ? "1" : "2";
        edit.dispatchEvent(new Event("input", { bubbles: true }));
      }
    }
  });
  main.addEventListener("input", (e) => {
    const edit = e.target.closest && e.target.closest(".seif .edit");
    if (!edit) return;
    const sec = edit.closest(".seif");
    queueSeif(sec, edit.parentElement.dataset.field);
  });
  main.addEventListener("focusout", (e) => {
    const edit = e.target.closest && e.target.closest(".seif .edit");
    if (edit && edit.isContentEditable && !edit.contains(e.relatedTarget)) stopEdit(edit);
  });

  /* paste as plain text */
  main.addEventListener("paste", (e) => {
    const t = e.target.closest && e.target.closest("[contenteditable=true]");
    if (!t) return;
    e.preventDefault();
    const lines = (e.clipboardData.getData("text/plain") || "").replace(/\r/g, "").split("\n");
    const single = !t.classList.contains("edit");
    lines.forEach((l, k) => {
      if (k && !single) document.execCommand("insertParagraph");
      if (l) document.execCommand("insertText", false, single && k ? " " + l : l);
    });
  });
  main.addEventListener("drop", (e) => e.preventDefault());

  /* ---------- header fields (always editable, single line) ---------- */
  $$(".mf").forEach((f) => {
    f.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); f.blur(); }
      else if ((e.ctrlKey || e.metaKey) && !e.altKey && /^[bi]$/i.test(e.key)) {
        e.preventDefault();
        document.execCommand(e.key.toLowerCase() === "b" ? "bold" : "italic");
      }
    });
    f.addEventListener("input", () => queue("meta." + f.dataset.meta, `/api/docs/${docId}/meta`, { [f.dataset.meta]: runsOf(f) }));
    f.addEventListener("blur", saveNow);
  });
})();
