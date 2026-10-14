"""
Klaviyo client — READ-ONLY for Email-type projects.

The task requires read-only access to Klaviyo. The generic `call(method, path, ...)` is hard-gated
to GET only — any non-GET method (POST/PUT/PATCH/DELETE) raises PermissionError — plus a few
read-only convenience wrappers. Auth + base URL + revision come from workspace/shared/oth/.cred (KLAVIYO_API_KEY,
KLAVIYO_BASE_URL, KLAVIYO_API_REVISION). Uses urllib (no extra deps).
"""
from __future__ import annotations

import json
import urllib.request
import urllib.error
import urllib.parse

from . import cred


def _cfg():
    c = cred.load()
    return (c.get("KLAVIYO_API_KEY", ""),
            c.get("KLAVIYO_BASE_URL", "https://a.klaviyo.com/api").rstrip("/"),
            c.get("KLAVIYO_API_REVISION", "2025-01-15"))


def configured() -> bool:
    return bool(_cfg()[0])


def call(method: str, path: str, params: dict | None = None, body: dict | None = None) -> dict:
    """Hit a Klaviyo endpoint, GET only. path like 'campaigns' or '/api/lists'. Returns {ok,status,data}.

    READ-ONLY enforcement: the task mandates read-only access to Klaviyo, so any non-GET method
    (POST/PUT/PATCH/DELETE) is rejected here before a request is ever built.
    """
    if method.upper() != "GET":
        raise PermissionError(
            f"Klaviyo integration is read-only: {method.upper()} not allowed (GET only)"
        )
    if body is not None:
        raise PermissionError("Klaviyo integration is read-only: request body not allowed")
    key, base, rev = _cfg()
    if not key:
        return {"ok": False, "status": 0, "error": "KLAVIYO_API_KEY missing in workspace/shared/oth/.cred"}
    p = path if path.startswith("http") else f"{base}/{path.lstrip('/')}"
    if params:
        p += ("&" if "?" in p else "?") + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(p, data=data, method=method.upper())
    req.add_header("Authorization", f"Klaviyo-API-Key {key}")
    req.add_header("revision", rev)
    req.add_header("accept", "application/json")
    if data is not None:
        req.add_header("content-type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
            return {"ok": True, "status": r.status, "data": json.loads(raw) if raw else {}}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "error": e.read().decode()[:1000]}
    except Exception as e:
        return {"ok": False, "status": 0, "error": str(e)}


# --- read-only convenience wrappers (all GET) ---
def lists():                       return call("GET", "lists")
def campaigns(params=None):        return call("GET", "campaigns", params or {"filter": "equals(messages.channel,'email')"})
def get_campaign(cid):            return call("GET", f"campaigns/{cid}")
def create_campaign(*_a, **_k):  # DISABLED: read-only integration, no write operations
    raise PermissionError("Klaviyo integration is read-only: create_campaign is disabled")
def profiles(params=None):         return call("GET", "profiles", params)
def metrics():                     return call("GET", "metrics")
def account():                     return call("GET", "accounts")


def metric_aggregates(metric_id: str, measurement: str = "count",
                      interval: str = "day", since: str | None = None) -> dict:
    """REPORTING-ONLY: POST /api/metric-aggregates to query an aggregated time series for a metric.

    This is the one allowed non-GET call: metric-aggregates is a read/reporting endpoint that only
    QUERIES aggregated data (counts/sums over time) — it never creates, sends, or modifies anything.
    It does not go through `call()` (which stays GET-only), and no other non-GET method is enabled,
    so the integration remains write-blocked everywhere else.

    Args:
        metric_id:   Klaviyo metric id to aggregate.
        measurement: aggregation measure, e.g. "count", "sum_value", "unique". Default "count".
        interval:    time bucket, e.g. "day", "week", "month", "hour". Default "day".
        since:       optional ISO-8601 datetime lower bound (adds a greater-or-equal(datetime,...) filter).

    Returns {ok,status,data}.
    """
    key, base, rev = _cfg()
    if not key:
        return {"ok": False, "status": 0, "error": "KLAVIYO_API_KEY missing in workspace/shared/oth/.cred"}
    attrs: dict = {
        "metric_id": metric_id,
        "measurements": [measurement],
        "interval": interval,
    }
    if since:
        attrs["filter"] = [f"greater-or-equal(datetime,{since})"]
    body = {"data": {"type": "metric-aggregate", "attributes": attrs}}
    p = f"{base}/metric-aggregates"
    data = json.dumps(body).encode()
    req = urllib.request.Request(p, data=data, method="POST")
    req.add_header("Authorization", f"Klaviyo-API-Key {key}")
    req.add_header("revision", rev)
    req.add_header("accept", "application/json")
    req.add_header("content-type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
            return {"ok": True, "status": r.status, "data": json.loads(raw) if raw else {}}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "error": e.read().decode()[:1000]}
    except Exception as e:
        return {"ok": False, "status": 0, "error": str(e)}


def flows_summary() -> dict:
    """READ-ONLY: count Klaviyo flows (workflows) by status — live vs draft vs manual."""
    r = call("GET", "flows")
    if not r.get("ok"):
        return r
    data = (r.get("data") or {}).get("data") or []
    by: dict = {}
    for f in data:
        s = ((f.get("attributes") or {}).get("status") or "unknown").lower()
        by[s] = by.get(s, 0) + 1
    return {"ok": True, "total": len(data), "by_status": by}
