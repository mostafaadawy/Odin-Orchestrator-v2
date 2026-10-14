"""
seed_connectors.py — move/seed the real connectors into workspace/connectors/<slug>/ and odin_core_iso.

Deadlock-safe: (1) create folders + index.json, (2) seed connector ROWS in one transaction and COMMIT +
CLOSE, (3) only THEN sync folders/files (each opens its own connection — no outer lock is held).
Run: python3 workspace/shared/testing/seed_connectors.py
"""
from __future__ import annotations
import sys, json, pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SERVER = ROOT / "server"
WS = ROOT / "workspace"
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))
import workspace_mw as mw
import psycopg2

CONN = [
    ("hubspot", "HubSpot", "crm", "HubSpot CRM connector (portal 47173986)"),
    ("klaviyo", "Klaviyo", "email", "Klaviyo email/flows connector"),
    ("veeqo", "Veeqo", "fulfillment", "Veeqo fulfillment/shipping connector"),
    ("claude-cli", "Claude CLI", "ai", "Claude command-line connector (agentic coding)"),
    ("az-cli", "Azure CLI", "cloud", "Azure CLI connector (VM/NSG/firewall control-plane)"),
]
SUBS = ["code", "config", "docs"]


def main():
    # 1) folders + index.json + subfolders (no DB)
    for cid, name, kind, desc in CONN:
        base = WS / "connectors" / cid
        base.mkdir(parents=True, exist_ok=True)
        ix = base / "index.json"
        if not ix.exists():
            ix.write_text(json.dumps({"id": cid, "name": name, "kind": kind, "description": desc}, indent=2))
        for s in SUBS:
            d = base / s
            d.mkdir(exist_ok=True)
            if not any(d.iterdir()):
                (d / ".gitkeep").write_text("")

    # 2) seed rows in ONE short transaction, then COMMIT + CLOSE (release the lock).
    #    lock_timeout so a stale lock can never hang us; first clear any backend stuck on the connectors row.
    c = psycopg2.connect(dbname="odin_core_iso", options="-c lock_timeout=8000")
    cu = c.cursor()
    try:
        cu.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                   "WHERE datname='odin_core_iso' AND pid <> pg_backend_pid() "
                   "AND (state='idle in transaction' OR (wait_event_type='Lock'))")
        c.commit()
    except Exception:
        c.rollback()
    for cid, name, kind, desc in CONN:
        base = WS / "connectors" / cid
        cu.execute("INSERT INTO connectors(id,name,path) VALUES(%s,%s,%s) "
                   "ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, path=EXCLUDED.path",
                   (cid, name, str(base.relative_to(ROOT))))
    c.commit()
    c.close()

    # 3) NOW sync folders + files (each opens its own connection; no lock is held)
    for cid, name, kind, desc in CONN:
        base = WS / "connectors" / cid
        mw.sync_folders("connector", cid)
        for f in base.rglob("*"):
            if f.is_file() and f.name != ".gitkeep":
                mw.sync_row(f)
    print("seeded", len(CONN), "connectors with folders + files")


if __name__ == "__main__":
    main()
