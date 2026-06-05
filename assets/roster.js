/* roster.js — homepage character roster, live from dnd-api.
 *
 * A player "claims" a character by filling the Player field on its sheet. Claimed
 * characters are shown explicitly here (with who claimed them) for quick access;
 * unclaimed ("available") ones live in the dropdown. Reflects renames/claims live
 * via the global WebSocket. If the API is unreachable, the static fallback markup
 * inside #roster is left in place.
 */
(function () {
  "use strict";

  var roster = document.getElementById("roster");
  var picker = document.getElementById("char-picker");
  if (!roster || !picker) return;

  function card(c) {
    var a = document.createElement("a");
    a.className = "char-card";
    a.href = c.url;
    var info = document.createElement("div");
    info.style.flex = "1";
    var nm = document.createElement("div");
    nm.className = "char-name";
    nm.textContent = c.name;
    var cls = document.createElement("div");
    cls.className = "char-class";
    cls.textContent = [c.epithet, c.class_level].filter(Boolean).join(" · ");
    info.appendChild(nm);
    info.appendChild(cls);
    var who = document.createElement("div");
    who.className = "claimed-by";
    who.textContent = "🛡 " + c.player;
    a.appendChild(info);
    a.appendChild(who);
    return a;
  }

  function render(list) {
    var claimed = list.filter(function (c) {
      return c.player;
    });
    var open = list.filter(function (c) {
      return !c.player;
    });

    picker.innerHTML = "";
    var first = document.createElement("option");
    first.value = "";
    first.textContent =
      open.length ? "— choose an available character —" : "— all characters claimed —";
    picker.appendChild(first);
    open.forEach(function (c) {
      var o = document.createElement("option");
      o.value = c.url;
      o.textContent = c.name + (c.class_level ? " — " + c.class_level : "");
      picker.appendChild(o);
    });

    roster.innerHTML = "";
    if (claimed.length) {
      claimed.forEach(function (c) {
        roster.appendChild(card(c));
      });
    } else {
      var p = document.createElement("p");
      p.className = "roster-empty";
      p.textContent =
        "No characters claimed yet — pick one from the menu above to begin.";
      roster.appendChild(p);
    }
  }

  picker.addEventListener("change", function () {
    if (picker.value) location.href = picker.value;
  });

  var t;
  function load() {
    fetch("/api/characters")
      .then(function (r) {
        return r.ok ? r.json() : null;
      })
      .then(function (d) {
        if (d && d.characters) render(d.characters);
      })
      .catch(function () {});
  }
  function debouncedLoad() {
    clearTimeout(t);
    t = setTimeout(load, 250);
  }

  // Live roster updates over the global channel, with a focus/poll fallback.
  function connect() {
    var ws;
    try {
      var proto = location.protocol === "https:" ? "wss:" : "ws:";
      ws = new WebSocket(proto + "//" + location.host + "/api/ws");
    } catch (e) {
      setTimeout(connect, 4000);
      return;
    }
    ws.onmessage = debouncedLoad;
    ws.onclose = function () {
      setTimeout(connect, 4000);
    };
    ws.onerror = function () {
      try {
        ws.close();
      } catch (e) {}
    };
  }

  window.addEventListener("focus", load);
  load();
  connect();
})();
