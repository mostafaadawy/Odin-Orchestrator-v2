"""
Shared JSON data store for Odin's new subsystems (projects, agents, scopes, models,
schedules, activity). One small, dependency-free helper so every module persists the same way
and survives restarts. All data lives under data/ (gitignored).
"""
from __future__ import annotations

import json
import pathlib
import threading
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
WS = ROOT / "workspace"

_LOCK = threading.RLock()

# STRUCTURE REMAP — these top-level stores have been MOVED out of the flat data/ into the workspace
# structure. Every reader goes through _p(), so this one table repoints all of them to the new homes.
_REMAP = {
    # core registry (→ shared/core-registry ; becomes odin_core_iso DB later)
    "projects.json":        WS / "shared" / "core-registry" / "projects.json",
    "company_agents.json":  WS / "shared" / "core-registry" / "company_agents.json",
    "connectors.json":      WS / "shared" / "core-registry" / "connectors.json",
    "connector_keys.json":  WS / "shared" / "core-registry" / "connector_keys.json",
    # config
    "models.json":          WS / "shared" / "config" / "models.json",
    # utils (tools/settings, more utility than config)
    "soc_settings.json":    WS / "shared" / "utils" / "soc_settings.json",
    "hubspot_scopes.json":  WS / "shared" / "utils" / "hubspot_scopes.json",
    # chat/scope plumbing (→ chats)
    "chat_registry.json":   WS / "chats" / "chat_registry.json",
    "_seq_counters.json":   WS / "chats" / "_seq_counters.json",
    # anchor layer
    "anchor_config.json":   WS / "anchor-layer" / "anchor_config.json",
    "anchor_manage.json":   WS / "anchor-layer" / "anchor_manage.json",
    "anchor_queue.json":    WS / "anchor-layer" / "anchor_queue.json",
    "anchor_sync.json":     WS / "anchor-layer" / "anchor_sync.json",
}


def _p(*parts: str) -> pathlib.Path:
    rel = "/".join(parts)
    if rel in _REMAP:
        return _REMAP[rel]
    # ALL per-project data (agents.json, skills, soc/zoom artifacts, …) lives under workspace/projects/<pid>/.
    # Handles both read_json("projects/<pid>/x") (single string) and ensure_dir("projects", pid, ...) (parts).
    if rel.startswith("projects/"):
        return WS.joinpath(*parts)
    # chat/scope layer → workspace/chats/ : the pools (scopes/) and their attachments (scope_files/)
    if rel == "scope_files" or rel.startswith("scope_files/"):
        sub = rel[len("scope_files"):].lstrip("/")
        return (WS / "chats" / "files" / sub) if sub else (WS / "chats" / "files")
    if rel == "scopes" or rel.startswith("scopes/"):
        sub = rel[len("scopes"):].lstrip("/")
        return (WS / "chats" / "scopes" / sub) if sub else (WS / "chats" / "scopes")
    return DATA.joinpath(*parts)


def ensure_dir(*parts: str) -> pathlib.Path:
    d = _p(*parts)
    d.mkdir(parents=True, exist_ok=True)
    return d


# PER-PROJECT SHARDED stores — one flat blob keyed by project id, now split into each project's
# workspace/projects/<pid>/jsons/<file>. store transparently splits on write and merges on read, so
# callers keep using read_json/write_json exactly as before. (mode, container_key)
_PROJ = ROOT / "workspace" / "projects"
_SHARDED = {
    "main_tasks.json":    ("dict", None),           # {pid: value}
    "operations.json":    ("list", None),           # [ {pid,...} ]
    "run_timings.json":   ("list", None),           # [ {pid,...} ]
    "approvals.json":     ("container", "items"),   # {items:[{pid,...}]}
    "schedules.json":     ("container", "tasks"),   # {tasks:[{pid,...}]}
    "notifications.json": ("container", "items"),   # {items:[{pid,...}]}
}


def _real_pids() -> set:
    try:
        return {p.name for p in _PROJ.iterdir() if p.is_dir() and not p.name.startswith("_")}
    except Exception:
        return set()


def _shard_dir(pid: str) -> pathlib.Path:
    tgt = pid if (pid and pid in _real_pids()) else "_shared"
    d = _PROJ / tgt / "data" / "jsons"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _read_sharded(fname: str):
    mode, ck = _SHARDED[fname]
    parts = []
    for pd in _PROJ.glob("*/data/jsons/" + fname):
        try:
            parts.append(json.loads(pd.read_text(encoding="utf-8")))
        except Exception:
            pass
    if mode == "dict":
        out = {}
        for v in parts:
            if isinstance(v, dict):
                out.update(v)
        return out
    if mode == "list":
        out = []
        for v in parts:
            if isinstance(v, list):
                out.extend(v)
        return out
    arr = []  # container
    for v in parts:
        if isinstance(v, dict):
            arr.extend(v.get(ck, []))
    return {ck: arr}


def _write_sharded(fname: str, data) -> None:
    mode, ck = _SHARDED[fname]
    real = _real_pids()

    def tgt(pid):
        return pid if (pid and pid in real) else "_shared"

    buckets: dict = {}   # keyed by TARGET dir (real pid or "_shared") so non-real items ACCUMULATE, not overwrite
    if mode == "dict":
        for pid, val in (data or {}).items():
            buckets.setdefault(tgt(pid), {})[pid] = val
    elif mode == "list":
        for it in (data or []):
            pid = it.get("pid") if isinstance(it, dict) else None
            buckets.setdefault(tgt(pid), []).append(it)
    else:
        for it in (data or {}).get(ck, []):
            pid = it.get("pid") if isinstance(it, dict) else None
            buckets.setdefault(tgt(pid), {}).setdefault(ck, []).append(it)
    with _LOCK:
        for pd in _PROJ.glob("*/data/jsons/" + fname):
            try:
                pd.unlink()
            except Exception:
                pass
        for target, content in buckets.items():
            d = _PROJ / target / "data" / "jsons"
            d.mkdir(parents=True, exist_ok=True)
            (d / fname).write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(rel: str, default):
    if rel in _SHARDED:
        v = _read_sharded(rel)
        return v if v not in (None, {}, []) else default
    p = _p(rel)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(rel: str, data) -> None:
    if rel in _SHARDED:
        _write_sharded(rel, data)
        return
    p = _p(rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(p)
    try:  # Phase-3 middleware: keep odin_core_iso in lockstep (best-effort, never breaks the write)
        import workspace_mw; workspace_mw.sync_row(str(p))
    except Exception:
        pass


def now() -> float:
    return time.time()
