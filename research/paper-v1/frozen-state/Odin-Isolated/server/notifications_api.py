"""Notifications API — the live sync feed for recurring/periodical work (read / mark-read / redirect)."""
from __future__ import annotations
from fastapi import APIRouter


def build_router() -> APIRouter:
    r = APIRouter()

    @r.get("/notifications")
    def list_notifs(unread: bool = False, limit: int = 100):
        import notifications_store as nt
        return {"items": nt.list(unread_only=unread, limit=limit), "unread": nt.unread_count()}

    @r.get("/notifications/count")
    def count():
        import notifications_store as nt
        return {"unread": nt.unread_count()}

    @r.post("/notifications/read")
    def read(body: dict | None = None):
        import notifications_store as nt
        b = body or {}
        return nt.mark_read(nid=b.get("id", ""), all=bool(b.get("all")))

    @r.post("/notifications/clear")
    def clear(body: dict | None = None):
        import notifications_store as nt
        b = body or {}
        return nt.clear(all=bool(b.get("all")))

    @r.post("/notifications/test")
    def test():
        """Emit a sample notification (for wiring up the UI)."""
        import notifications_store as nt
        return nt.add("info", "🔔 Test notification", body="Notifications are working.", severity="info")

    return r
