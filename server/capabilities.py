"""
Capabilities & integrations registry — what the system ALREADY has connected, and what it can
help connect. The CTO/brain uses this to reason about a project's dependencies: tell the owner
what's available (Claude engine, Azure VM, local models) vs what still needs connecting (App
Store, Google Play, Cloudinary, Stripe, GitHub…), and how.
"""
from __future__ import annotations

import os
import json
import shutil
import urllib.request
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Things we know HOW to connect (offered when a project needs them).
CATALOG = [
    {"name": "Apple App Store", "kind": "distribution", "needs": "Apple Developer account + signing certs/provisioning",
     "how": "Enrol in Apple Developer Program, create an App ID + signing certificate, then connect Xcode/Fastlane."},
    {"name": "Google Play", "kind": "distribution", "needs": "Google Play Console account + signing key",
     "how": "Create a Play Console account, generate an upload key, connect via Gradle/Fastlane."},
    {"name": "Cloudinary", "kind": "media", "needs": "Cloudinary account + API key/secret",
     "how": "Create a Cloudinary account, copy the cloud name/API key/secret into the project's env."},
    {"name": "Stripe", "kind": "payments", "needs": "Stripe account + API keys",
     "how": "Create a Stripe account, add the secret/publishable keys to env, set up a webhook."},
    {"name": "GitHub", "kind": "vcs", "needs": "GitHub account + repo + token",
     "how": "Create a repo, add a deploy/personal token, connect git remote."},
    {"name": "Vercel / Netlify", "kind": "hosting", "needs": "account + project link",
     "how": "Connect the repo to Vercel/Netlify for static/SSR hosting."},
]


def _ollama_models() -> list:
    try:
        url = os.environ.get("ODIN_OLLAMA_URL", "http://localhost:11434").rstrip("/")
        with urllib.request.urlopen(f"{url}/api/tags", timeout=2) as r:
            data = json.loads(r.read().decode("utf-8"))
        return [m.get("name") for m in data.get("models", []) if m.get("name")]
    except Exception:
        return []


# ---- user-added external connectors (API-key integrations: GA, Klaviyo, Stripe, MCPs…) ----
import store  # type: ignore


def _db_connector_ids():
    """odin_core is the single source of truth for WHICH connectors exist. None if DB unreachable."""
    try:
        import psycopg2  # type: ignore
        c = psycopg2.connect(dbname="odin_core"); cu = c.cursor()
        cu.execute("SELECT id FROM connectors"); ids = [r[0] for r in cu.fetchall()]; c.close()
        return ids
    except Exception:
        return None


def _connector_cfg(cid: str) -> dict:
    """A connector's config lives in its OWN folder (workspace/connectors/<id>/index.json), which the DB
    points to — never a global registry file."""
    import workspace_mw as mw  # type: ignore
    p = mw.resolve_path("connector", cid, "", "index.json")
    try:
        return json.loads(p.read_text()) if p.exists() else {"id": cid}
    except Exception:
        return {"id": cid}


def list_connectors() -> list:
    """Single source of truth = odin_core. List exactly the connectors the database has, each loaded from
    its own on-disk file. No global connectors.json — a ghost can never appear here."""
    ids = _db_connector_ids()
    if ids is None:
        import workspace_mw as mw  # type: ignore
        base = mw.WS / "connectors"
        try:
            ids = [d.name for d in base.iterdir() if d.is_dir()]
        except Exception:
            ids = []
    out = []
    for cid in ids:
        c = _connector_cfg(cid); c.setdefault("id", cid); out.append(c)
    return out


def add_connector(name: str, ctype: str = "", api_key: str = "") -> dict:
    import uuid
    import workspace_mw as mw  # type: ignore
    cid = uuid.uuid4().hex[:8]
    c = {"id": cid, "name": name, "type": ctype,
         "hasKey": bool(api_key), "status": "connected" if api_key else "needs key",
         "created": store.now()}
    # THE single door: write the connector's own index.json → creates its folder + odin_core row + indexes it
    mw.put_file("connector", cid, "", "index.json", c)
    if api_key:  # store the secret OUT of the registry, in a gitignored file
        keys = store.read_json("connector_keys.json", {})
        keys[cid] = api_key
        store.write_json("connector_keys.json", keys)
    return c


def remove_connector(cid: str) -> bool:
    import workspace_mw as mw  # type: ignore
    try:
        mw.delete_owner("connector", cid)   # flush the DB row + folder (single door)
    except Exception:
        pass
    try:
        keys = store.read_json("connector_keys.json", {}); keys.pop(cid, None)
        store.write_json("connector_keys.json", keys)
    except Exception:
        pass
    return True


def snapshot() -> dict:
    have, available = [], []

    # Claude Code engine
    if shutil.which("claude"):
        have.append({"name": "Claude Code (engine)", "kind": "ai", "detail": "terminal-capable brain"})

    # Local models (Ollama)
    models = _ollama_models()
    if models:
        have.append({"name": "Local models (Ollama)", "kind": "ai", "detail": ", ".join(models[:4])})

    # Azure
    if shutil.which("az"):
        have.append({"name": "Azure CLI", "kind": "cloud", "detail": "control plane"})
    try:
        prof = json.loads((ROOT / "infra" / "azure" / "connection.profile.json").read_text())
        az = prof.get("azure", {})
        if az.get("vmName"):
            have.append({"name": "Azure VM", "kind": "cloud",
                         "detail": f"{az.get('vmName')} / {az.get('resourceGroup','')}"})
    except Exception:
        pass

    # user-added connectors
    user = list_connectors()
    for c in user:
        have.append({"name": c["name"], "kind": c.get("type", "integration"),
                     "detail": c.get("status", ""), "id": c["id"], "user": True})

    have_names = {h["name"] for h in have}
    for c in CATALOG:
        if c["name"] not in have_names:
            available.append(c)

    return {"have": have, "available": available, "connectors": user}


def summary_text() -> str:
    s = snapshot()
    have = "; ".join(f"{h['name']} ({h.get('detail','')})" for h in s["have"]) or "none detected"
    avail = "; ".join(c["name"] for c in s["available"])
    return (f"Already connected: {have}.\n"
            f"NOT yet connected but can be set up on request: {avail}.")
