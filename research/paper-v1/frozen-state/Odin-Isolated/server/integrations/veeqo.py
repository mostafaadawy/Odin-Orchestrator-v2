"""
Veeqo (VQ) client — READ-ONLY for Fulfillment-Provider projects (Revealer sandbox).

The task mandates read-only access to Veeqo. The generic `call(method, path, ...)` is hard-gated
two ways — modeled on klaviyo.py:
  1. METHOD gate: any non-GET method (POST/PUT/PATCH/DELETE) raises PermissionError, and a
     request body is rejected.
  2. ENDPOINT whitelist: only the read-only endpoints the app needs are allowed —
     /orders, /shipments, /carriers, /current_user (and their sub-paths, e.g. /orders/{id}).
     Anything else raises PermissionError before a request is ever built.
Auth: VEEQO_API_KEY from workspace/shared/oth/.cred, header `x-api-key` (never hardcoded or logged). Base
https://api.veeqo.com. Uses urllib (no extra deps).
"""
from __future__ import annotations

import json
import urllib.request
import urllib.error
import urllib.parse

from . import cred

BASE = "https://api.veeqo.com"

# Read-only endpoints this integration is permitted to reach (prefix match on the first path
# segment). Any other path is rejected — same read-only posture QA required for klaviyo.py.
ALLOWED_PREFIXES = ("orders", "shipments", "carriers", "current_user")


def _key() -> str:
    return cred.get("VEEQO_API_KEY", "")


def configured() -> bool:
    return bool(_key())


def _allowed_path(path: str) -> bool:
    """True only if path's first segment is in ALLOWED_PREFIXES (e.g. 'orders/123' -> 'orders')."""
    head = path.lstrip("/").split("?", 1)[0].split("/", 1)[0].lower()
    return head in ALLOWED_PREFIXES


def call(method: str, path: str, params: dict | None = None, body: dict | None = None) -> dict:
    """Hit a Veeqo endpoint, GET only, whitelisted paths only. Returns {ok,status,data}.

    READ-ONLY enforcement: the task mandates read-only access to Veeqo, so any non-GET method
    (POST/PUT/PATCH/DELETE) or request body is rejected, and only the whitelisted read-only
    endpoints (orders/shipments/carriers/current_user) are reachable — all before a request is built.
    """
    if method.upper() != "GET":
        raise PermissionError(
            f"Veeqo integration is read-only: {method.upper()} not allowed (GET only)"
        )
    if body is not None:
        raise PermissionError("Veeqo integration is read-only: request body not allowed")
    # absolute URLs are only allowed if they point at our BASE and a whitelisted path
    if path.startswith("http"):
        if not path.startswith(BASE):
            raise PermissionError(f"Veeqo integration: off-base URL not allowed: {path[:80]}")
        rel = path[len(BASE):]
    else:
        rel = path
    if not _allowed_path(rel):
        raise PermissionError(
            f"Veeqo integration is read-only: endpoint '{rel.lstrip('/').split('?',1)[0]}' "
            f"not in read-only whitelist {ALLOWED_PREFIXES}"
        )
    key = _key()
    if not key:
        return {"ok": False, "status": 0, "error": "VEEQO_API_KEY missing in workspace/shared/oth/.cred"}
    p = path if path.startswith("http") else f"{BASE}/{path.lstrip('/')}"
    if params:
        p += ("&" if "?" in p else "?") + urllib.parse.urlencode(params)
    req = urllib.request.Request(p, data=None, method="GET")
    req.add_header("x-api-key", key)
    req.add_header("accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
            return {"ok": True, "status": r.status, "data": json.loads(raw) if raw else {}}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "error": e.read().decode()[:1000]}
    except Exception as e:
        return {"ok": False, "status": 0, "error": str(e)}


# --- read-only convenience wrappers (all GET, all whitelisted) ---
def orders(params=None):              return call("GET", "orders", params)
def order(order_id):                  return call("GET", f"orders/{order_id}")
def shipments(params=None):           return call("GET", "shipments", params)
def shipment_status(order_id):        return call("GET", f"orders/{order_id}")   # status lives on the order
def carriers():                       return call("GET", "carriers")
def current_user():                   return call("GET", "current_user")
def create_shipment(*_a, **_k):  # DISABLED: read-only integration, no write operations
    raise PermissionError("Veeqo integration is read-only: create_shipment is disabled")


def orders_summary(since_iso: str | None = None) -> dict:
    """READ-ONLY: count orders (optionally since a date) — used for 'how many orders this week'."""
    params = {"page_size": 100}
    if since_iso:
        params["created_at_min"] = since_iso
    r = call("GET", "orders", params)
    if not r.get("ok"):
        return r
    data = r.get("data")
    if isinstance(data, list):
        count = len(data)
    elif isinstance(data, dict):
        count = data.get("total_records") or len(data.get("orders", []))
    else:
        count = 0
    return {"ok": True, "count": count, "since": since_iso}
