"""
HubSpot API router — the operator agent's endpoints (portal 47173986).

Mounted at app start. Everything returns REAL data from the private-app token in workspace/shared/oth/.cred; nothing is
faked. Requests that need a scope not granted return actionable guidance (see integrations/hubspot).

  GET  /hubspot/status         → connection check + granted scope count (the top-bar badge uses this)
  GET  /hubspot/scopes         → the 35 granted scopes + how to add more
  POST /hubspot/run            → DEFAULT run: confirm connection + account overview (contacts/companies/
                                 deals/this-month). Writes a report + notification like other projects.
  POST /hubspot/ask   {query}  → a specific ask, e.g. "contacts this month", "how many companies"
"""
from __future__ import annotations

import time

try:
    from fastapi import APIRouter
    from pydantic import BaseModel
except Exception:  # pragma: no cover
    APIRouter = None  # type: ignore

from integrations import hubspot


def _notify(title: str, body: str, kind: str = "hubspot", pid: str = "hubspot-crm-operator") -> None:
    try:
        import notifications_store as ns  # type: ignore
        ns.add(kind, title, body=body, pid=pid)
    except Exception:
        pass


def _report(pid: str, payload: dict) -> None:
    try:
        import scopes as _sc  # type: ignore
        _sc.sync_up(f"project:{pid}", f"HubSpot run: {payload.get('summary','overview')}")
    except Exception:
        pass


def run_overview(pid: str = "hubspot-crm-operator") -> dict:
    """DETERMINISTIC run used by BOTH the /hubspot/run endpoint AND the project ▶ Run button (scheduler).
    Confirms the connection, fetches REAL counts, fires a notification + feed report, returns the payload."""
    import time as _t
    ov = hubspot.account_overview()
    if ov.get("connected"):
        c = ov.get("counts", {})
        summary = (f"connected (portal {ov['connection'].get('portal_id')}) · "
                   f"contacts {c.get('contacts')} · companies {c.get('companies')} · "
                   f"deals {c.get('deals')} · this-month {c.get('contacts_this_month')}")
        _notify("HubSpot connected ✓", summary, pid=pid)
    else:
        summary = f"NOT connected: {ov.get('error')}"
        _notify("HubSpot connection failed", summary, pid=pid)
    ov["summary"] = summary
    ov["ran_at"] = int(_t.time())
    _report(pid, ov)
    return ov


# --- natural-language-ish mapping to an in-scope capability -------------------------------
def _answer_query(q: str) -> dict:
    ql = (q or "").lower()
    if "this month" in ql or "current month" in ql or ("month" in ql and "contact" in ql):
        r = hubspot.contacts_this_month()
        return {"query": q, "capability": "contacts_this_month",
                "answer": r.get("total") if r.get("ok") else None,
                "ok": r.get("ok", False), "guidance": None if r.get("ok") else r.get("error")}
    if "compan" in ql:
        allowed, missing = hubspot.capability_allowed("companies_count")
        if not allowed:
            return {"query": q, "ok": False, "guidance": hubspot.scope_guidance(missing)}
        r = hubspot.object_count("companies")
        return {"query": q, "capability": "companies_count", "answer": r.get("total"), "ok": r.get("ok", False)}
    if "deal" in ql:
        allowed, missing = hubspot.capability_allowed("deals_count")
        if not allowed:
            return {"query": q, "ok": False, "guidance": hubspot.scope_guidance(missing)}
        r = hubspot.object_count("deals")
        return {"query": q, "capability": "deals_count", "answer": r.get("total"), "ok": r.get("ok", False)}
    if "contact" in ql or "lead" in ql or "profile" in ql:
        allowed, missing = hubspot.capability_allowed("contacts_count")
        if not allowed:
            return {"query": q, "ok": False, "guidance": hubspot.scope_guidance(missing)}
        r = hubspot.object_count("contacts")
        return {"query": q, "capability": "contacts_count", "answer": r.get("total"), "ok": r.get("ok", False)}
    # unknown / likely out of scope → be smart, don't fake
    return {"query": q, "ok": False,
            "guidance": ("I can answer, within the granted scopes: total contacts, total companies, "
                         "total deals, and contacts created this month. For anything else (tickets, "
                         "marketing emails, forms, workflows, …) the private app needs the matching scope "
                         "added in the HubSpot portal, then the token regenerated in workspace/shared/oth/.cred.")}


def build_router():
    if APIRouter is None:
        raise RuntimeError("fastapi not available")
    r = APIRouter(prefix="/hubspot", tags=["hubspot"])

    class AskIn(BaseModel):
        query: str = ""
        pid: str = "hubspot-crm-operator"

    @r.get("/status")
    def status():
        if not hubspot.configured():
            return {"connected": False, "error": "HUBSPOT_SECRET_KEY missing in workspace/shared/oth/.cred"}
        conn = hubspot.connection_check()
        return {"connected": conn.get("ok", False), "connection": conn,
                "granted_scopes": len(hubspot.granted_scopes())}

    @r.get("/overview")
    def overview():
        """GET version of the account overview (connection + real counts) — mirrored to the anchor so
        web/mobile show the HubSpot badge + counts without a direct backend call."""
        return hubspot.account_overview()

    @r.get("/scopes")
    def scopes():
        doc = hubspot.scopes_doc()
        return {"portal_id": doc.get("portal_id"), "granted": doc.get("granted_scopes", []),
                "how_to_add": ("HubSpot portal → Settings → Integrations → Private Apps → open this app "
                               "→ Scopes → add/remove → Save → regenerate token → update HUBSPOT_SECRET_KEY "
                               "in workspace/shared/oth/.cred.")}

    @r.post("/run")
    def run(body: AskIn | None = None):
        """DEFAULT run: confirm connection + full account overview. Real data only."""
        return run_overview((body.pid if body else None) or "hubspot-crm-operator")

    @r.post("/ask")
    def ask(body: AskIn):
        return _answer_query(body.query)

    return r
