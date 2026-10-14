"""
Per-scope model control (Phase 5).

The owner can choose which AI model powers each level:
    main                       -> the company brain
    project:<pid>              -> a whole project
    member:<pid>:<agent>       -> a single team member

Resolution is most-specific-wins: member -> project -> main -> built-in default. Lighter/cheaper
models can be assigned to simple members to save credits; powerful paid models only where needed.
"""
from __future__ import annotations

import os
import json
import urllib.request
import store  # type: ignore

# The CORE engine is Claude CLI (it has the terminal tools — az, bash — to actually DO things
# like check the VM). Local Ollama models are an opt-in, per-scope choice to save credits.
DEFAULT_MAIN = os.environ.get("ODIN_MAIN_MODEL", "claude-cli")

# Curated catalog the UI can show; live local models are appended from `ollama`.
CATALOG = [
    {"id": "claude-cli", "label": "Claude Code (engine)", "kind": "claude", "cost": "paid"},
    {"id": "qwen2.5:7b-instruct-q4_K_M", "label": "Qwen2.5 7B (local, fast)", "kind": "ollama", "cost": "free"},
    {"id": "qwen2.5:14b-instruct-q4_K_M", "label": "Qwen2.5 14B (local, stronger)", "kind": "ollama", "cost": "free"},
]


def _cfg() -> dict:
    return store.read_json("models.json", {"main": DEFAULT_MAIN, "scopes": {}})


def _save(cfg: dict) -> None:
    store.write_json("models.json", cfg)


def get_model(scope_id: str) -> str:
    cfg = _cfg()
    if scope_id == "main" or scope_id == "company":
        return cfg.get("main", DEFAULT_MAIN)
    scopes = cfg.get("scopes", {})
    if scope_id in scopes:
        return scopes[scope_id]
    # member -> fall back to its project, then main
    if scope_id.startswith("member:"):
        _, pid, _agent = scope_id.split(":", 2)
        if f"project:{pid}" in scopes:
            return scopes[f"project:{pid}"]
    return cfg.get("main", DEFAULT_MAIN)


def set_model(scope_id: str, model: str) -> dict:
    cfg = _cfg()
    if scope_id in ("main", "company"):
        cfg["main"] = model
    else:
        cfg.setdefault("scopes", {})[scope_id] = model
    _save(cfg)
    return cfg


def available_models() -> list:
    models = list(CATALOG)
    have = {m["id"] for m in models}
    # append any local Ollama models actually installed
    try:
        url = os.environ.get("ODIN_OLLAMA_URL", "http://localhost:11434").rstrip("/")
        with urllib.request.urlopen(f"{url}/api/tags", timeout=3) as r:
            data = json.loads(r.read().decode("utf-8"))
        for m in data.get("models", []):
            mid = m.get("name") or m.get("model")
            if mid and mid not in have:
                models.append({"id": mid, "label": f"{mid} (local)", "kind": "ollama", "cost": "free"})
                have.add(mid)
    except Exception:
        pass
    return models
