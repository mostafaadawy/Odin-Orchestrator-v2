#!/usr/bin/env python3
"""Read-only LIVE check of every connector that needs an API key (one harmless GET each). Prints names + ok/count
only — never a key, never record contents."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "server"))
from integrations import klaviyo, veeqo, hubspot, easypost
def show(name, fn):
    try:
        r = fn()
        ok = isinstance(r, dict) and (r.get("ok", True) is not False) and not r.get("error")
        detail = {k: r[k] for k in ("ok", "total", "count", "status", "portal_ok") if isinstance(r, dict) and k in r}
        print(f"{name:10s} {'LIVE ✓' if ok else 'FAILED ✗'}  {detail if ok else str(r.get('error', r))[:120]}")
    except Exception as e:
        print(f"{name:10s} FAILED ✗  {type(e).__name__}: {str(e)[:120]}")
show("Klaviyo", klaviyo.flows_summary)
show("Veeqo", lambda: veeqo.call("GET", "orders", {"page_size": 1}) if hasattr(veeqo, "call") else {"ok": veeqo.configured()})
show("HubSpot", hubspot.connection_check)
show("EasyPost", lambda: (lambda r: {"ok": "error" not in r} if isinstance(r, dict) else {"ok": bool(r)})(easypost.trackers({"page_size": 1})))
