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
from fastapi.responses import FileResponse, JSONResponse

DATA_DIR = Path(os.environ.get("DND_DATA_DIR", "/data"))
PORTRAIT_DIR = DATA_DIR / "portraits"
NAME_RE = re.compile(r"^[a-z0-9_-]{1,64}$")
FLUSH_DELAY = 0.25  # seconds — debounce window for write-behind
ALLOWED_IMG = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}

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


def _valid(name: str) -> str:
    if not NAME_RE.match(name):
        raise HTTPException(status_code=400, detail="invalid character name")
    return name


def _path(name: str) -> Path:
    return DATA_DIR / f"{name}.json"


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
    if updates:
        _schedule_flush(name)


async def _apply_and_broadcast(name: str, updates: dict, *, exclude: WebSocket | None = None) -> None:
    _apply(name, updates)
    for field, value in updates.items():
        if isinstance(field, str):
            await _broadcast(name, field, value, exclude=exclude)


# ── REST ─────────────────────────────────────────────────────────────────────
@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.get("/characters")
async def list_characters():
    names = sorted(p.stem for p in DATA_DIR.glob("*.json")) if DATA_DIR.exists() else []
    return {"characters": names}


@app.get("/characters/{name}")
async def get_character(name: str):
    return _overrides(_valid(name))


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


@app.exception_handler(HTTPException)
async def _http_exc(_, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
