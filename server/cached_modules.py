"""
cached_modules.py — the Pool of Cached Modules, surfaced to role agents.

When a role agent starts a task, it FETCHES the pool for its role (+ Miscellaneous), reads each
module's metadata, and DECIDES for itself whether one matches the case — if so it configures and
runs it; if not, it works normally. The CTO does not use the pool; only role agents do.
"""
from __future__ import annotations

import json
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
POOL = ROOT / "workspace" / "shared" / "cached_modules"


def cache_enabled() -> bool:
    """The cache can be turned OFF (e.g. for the cached-vs-non-cached timing baseline)."""
    return os.environ.get("ODIN_DISABLE_CACHE") != "1"


def _role_dir(role: str) -> str:
    """Map a member name/role to a pool subfolder (DevOps/Frontend/Backend), else ''."""
    r = (role or "").lower()
    if "devops" in r or "cloud" in r or "infra" in r:
        return "DevOps"
    if "mobile" in r or "flutter" in r or "android" in r or "ios" in r:
        return "Mobile"
    # web UI + server/API + database are ONE role now (Fullstack)
    if any(k in r for k in ("full", "front", "ui", "back", "api", "server", "database", "db", "web", "stack")):
        return "Fullstack"
    return ""


def list_for_role(role: str) -> list:
    """Modules available to this role: its own folder + Miscellaneous. Returns metadata dicts."""
    out = []
    folders = [d for d in (_role_dir(role), "Miscellaneous") if d]
    for folder in folders:
        d = POOL / folder
        if not d.is_dir():
            continue
        for meta in sorted(d.glob("*.meta.json")):
            try:
                m = json.loads(meta.read_text(encoding="utf-8"))
                m["path"] = str((d / m.get("name", meta.stem.replace(".meta", ""))))
                m["folder"] = folder
                out.append(m)
            except Exception:
                continue
    return out


def index_text(role: str) -> str:
    """A compact, readable catalog of the pool for THIS role — handed to the agent so it can decide."""
    if not cache_enabled():
        return ""   # baseline run: no pool surfaced, agent works from scratch
    mods = list_for_role(role)
    if not mods:
        return ""
    lines = ["===== CACHED MODULES POOL (check here FIRST; reuse a proven module if one fits) ====="]
    for m in mods:
        inputs = ", ".join((m.get("inputs") or {}).keys())
        lines.append(
            f"- {m.get('name')}  [{m.get('status', '?')}]  ({m.get('folder')})\n"
            f"    what: {m.get('summary', '')}\n"
            f"    path: {m.get('path', '')}\n"
            f"    configure via: {inputs or '(see file header)'}")
    lines.append(
        "DECIDE: if one of these MATCHES your task, adapt its inputs/config and RUN it (faster, proven); "
        "if nothing fits, just work normally. Only use a module whose status is 'working'.")
    return "\n".join(lines) + "\n"


def has_pool_for(role: str) -> bool:
    return bool(list_for_role(role))
