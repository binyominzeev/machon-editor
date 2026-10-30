(() => {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];

  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});

  const main = $("#doc");
  if (!main) return;
  const docId = main.dataset.doc;
  const narrow = () => matchMedia("(max-width:900px)").matches;

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
  const statusEl = $("#status");
  const PEND = "pending-saves:" + docId;
  const pending = () => JSON.parse(localStorage.getItem(PEND) || "{}");
  const setPending = (p) => localStorage.setItem(PEND, JSON.stringify(p));
  const setStatus = (cls, text) => { statusEl.className = cls; statusEl.textContent = text; };
  const timers = new Map();

  async function flush() {
    const p = pending();
    const keys = Object.keys(p);
    if (!keys.length) return setStatus("", "✓ mentve");
    setStatus("dirty", "mentés…");
    for (const k of keys) {
      try {
        const r = await fetch(p[k].url, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(p[k].body), keepalive: true });
        if (!r.ok) throw new Error(r.status);
        const now = pending();
        if (JSON.stringify(now[k]) === JSON.stringify(p[k])) { delete now[k]; setPending(now); }
      } catch (e) {
        return setStatus("err", "⚠ nincs mentve");
      }
    }
    return Object.keys(pending()).length ? flush() : setStatus("", "✓ mentve");
  }

  function queue(key, url, body, delay = 900) {
    const p = pending();
    p[key] = { url, body };
    setPending(p);
    setStatus("dirty", "…");
    clearTimeout(timers.get(key));
    timers.set(key, setTimeout(flush, delay));
  }
  const saveNow = () => { timers.forEach(clearTimeout); flush(); };
  addEventListener("online", flush);
  addEventListener("pagehide", saveNow);
  document.addEventListener("visibilitychange", () => document.hidden && saveNow());
  setInterval(() => Object.keys(pending()).length && flush(), 15000);
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
