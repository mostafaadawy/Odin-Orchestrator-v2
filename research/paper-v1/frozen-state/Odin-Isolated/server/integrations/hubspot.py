"""
HubSpot client — operator-agent analytics over the CRM (portal 47173986).

Auth: a HubSpot PRIVATE APP token from workspace/shared/oth/.cred (HUBSPOT_SECRET_KEY, format `pat-...`), sent as
`Authorization: Bearer <token>`. Uses urllib (no extra deps), same shape as the Klaviyo/Veeqo clients.

Scope-aware: the granted scopes live in data/hubspot_scopes.json (the source of truth). Analytics that
fall inside those scopes are answered with REAL counts. If a request needs a scope that is NOT granted,
the client returns a clear, actionable message telling the owner how to add it in the portal + regenerate
the token — it never fabricates a number.
"""
from __future__ import annotations

import json
import time
import datetime
import pathlib
import urllib.request
import urllib.error
import urllib.parse

from . import cred

BASE = "https://api.hubapi.com"
_SCOPES_FILE = (pathlib.Path(__file__).resolve().parent.parent.parent
                / "workspace" / "shared" / "utils" / "hubspot_scopes.json")


def _token() -> str:
    return cred.load().get("HUBSPOT_SECRET_KEY", "").strip()


def configured() -> bool:
    return bool(_token())


def scopes_doc() -> dict:
    try:
        return json.loads(_SCOPES_FILE.read_text())
    except Exception:
        return {"granted_scopes": [], "capability_requirements": {}}


def granted_scopes() -> list[str]:
    return scopes_doc().get("granted_scopes", [])


def scope_guidance(missing: list[str]) -> str:
    return (
        "This request needs HubSpot scope(s) not currently granted: "
        + ", ".join(missing)
        + ". To enable it: HubSpot portal → Settings → Integrations → Private Apps → open this app → "
          "Scopes → add the scope(s) above → Save → regenerate the token → update HUBSPOT_SECRET_KEY in "
          "workspace/shared/oth/.cred. I won't guess a number that isn't backed by a permitted read."
    )


def capability_allowed(capability: str) -> tuple[bool, list[str]]:
    """Return (allowed, missing_scopes) for a named analytics capability."""
    doc = scopes_doc()
    needed = doc.get("capability_requirements", {}).get(capability, [])
    granted = set(doc.get("granted_scopes", []))
    missing = [s for s in needed if s not in granted]
    return (len(missing) == 0, missing)


# ---------------------------------------------------------------------------
def call(method: str, path: str, params: dict | None = None, body: dict | None = None,
         timeout: int = 30) -> dict:
    """Hit a HubSpot endpoint. Returns {ok,status,data|error}. GET + POST(search/reporting) used here."""
    tok = _token()
    if not tok:
        return {"ok": False, "status": 0, "error": "HUBSPOT_SECRET_KEY missing in workspace/shared/oth/.cred"}
    p = path if path.startswith("http") else f"{BASE}/{path.lstrip('/')}"
    if params:
        p += ("&" if "?" in p else "?") + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(p, data=data, method=method.upper())
    req.add_header("Authorization", f"Bearer {tok}")
    req.add_header("accept", "application/json")
    if data is not None:
        req.add_header("content-type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode()
            return {"ok": True, "status": r.status, "data": json.loads(raw) if raw else {}}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "error": e.read().decode()[:1000]}
    except Exception as e:
        return {"ok": False, "status": 0, "error": str(e)}


# ---------------------------------------------------------------------------
def account() -> dict:
    """Portal / account details — doubles as the connection check."""
    return call("GET", "account-info/v3/details")


def object_count(obj: str, filters: list | None = None) -> dict:
    """Total count of a CRM object via the search endpoint's `total` (no page walk needed)."""
    body: dict = {"limit": 1}
    if filters:
        body["filterGroups"] = [{"filters": filters}]
    else:
        body["filterGroups"] = []
    r = call("POST", f"crm/v3/objects/{obj}/search", body=body)
    if not r.get("ok"):
        return r
    return {"ok": True, "status": r["status"], "total": (r.get("data") or {}).get("total")}


def _month_start_ms(dt: datetime.datetime | None = None) -> int:
    now = dt or datetime.datetime.now(datetime.timezone.utc)
    return int(datetime.datetime(now.year, now.month, 1, tzinfo=datetime.timezone.utc).timestamp() * 1000)


def contacts_this_month() -> dict:
    ok, missing = capability_allowed("contacts_this_month")
    if not ok:
        return {"ok": False, "status": 403, "error": scope_guidance(missing)}
    return object_count("contacts", filters=[
        {"propertyName": "createdate", "operator": "GTE", "value": str(_month_start_ms())}
    ])


def connection_check() -> dict:
    """Confirm the token authenticates. Returns {ok, portal_id, account_type, ...}."""
    r = account()
    if not r.get("ok"):
        return {"ok": False, "error": r.get("error"), "status": r.get("status")}
    d = r.get("data") or {}
    return {"ok": True, "portal_id": d.get("portalId"), "account_type": d.get("accountType"),
            "time_zone": d.get("timeZone"), "currency": d.get("companyCurrency"),
            "ui_domain": d.get("uiDomain")}


def account_overview() -> dict:
    """The default/first-run payload: connection + key CRM counts, all REAL, scope-checked."""
    conn = connection_check()
    out: dict = {"connected": conn.get("ok", False), "connection": conn,
                 "granted_scope_count": len(granted_scopes()), "fetched_at": int(time.time())}
    if not conn.get("ok"):
        out["error"] = conn.get("error")
        return out
    counts: dict = {}
    for cap, obj in (("contacts_count", "contacts"), ("companies_count", "companies"),
                     ("deals_count", "deals")):
        allowed, missing = capability_allowed(cap)
        if not allowed:
            counts[obj] = {"blocked": True, "guidance": scope_guidance(missing)}
            continue
        r = object_count(obj)
        counts[obj] = r.get("total") if r.get("ok") else {"error": r.get("error")}
    tm = contacts_this_month()
    counts["contacts_this_month"] = tm.get("total") if tm.get("ok") else {"blocked": True, "guidance": tm.get("error")}
    out["counts"] = counts
    return out
