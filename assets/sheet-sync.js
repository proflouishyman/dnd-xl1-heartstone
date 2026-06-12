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
  function isSlotTrack(el) {
    return el && el.classList && el.classList.contains("slot-track");
  }
  function isCondTrack(el) {
    return el && el.classList && el.classList.contains("conditions-track");
  }
  function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch];
    });
  }
  function getValue(el) {
    if (el.tagName === "IMG") return el.getAttribute("src");
    if (isSlotTrack(el)) return el._used || [];
    if (isCondTrack(el)) return el._conds || [];
    return isFormField(el) ? el.value : el.textContent;
  }
  // Programmatic sets here never fire 'input'/'change', so remote applies don't echo.
  function setValue(el, v) {
    if (el.tagName === "IMG") {
      if (v) el.src = v;
      return;
    }
    if (isSlotTrack(el)) {
      renderSlots(el, v);
      return;
    }
    if (isCondTrack(el)) {
      renderConditions(el, v);
      return;
    }
    if (isFormField(el)) el.value = v == null ? "" : v;
    else el.textContent = v == null ? "" : v;
  }

  // ── Spell-slot pip readout (data-field="spell_slots_used") ──
  // Maxima are static (data-max="3,2,2,1"); `used` arrives live over the same WS
  // channel as every other field. remaining = max − used, recomputed client-side.
  function _ints(v) {
    if (Array.isArray(v)) return v.map(function (x) { return parseInt(x, 10) || 0; });
    if (typeof v === "string" && v) {
      try {
        var j = JSON.parse(v);
        if (Array.isArray(j)) return j.map(function (x) { return parseInt(x, 10) || 0; });
      } catch (e) {}
      return v.split(/[,/]/).map(function (x) { return parseInt(x, 10) || 0; });
    }
    return [];
  }
  function renderSlots(el, used) {
    var max = _ints(el.getAttribute("data-max"));
    var u = _ints(used);
    // Clamp + remember the authoritative used vector for click math.
    el._used = max.map(function (m, i) { return Math.max(0, Math.min(u[i] || 0, m)); });
    var rows = el.querySelector(".slot-rows") || el;
    var html = "";
    for (var i = 0; i < max.length; i++) {
      var m = max[i] || 0;
      if (m <= 0) continue;
      var remain = m - el._used[i];
      var pips = "";
      for (var k = 0; k < m; k++) {
        var on = k < remain;
        pips +=
          '<span class="pip' + (on ? " on" : "") + '" data-lvl="' + i + '">' +
          (on ? "●" : "○") + "</span>";
      }
      html +=
        '<div class="slot-row"><span class="slot-lvl">L' + (i + 1) + "</span>" +
        '<span class="pips">' + pips + "</span>" +
        '<span class="slot-num">' + remain + "/" + m + "</span></div>";
    }
    rows.innerHTML = html;
  }
  function wireSlotTrack(el) {
    renderSlots(el, null); // initial all-available, until the snapshot lands
    el.addEventListener("click", function (e) {
      var pip = e.target && e.target.closest && e.target.closest(".pip");
      if (!pip || !el.contains(pip)) return;
      var lvl = parseInt(pip.getAttribute("data-lvl"), 10);
      var max = _ints(el.getAttribute("data-max"));
      var used = (el._used || []).slice();
      // Click an available pip to spend a slot; a spent pip to restore one.
      var delta = pip.classList.contains("on") ? 1 : -1;
      used[lvl] = Math.max(0, Math.min((used[lvl] || 0) + delta, max[lvl] || 0));
      renderSlots(el, used); // optimistic local render
      send("spell_slots_used", el._used); // persist + broadcast (clamped vector)
    });
  }

  // ── Conditions chip readout (data-field="conditions") ──
  // The bot writes a JSON list [{name, turns?, source?}] and counts timed ones down on
  // /turn; render chips live and let a table-side ✕ (clear) or the add-input (add) edit
  // the same persisted field. Sending null on the last clear deletes the override.
  function _condList(v) {
    if (Array.isArray(v)) return v;
    if (typeof v === "string" && v) {
      try {
        var j = JSON.parse(v);
        if (Array.isArray(j)) return j;
      } catch (e) {}
    }
    return [];
  }
  function renderConditions(el, list) {
    el._conds = _condList(list).filter(function (c) {
      return c && c.name;
    });
    var box = el.querySelector(".cond-chips") || el;
    var html = "";
    for (var i = 0; i < el._conds.length; i++) {
      var c = el._conds[i];
      var t =
        c.turns != null && c.turns !== ""
          ? '<span class="cond-turns">' + escapeHtml(c.turns) + "t</span>"
          : "";
      html +=
        '<span class="cond-chip">' +
        escapeHtml(c.name) +
        " " +
        t +
        '<span class="cond-x" data-i="' + i + '" title="clear">✕</span></span>';
    }
    box.innerHTML = html;
  }
  function wireCondTrack(el) {
    renderConditions(el, []); // empty until the snapshot lands
    el.addEventListener("click", function (e) {
      var x = e.target && e.target.closest && e.target.closest(".cond-x");
      if (!x || !el.contains(x)) return;
      var i = parseInt(x.getAttribute("data-i"), 10);
      var list = (el._conds || []).slice();
      if (i >= 0 && i < list.length) {
        list.splice(i, 1);
        renderConditions(el, list); // optimistic
        send("conditions", list.length ? list : null); // null deletes the override
      }
    });
    var input = el.querySelector(".cond-add");
    if (input) {
      input.addEventListener("keydown", function (e) {
        if (e.key !== "Enter") return;
        var name = input.value.trim();
        if (!name) return;
        var list = (el._conds || []).slice();
        list.push({ name: name });
        input.value = "";
        renderConditions(el, list);
        send("conditions", list);
      });
    }
  }

  // ── XP → next-level progress bar (read-only; reads the synced `xp` scalar) ──
  // Floor/next are baked per character (data-floor/data-next from the BECMI table);
  // the live xp value comes from the `xp` field. remaining recomputes client-side.
  function _xpNum(s) {
    var n = parseInt(String(s == null ? "" : s).replace(/[^\d-]/g, ""), 10);
    return isNaN(n) ? 0 : n;
  }
  function renderXpBar(bar) {
    var floor = _xpNum(bar.getAttribute("data-floor"));
    var nextAttr = bar.getAttribute("data-next");
    var xpEl = fields["xp"];
    var xp = xpEl ? _xpNum(getValue(xpEl)) : floor;
    var fill = bar.querySelector(".xp-fill");
    var label = bar.parentNode && bar.parentNode.querySelector(".xp-bar-label");
    if (nextAttr == null || nextAttr === "") {
      bar.classList.add("maxed");
      if (fill) fill.style.width = "100%";
      if (label) label.textContent = xp.toLocaleString() + " XP · max level";
      return;
    }
    var next = _xpNum(nextAttr);
    var span = next - floor;
    var pct = span > 0 ? Math.max(0, Math.min(1, (xp - floor) / span)) : 0;
    if (fill) fill.style.width = (pct * 100).toFixed(1) + "%";
    if (label)
      label.textContent = xp.toLocaleString() + " / " + next.toLocaleString();
  }
  function renderXpBars() {
    document.querySelectorAll(".xp-bar").forEach(renderXpBar);
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
    if (field === "xp") renderXpBars();
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
    if (isSlotTrack(el)) return; // pip readout has its own click wiring (below)
    if (isCondTrack(el)) return; // conditions chips have their own wiring (below)
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
  document.querySelectorAll(".slot-track").forEach(wireSlotTrack);
  document.querySelectorAll(".conditions-track").forEach(wireCondTrack);
  if (fields["xp"]) fields["xp"].addEventListener("input", renderXpBars);
  renderXpBars(); // initial paint from the baked value; snapshot refines it
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
