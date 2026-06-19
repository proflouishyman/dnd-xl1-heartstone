"""dnd-api — shared, persisted, realtime character-sheet state for dnd.haldo.org.

Each character sheet is a static HTML page; this service stores per-character
*overrides* (a flat ``{field_id: value}`` map) in the dnd_data docker volume and
streams field-level changes to every connected viewer over a WebSocket. The same
state is exposed as a plain REST API so the clanker Discord bot can read/modify
sheets (roll with modifiers, apply damage, manage inventory).

Conflict model is field-level last-write-wins; a single uvicorn worker keeps the
in-memory map authoritative and serializes the debounced write-behind to disk.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response

DATA_DIR = Path(os.environ.get("DND_DATA_DIR", "/data"))
PORTRAIT_DIR = DATA_DIR / "portraits"
NAME_RE = re.compile(r"^[a-z0-9_-]{1,64}$")
FLUSH_DELAY = 0.25  # seconds — debounce window for write-behind
ALLOWED_IMG = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}

# Base (pre-rolled) character values, baked next to this module by gen_manifest.py.
# Player overrides merge on top; this is what lets the roster show class/race even
# for an untouched sheet, and lets /resolve map a renamed character back to its id.
try:
    MANIFEST = json.loads((Path(__file__).resolve().parent / "manifest.json").read_text(encoding="utf-8"))
except Exception:
    MANIFEST = {}

# Fields that affect the homepage roster — changes to these ping the global channel.
SUMMARY_FIELDS = {"name", "epithet", "class_level", "race", "alignment", "player"}


def slugify(s) -> str:
    s = re.sub(r"[^a-z0-9_-]+", "-", str(s).lower())
    return re.sub(r"-+", "-", s).strip("-")


app = FastAPI(title="dnd-api", version="1.0")

# clanker may call this directly (container-internal) or via the proxy; allow it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory state ──────────────────────────────────────────────────────────
_state: dict[str, dict] = {}          # name -> {field_id: value}
_loaded: set[str] = set()             # names whose JSON has been read from disk
_subs: dict[str, set[WebSocket]] = {} # name -> connected websockets
_flush_tasks: dict[str, asyncio.Task] = {}
_global_subs: set[WebSocket] = set()  # homepage roster listeners (global /ws)
_name_index: dict[str, str] = {}      # vanity name-slug -> character id
_name_index_ready = False


def _valid(name: str) -> str:
    if not NAME_RE.match(name):
        raise HTTPException(status_code=400, detail="invalid character name")
    return name


def _path(name: str) -> Path:
    return DATA_DIR / f"{name}.json"


def _index_name(name, cid: str) -> None:
    sl = slugify(name)
    if sl:
        _name_index[sl] = cid


def _ensure_name_index() -> None:
    """Build the vanity-slug → id map once: manifest base names + persisted renames."""
    global _name_index_ready
    if _name_index_ready:
        return
    for cid, base in MANIFEST.items():
        _index_name(base.get("name", cid), cid)
    if DATA_DIR.exists():
        for p in DATA_DIR.glob("*.json"):
            try:
                ov = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if ov.get("name"):
                _index_name(ov["name"], p.stem)
    _name_index_ready = True


def _resolve_id(slug: str):
    """Map a URL slug to a character id: a real id wins; else a renamed character."""
    if slug in MANIFEST:
        return slug
    _ensure_name_index()
    return _name_index.get(slug)


def _card_slug(name, cid: str) -> str:
    """Homepage roster link target for a character. Use the pretty vanity slug of
    `name`, UNLESS that slug collides with ANOTHER character's id — a character
    renamed e.g. "Kelek" (slug "kelek") must link to its OWN /characters/<id>.html,
    not /characters/kelek.html, which nginx serves as the real `kelek` character's
    static sheet (bypassing the vanity resolver). Falls back to the id, whose static
    page always resolves correctly. Mirrors sheet-sync.js's vanity-collision guard."""
    slug = slugify(name)
    if not slug or (slug in MANIFEST and slug != cid):
        return cid
    return slug


def _overrides(name: str) -> dict:
    """Return the live overrides dict for a character, loading from disk once."""
    if name not in _loaded:
        try:
            _state[name] = json.loads(_path(name).read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            _state[name] = {}
        _loaded.add(name)
    return _state.setdefault(name, {})


def _write_now(name: str) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _path(name).with_suffix(".json.tmp")
    tmp.write_text(json.dumps(_state.get(name, {}), ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, _path(name))


def _schedule_flush(name: str) -> None:
    old = _flush_tasks.get(name)
    if old and not old.done():
        old.cancel()

    async def _flush() -> None:
        try:
            await asyncio.sleep(FLUSH_DELAY)
            await asyncio.to_thread(_write_now, name)
        except asyncio.CancelledError:
            pass

    _flush_tasks[name] = asyncio.create_task(_flush())


async def _broadcast(name: str, field: str, value, *, exclude: WebSocket | None = None) -> None:
    msg = {"type": "update", "field": field, "value": value}
    for ws in list(_subs.get(name, ())):
        if ws is exclude:
            continue
        try:
            await ws.send_json(msg)
        except Exception:
            _subs.get(name, set()).discard(ws)


def _apply(name: str, updates: dict, *, exclude: WebSocket | None = None) -> None:
    """Merge updates into state, schedule a flush, and broadcast each field."""
    ov = _overrides(name)
    for field, value in updates.items():
        if not isinstance(field, str):
            continue
        if value is None:
            ov.pop(field, None)
        else:
            ov[field] = value
            if field == "name":
                _index_name(value, name)
    if updates:
        _schedule_flush(name)


async def _broadcast_summary(cid: str) -> None:
    """Tell homepage-roster listeners that a character's summary fields changed."""
    msg = {"type": "summary-changed", "id": cid}
    for ws in list(_global_subs):
        try:
            await ws.send_json(msg)
        except Exception:
            _global_subs.discard(ws)


async def _apply_and_broadcast(name: str, updates: dict, *, exclude: WebSocket | None = None) -> None:
    _apply(name, updates)
    touched_summary = False
    for field, value in updates.items():
        if isinstance(field, str):
            await _broadcast(name, field, value, exclude=exclude)
            if field in SUMMARY_FIELDS:
                touched_summary = True
    if touched_summary:
        await _broadcast_summary(name)


# ── REST ─────────────────────────────────────────────────────────────────────
@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.get("/characters")
async def list_characters():
    """Homepage roster: each character's current summary (manifest base + overrides)."""
    out = []
    for cid, base in MANIFEST.items():
        ov = _overrides(cid)

        def val(key, default=""):
            v = ov.get(key)
            return v if v not in (None, "") else base.get(key, default)

        name = val("name", cid)
        out.append({
            "id": cid,
            "name": name,
            "epithet": val("epithet"),
            "class_level": val("class_level"),
            "race": val("race"),
            "alignment": val("alignment"),
            "player": ov.get("player") or "",
            "url": f"/characters/{_card_slug(name, cid)}.html",
        })
    return {"characters": out}


@app.get("/resolve/characters/{slug}.html")
async def resolve_sheet(slug: str):
    """Map a vanity URL slug back to its static sheet via nginx X-Accel-Redirect.

    Static id files (e.g. /characters/kelek.html) are served directly by nginx and
    never reach here; only renamed characters' vanity URLs do."""
    cid = _resolve_id(slug.lower())
    if not cid:
        raise HTTPException(status_code=404, detail="unknown character")
    return Response(status_code=200, headers={"X-Accel-Redirect": f"/_sheet/{cid}.html"})


@app.get("/characters/{name}")
async def get_character(name: str):
    return _overrides(_valid(name))


# ── Enriched read for clanker: base (manifest) merged with overrides ──────────
_ABILITY_FIELD = {"STR": "str_score", "DEX": "dex_score", "INT": "int_score",
                  "CON": "con_score", "WIS": "wis_score", "CHA": "cha_score"}
_COIN_KEYS = ("pp", "gp", "ep", "sp", "cp")


def _as_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@app.get("/characters/{name}/full")
async def get_character_full(name: str):
    """Base (enriched manifest) merged with live overrides, normalized for clanker.

    GET /characters/{name} returns *only* overrides; the bot also needs the
    pre-rolled base (stats, thac0, saves, weapons, hp_max…). This merges them and
    resolves the common mutable fields (hp_current, ac, coins, inventory,
    memorized spells) into one authoritative 'current sheet'.
    """
    name = _valid(name)
    base = MANIFEST.get(name, {})
    ov = _overrides(name)

    stats = dict(base.get("stats", {}))
    for ab, fid in _ABILITY_FIELD.items():
        if fid in ov:
            stats[ab] = _as_int(ov[fid], stats.get(ab))

    hp_max = _as_int(ov.get("hp_max"), _as_int(base.get("hp_max")))
    ac = _as_int(ov.get("ac"), _as_int(base.get("ac")))
    coins = {k: _as_int(ov.get(f"coin_{k}"), 0) for k in _COIN_KEYS}

    inv_rows = _as_int(base.get("inv_rows"), 20)
    inventory = []
    for n in range(1, inv_rows + 1):
        item = ov.get(f"inv_item_{n}")
        if item:
            charges = _as_int(ov.get(f"inv_charges_{n}"), None)
            inventory.append({
                "slot": n,
                "item": item,
                "qty": _as_int(ov.get(f"inv_qty_{n}"), 1),
                "notes": ov.get(f"inv_notes_{n}", ""),
                # Charges on a wand/rod/staff (None when the item isn't charged).
                "charges": charges,
            })

    memo_slots = _as_int(base.get("memo_slots"), 0)
    memorized = {n: ov[f"memo_{n}"] for n in range(1, memo_slots + 1)
                 if f"memo_{n}" in ov}

    # Daily spell-slot usage. `spell_slots` (from the manifest) is the per-level
    # max/day; `spell_slots_used` is a same-length override list of how many have
    # been expended today. Default to all-zero and clamp to the slot maxima so a
    # stale override can't exceed the budget. `spell_slots_remaining` is derived
    # for convenience (UI + the bot both consume it).
    spell_slots = base.get("spell_slots")
    spell_slots_used = None
    spell_slots_remaining = None
    if isinstance(spell_slots, list) and spell_slots:
        raw = ov.get("spell_slots_used")
        used = raw if isinstance(raw, list) else []
        spell_slots_used = [
            max(0, min(_as_int(used[i], 0) or 0, int(mx)))
            if i < len(used) else 0
            for i, mx in enumerate(spell_slots)
        ]
        spell_slots_remaining = [int(mx) - u for mx, u in zip(spell_slots, spell_slots_used)]

    # ── "Acquired" override sections (inject_acquired.py rows) ───────────────
    # Learned/added spells: surfaced as a `learned` list AND merged into the spellbook
    # (`spells`) under their level so the bot's _spell_level/casting just works. A row
    # with no level is listed but not merged (uncastable until the level is set).
    spells = {k: list(v) for k, v in (base.get("spells") or {}).items()}
    learned = []
    for n in range(1, _as_int(base.get("learn_rows"), 0) + 1):
        nm = ov.get(f"learn_spell_{n}")
        if not nm:
            continue
        lvl = _as_int(ov.get(f"learn_lvl_{n}"))
        learned.append({"slot": n, "name": nm, "level": lvl})
        if lvl:
            row = spells.setdefault(str(lvl), [])
            if nm not in row:
                row.append(nm)

    # Per-character magic items (name + description + optional charges).
    magic_items = []
    for n in range(1, _as_int(base.get("magic_rows"), 0) + 1):
        nm = ov.get(f"magic_item_{n}")
        if nm:
            magic_items.append({
                "slot": n, "name": nm,
                "desc": ov.get(f"magic_item_desc_{n}", ""),
                "charges": _as_int(ov.get(f"magic_item_charges_{n}")),
            })

    # Acquired weapons/armor appended onto the baked lists (never overwrite the base).
    weapons = list(base.get("weapons", []))
    for n in range(1, _as_int(base.get("weapon_rows"), 0) + 1):
        wn = ov.get(f"weapon_{n}")
        if wn:
            weapons.append(wn)
    armor = base.get("armor", "")
    extra_armor = [ov[f"armor_{n}"] for n in range(1, _as_int(base.get("armor_rows"), 0) + 1)
                   if ov.get(f"armor_{n}")]
    if extra_armor:
        armor = "; ".join(([armor] if armor else []) + extra_armor)

    def pick(field, default=None):
        v = ov.get(field)
        return v if v not in (None, "") else base.get(field, default)

    return {
        "id": name,
        "name": ov.get("name") or base.get("name", name),
        "class": base.get("class"),
        "level": base.get("level"),
        "class_level": pick("class_level", ""),
        "race": pick("race", ""),
        "alignment": pick("alignment", ""),
        "save_as": base.get("save_as", ""),
        "stats": stats,
        "ac": ac,
        "hp_max": hp_max,
        "hp_current": _as_int(ov.get("hp_current"), hp_max),
        "mv": _as_int(ov.get("mv"), _as_int(base.get("mv"))),
        "attacks": _as_int(ov.get("attacks"), _as_int(base.get("attacks"))),
        # XP: override if set, else the BECMI level floor from the manifest — so a
        # clanker award accumulates from the real value instead of starting at 0.
        "xp": _as_int(ov.get("xp"), _as_int(base.get("xp"), 0)),
        "xp_next": _as_int(base.get("xp_next")),
        "thac0": base.get("thac0"),
        "saves": base.get("saves", {}),
        "to_hit": base.get("to_hit", {}),
        "save_note": base.get("save_note", ""),
        "weapons": weapons,
        "armor": armor,
        "special": base.get("special", []),
        "spells": spells,
        "learned": learned,
        "magic_items": magic_items,
        "spell_slots": base.get("spell_slots"),
        "spell_slots_used": spell_slots_used,
        "spell_slots_remaining": spell_slots_remaining,
        "thief_skills": base.get("thief_skills"),
        "backstab": base.get("backstab"),
        "sweep": base.get("sweep", 0),
        "coins": coins,
        "inventory": inventory,
        "memorized": memorized,
        "inv_rows": inv_rows,
        "memo_slots": memo_slots,
        # "acquired" section sizes so the bot can find an empty row to write into
        "learn_rows": _as_int(base.get("learn_rows"), 0),
        "magic_rows": _as_int(base.get("magic_rows"), 0),
        "weapon_rows": _as_int(base.get("weapon_rows"), 0),
        "armor_rows": _as_int(base.get("armor_rows"), 0),
        "player": ov.get("player", ""),
        "overrides": ov,
    }


@app.patch("/characters/{name}")
async def patch_character(name: str, request: Request):
    name = _valid(name)
    try:
        updates = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="body must be JSON object")
    if not isinstance(updates, dict):
        raise HTTPException(status_code=400, detail="body must be a {field: value} object")
    await _apply_and_broadcast(name, updates)
    return _overrides(name)


@app.put("/characters/{name}/portrait")
async def put_portrait(name: str, file: UploadFile):
    name = _valid(name)
    ext = ALLOWED_IMG.get((file.content_type or "").lower())
    if not ext:
        raise HTTPException(status_code=415, detail=f"unsupported image type: {file.content_type}")
    PORTRAIT_DIR.mkdir(parents=True, exist_ok=True)
    # one portrait per character; drop any prior extension
    for old in PORTRAIT_DIR.glob(f"{name}.*"):
        old.unlink(missing_ok=True)
    dest = PORTRAIT_DIR / f"{name}{ext}"
    dest.write_bytes(await file.read())
    url = f"/api/characters/{name}/portrait?v={int(time.time())}"
    await _apply_and_broadcast(name, {"portrait": url})
    return {"portrait": url}


@app.get("/characters/{name}/portrait")
async def get_portrait(name: str):
    name = _valid(name)
    matches = sorted(PORTRAIT_DIR.glob(f"{name}.*")) if PORTRAIT_DIR.exists() else []
    if not matches:
        raise HTTPException(status_code=404, detail="no portrait override")
    return FileResponse(matches[0])


# ── WebSocket ────────────────────────────────────────────────────────────────
@app.websocket("/ws/{name}")
async def ws_character(ws: WebSocket, name: str):
    if not NAME_RE.match(name):
        await ws.close(code=1008)
        return
    await ws.accept()
    _subs.setdefault(name, set()).add(ws)
    await ws.send_json({"type": "snapshot", "data": _overrides(name)})
    try:
        while True:
            msg = await ws.receive_json()
            field = msg.get("field")
            if isinstance(field, str):
                await _apply_and_broadcast(name, {field: msg.get("value")}, exclude=ws)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        _subs.get(name, set()).discard(ws)


@app.websocket("/ws")
async def ws_global(ws: WebSocket):
    """Homepage roster channel: pushes {"type":"summary-changed","id":…} so the
    index refetches when any character's name/class/alignment/player changes."""
    await ws.accept()
    _global_subs.add(ws)
    try:
        while True:
            await ws.receive_text()  # clients don't send; keep the socket open
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        _global_subs.discard(ws)


@app.exception_handler(HTTPException)
async def _http_exc(_, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
