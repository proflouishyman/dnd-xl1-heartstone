/* sheet-sync.js — shared, persisted, realtime character-sheet editing.
 *
 * Loads per-character overrides from dnd-api, streams field-level edits over a
 * WebSocket so every viewer sees changes live (last-write-wins), and gates all
 * editing behind a pencil "edit mode" toggle. The same fields are read/written
 * by the clanker bot through the REST API, so this is just one more client.
 *
 * Field identity: every editable element carries data-field="<id>". Inputs and
 * textareas store their value in .value; tagged display leaves (data-editable)
 * store it in .textContent; the portrait <img data-field="portrait"> stores a
 * URL in .src.
 */
(function () {
  "use strict";

  var body = document.body;
  var CHAR =
    body.getAttribute("data-char") ||
    (location.pathname.split("/").pop() || "").replace(/\.html$/i, "").toLowerCase();
  if (!CHAR) return;

  var API = "/api/characters/" + encodeURIComponent(CHAR);

  // ── Generic tagging: every text-leaf element that the injector didn't already
  //    give a semantic data-field gets a deterministic cell_<N> id from a
  //    document-order walk. The baked HTML is identical for every viewer, so the
  //    ids line up across clients and reloads — this is what makes "every
  //    element" editable (incl. the THAC0 / saving-throw / thief / turn-undead
  //    reference tables) without a build-time DOM parser. ──
  function autoTag() {
    var sel = "td,th,li,p,span,div,h1,h2,h3,h4,h5,h6,b,i,em,strong,caption,dt,dd";
    var n = 0;
    document.body.querySelectorAll(sel).forEach(function (el) {
      if (el.hasAttribute("data-field")) return; // already semantic
      if (el.children.length > 0) return; // not a pure text leaf
      if (el.closest("#sync-toolbar")) return; // our own chrome
      if (!el.textContent || !el.textContent.trim()) return; // empty
      el.setAttribute("data-field", "cell_" + n++);
      el.setAttribute("data-editable", "");
    });
  }
  autoTag();

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

  // ── Apply remote changes (with a focus-guard so we never yank a field
  //    the local user is actively typing in; queued values land on blur) ──
  var pending = {};
  function applyRemote(field, value) {
    var el = fields[field];
    if (!el) return;
    if (document.activeElement === el) {
      pending[field] = value;
      return;
    }
    setValue(el, value);
  }
  function applySnapshot(data) {
    if (!data) return;
    Object.keys(data).forEach(function (f) {
      applyRemote(f, data[f]);
    });
  }
  document.addEventListener("focusout", function (e) {
    var t = e.target;
    var f = t && t.getAttribute && t.getAttribute("data-field");
    if (f && f in pending) {
      setValue(fields[f], pending[f]);
      delete pending[f];
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
  Object.keys(fields).forEach(function (f) {
    var el = fields[f];
    if (el.tagName === "IMG") return; // portrait uses upload, below
    el.addEventListener("input", function () {
      onEdit(el);
    });
    el.addEventListener("change", function () {
      onEdit(el);
    });
  });

  // ── Toolbar (pencil edit-mode toggle + connection dot) ──
  var dot, pencil, editing = false;
  function setDot(on) {
    if (dot) dot.className = "sync-dot" + (on ? " on" : "");
  }
  function setEditing(on) {
    editing = on;
    body.classList.toggle("edit-mode", on);
    document.querySelectorAll("[data-field]").forEach(function (el) {
      if (isFormField(el)) el.readOnly = !on;
      else if (el.hasAttribute("data-editable")) el.contentEditable = on ? "true" : "false";
    });
    if (pencil) {
      pencil.textContent = on ? "✓" : "✎";
      pencil.title = on ? "Apply & exit edit mode" : "Edit this sheet";
      pencil.classList.toggle("active", on);
    }
  }
  function buildToolbar() {
    var bar = document.createElement("div");
    bar.id = "sync-toolbar";
    dot = document.createElement("span");
    dot.className = "sync-dot";
    dot.title = "Live-sync connection";
    pencil = document.createElement("button");
    pencil.type = "button";
    pencil.className = "sync-pencil";
    pencil.textContent = "✎";
    pencil.title = "Edit this sheet";
    pencil.addEventListener("click", function () {
      setEditing(!editing);
    });
    bar.appendChild(dot);
    bar.appendChild(pencil);
    body.appendChild(bar);
  }

  // ── Portrait replacement (edit mode → file picker → upload) ──
  function wirePortrait() {
    var img = fields["portrait"];
    if (!img) return;
    img.title = "Click to change portrait (in edit mode)";
    var picker = document.createElement("input");
    picker.type = "file";
    picker.accept = "image/*";
    picker.style.display = "none";
    body.appendChild(picker);
    img.addEventListener("click", function () {
      if (editing) picker.click();
    });
    picker.addEventListener("change", function () {
      var f = picker.files && picker.files[0];
      if (!f) return;
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
  buildToolbar();
  wirePortrait();
  setEditing(false); // start locked (view mode)
  fetch(API)
    .then(function (r) {
      return r.ok ? r.json() : {};
    })
    .then(applySnapshot)
    .catch(function () {});
  connect();
})();
