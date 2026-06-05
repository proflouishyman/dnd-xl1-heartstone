/* sheet-sync.js — shared, persisted, realtime character-sheet editing.
 *
 * Every tagged field (data-field) is directly click-to-edit — no edit mode. Edits
 * stream field-level over a WebSocket so every viewer sees them live (last-write-
 * wins), persist in dnd-api, and are the same fields the clanker bot reads/writes.
 *
 * Field identity: data-field="<id>". Inputs/textarea store their value in .value;
 * tagged display leaves (data-editable) are contenteditable and store .textContent;
 * the portrait <img data-field="portrait"> stores a URL in .src (replaced via upload).
 *
 * Renaming: when the character's `name` changes, the page rewrites its own URL to
 * /characters/<slug-of-name>.html (reload-safe — nginx + dnd-api resolve the vanity
 * slug back to this sheet) and updates the title. The immutable id (data-char) never
 * changes; it stays the storage key and WS channel.
 */
(function () {
  "use strict";

  var body = document.body;
  var CHAR =
    body.getAttribute("data-char") ||
    (location.pathname.split("/").pop() || "").replace(/\.html$/i, "").toLowerCase();
  if (!CHAR) return;

  var API = "/api/characters/" + encodeURIComponent(CHAR);

  // field_id -> element
  var fields = {};
  document.querySelectorAll("[data-field]").forEach(function (el) {
    fields[el.getAttribute("data-field")] = el;
  });

  function isFormField(el) {
    return el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA");
  }
  function getValue(el) {
    if (el.tagName === "IMG") return el.getAttribute("src");
    return isFormField(el) ? el.value : el.textContent;
  }
  // Programmatic sets here never fire 'input'/'change', so remote applies don't echo.
  function setValue(el, v) {
    if (el.tagName === "IMG") {
      if (v) el.src = v;
      return;
    }
    if (isFormField(el)) el.value = v == null ? "" : v;
    else el.textContent = v == null ? "" : v;
  }

  // ── Vanity URL (mirror of the backend slugify) ──
  function slugify(s) {
    return String(s == null ? "" : s)
      .toLowerCase()
      .replace(/[^a-z0-9_-]+/g, "-")
      .replace(/-+/g, "-")
      .replace(/^-|-$/g, "");
  }
  var knownIds = null; // Set of all character ids, for vanity-slug collision guard
  function reconcileURL() {
    var nameEl = fields["name"];
    if (!nameEl) return;
    var slug = slugify(getValue(nameEl));
    if (!slug) return;
    // Don't claim a vanity slug that is a *different* character's id (its static file).
    if (knownIds && knownIds.has(slug) && slug !== CHAR) slug = CHAR;
    var want = "/characters/" + slug + ".html";
    if (location.pathname !== want) {
      try {
        history.replaceState(null, "", want + location.search + location.hash);
      } catch (e) {}
    }
    var nm = getValue(nameEl);
    if (nm) document.title = nm + " — XL-1 Quest for the Heartstone";
  }

  // ── Apply remote changes (focus-guard: never yank a field being typed in;
  //    queued values land on blur) ──
  var pending = {};
  function applyRemote(field, value) {
    var el = fields[field];
    if (!el) return;
    if (document.activeElement === el) {
      pending[field] = value;
      return;
    }
    setValue(el, value);
    if (field === "name") reconcileURL();
  }
  function applySnapshot(data) {
    if (data)
      Object.keys(data).forEach(function (f) {
        applyRemote(f, data[f]);
      });
    reconcileURL();
  }
  document.addEventListener("focusout", function (e) {
    var t = e.target;
    var f = t && t.getAttribute && t.getAttribute("data-field");
    if (f && f in pending) {
      setValue(fields[f], pending[f]);
      delete pending[f];
      if (f === "name") reconcileURL();
    } else if (f === "name") {
      reconcileURL(); // settle the URL after a local rename
    }
  });

  // ── WebSocket transport (with reconnect) ──
  var ws = null,
    wsReady = false,
    backoff = 1000;
  function wsUrl() {
    var proto = location.protocol === "https:" ? "wss:" : "ws:";
    return proto + "//" + location.host + "/api/ws/" + encodeURIComponent(CHAR);
  }
  function connect() {
    try {
      ws = new WebSocket(wsUrl());
    } catch (e) {
      scheduleReconnect();
      return;
    }
    ws.onopen = function () {
      wsReady = true;
      backoff = 1000;
      setDot(true);
    };
    ws.onclose = function () {
      wsReady = false;
      setDot(false);
      scheduleReconnect();
    };
    ws.onerror = function () {
      try {
        ws.close();
      } catch (e) {}
    };
    ws.onmessage = function (ev) {
      var m;
      try {
        m = JSON.parse(ev.data);
      } catch (e) {
        return;
      }
      if (m.type === "snapshot") applySnapshot(m.data);
      else if (m.type === "update") applyRemote(m.field, m.value);
    };
  }
  function scheduleReconnect() {
    setTimeout(connect, backoff);
    backoff = Math.min(backoff * 2, 15000);
  }
  function send(field, value) {
    pulse();
    if (ws && wsReady) {
      try {
        ws.send(JSON.stringify({ field: field, value: value }));
        return;
      } catch (e) {}
    }
    var o = {};
    o[field] = value;
    fetch(API, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(o),
    }).catch(function () {});
  }

  // ── Emit local edits (debounced per field) ──
  var timers = {};
  function onEdit(el) {
    var f = el.getAttribute("data-field");
    if (!f) return;
    clearTimeout(timers[f]);
    timers[f] = setTimeout(function () {
      send(f, getValue(el));
    }, 200);
  }

  // ── Make fields editable (always — no mode toggle) and wire emit ──
  Object.keys(fields).forEach(function (f) {
    var el = fields[f];
    if (el.tagName === "IMG") return; // portrait uses upload, below
    if (el.hasAttribute("data-editable") && !isFormField(el)) el.contentEditable = "true";
    el.addEventListener("input", function () {
      onEdit(el);
    });
    el.addEventListener("change", function () {
      onEdit(el);
    });
  });

  // ── Tiny live-sync status dot (non-interactive) ──
  var dot;
  function setDot(on) {
    if (dot) dot.className = "sync-dot" + (on ? " on" : "");
  }
  var pulseT;
  function pulse() {
    if (!dot) return;
    dot.classList.add("saving");
    clearTimeout(pulseT);
    pulseT = setTimeout(function () {
      dot.classList.remove("saving");
    }, 400);
  }
  function buildStatus() {
    var bar = document.createElement("div");
    bar.id = "sync-status";
    bar.title = "Live edits — changes save and sync to everyone automatically";
    dot = document.createElement("span");
    dot.className = "sync-dot";
    bar.appendChild(dot);
    body.appendChild(bar);
  }

  // ── Portrait replacement (click → file picker → upload) ──
  function wirePortrait() {
    var img = fields["portrait"];
    if (!img) return;
    img.title = "Click to change portrait";
    var picker = document.createElement("input");
    picker.type = "file";
    picker.accept = "image/*";
    picker.style.display = "none";
    body.appendChild(picker);
    img.addEventListener("click", function () {
      picker.click();
    });
    picker.addEventListener("change", function () {
      var f = picker.files && picker.files[0];
      if (!f) return;
      pulse();
      var fd = new FormData();
      fd.append("file", f);
      fetch(API + "/portrait", { method: "PUT", body: fd })
        .then(function (r) {
          return r.ok ? r.json() : null;
        })
        .then(function (res) {
          if (res && res.portrait) img.src = res.portrait;
          picker.value = "";
        })
        .catch(function () {});
    });
  }

  // ── Boot ──
  buildStatus();
  wirePortrait();
  // Learn all character ids (vanity-slug collision guard), then settle the URL.
  fetch("/api/characters")
    .then(function (r) {
      return r.ok ? r.json() : null;
    })
    .then(function (d) {
      if (d && d.characters) {
        knownIds = new Set(
          d.characters.map(function (c) {
            return c.id;
          })
        );
        reconcileURL();
      }
    })
    .catch(function () {});
  fetch(API)
    .then(function (r) {
      return r.ok ? r.json() : {};
    })
    .then(applySnapshot)
    .catch(function () {});
  connect();
})();
