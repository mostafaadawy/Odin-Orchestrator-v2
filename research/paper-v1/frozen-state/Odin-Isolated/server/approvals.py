"""Approval gate — the owner must explicitly approve before ANY agent changes files or runs a
state-changing / VM command.

An agent runs READ-ONLY and PROPOSES changes. The Project CTO collects them into ONE approval
request stored here. The frontend shows a notification bubble (+ OS alert); the owner approves or
rejects. Only approved actions are then executed by a write-enabled run.

Status flow: pending → approved | rejected  (and an applied flag once executed).
"""
from __future__ import annotations

import re
import uuid
import store

_FILE = "approvals.json"

# Anything destructive or production-touching → CRITICAL (red).
_DESTRUCTIVE = re.compile(
    r"\b(rm|sudo|reboot|shutdown|halt|poweroff|drop|truncate|mkfs|dd)\b|"
    r"migrate\s+reset|prisma\s+migrate\s+reset|--delete\b|--force\b|--delete-excluded", re.I)
# Commands that change the environment but not your source → CAUTION (yellow).
_WRITECMD = re.compile(
    r"\b(npm\s+(i|install|ci|run\s+build|rebuild)|yarn|pnpm|git\s+(push|commit|reset|checkout|clean)|"
    r"systemctl|service|pm2|docker|prisma\s+(generate|migrate)|next\s+build|nest\s+build)\b", re.I)


def severity_of(files, commands, kind="change") -> str:
    """critical (red) | caution (yellow) | routine (neutral).
    Modifying files / accessing a folder / any VM or destructive command = RED."""
    if kind == "qa-recommendation":
        return "routine"
    if files:                                  # writing/creating/deleting files = red
        return "critical"
    for c in (commands or []):
        cmd = (c.get("cmd", "") if isinstance(c, dict) else str(c))
        where = (c.get("where", "local") if isinstance(c, dict) else "local")
        if where == "vm" or _DESTRUCTIVE.search(cmd) or any(k in cmd for k in ("rsync", "scp", "ssh ", "ssh\t")):
            return "critical"
    if commands:
        return "caution" if any(_WRITECMD.search(c.get("cmd", "") if isinstance(c, dict) else str(c)) for c in commands) else "caution"
    return "routine"


def _all() -> list:
    return store.read_json(_FILE, {"items": []}).get("items", [])


def _save(items: list) -> None:
    store.write_json(_FILE, {"items": items})


def create(pid: str, member: str, title: str, summary: str = "",
           files: list | None = None, commands: list | None = None,
           cwd: str = "", kind: str = "change", inline: bool = False,
           security: bool = False, recommended: str = "", fix_plan: str = "") -> dict:
    """Create a pending approval request.
    files: [{"path","action"("edit"|"create"|"delete"),"why","preview"?}]
    commands: [{"cmd","where"("local"|"vm"),"why"}]
    inline=True  → an active run is already waiting to apply it (don't background-execute on approve).
    inline=False → created from a chat; the approve endpoint will execute it in the background.

    security=True  → a SECURITY ALARM approval: a SEPARATE, deliberate channel. It is flagged
      (security=True, alarm=True, severity="security", kind="security") so the UI renders it as a big
      red alarm and — critically — it is EXCLUDED from any 'approve all' (see list_pending(bulk=True) and
      approve_all_safe): each must be approved INDIVIDUALLY so a security fix can never be swept in by
      accident. `recommended` = the recommended action; `fix_plan` = how it will be done (e.g. patch in
      LOCAL first, then deploy — never hot-patched on the VM)."""
    item = {
        "id": uuid.uuid4().hex[:12],
        "pid": pid,
        "member": member,
        "title": (("🔴 SECURITY: " if security else "") + (title or "Proposed changes"))[:180],
        "summary": summary or "",
        "files": files or [],
        "commands": commands or [],
        "cwd": cwd or "",
        "kind": "security" if security else kind,   # "change" | "vm" | "qa-recommendation" | "security"
        "severity": "security" if security else severity_of(files, commands, kind),  # critical|caution|routine|security
        "security": bool(security),   # a distinct, red-alarm channel — NEVER part of 'approve all'
        "alarm": bool(security),      # UI flag: render big/red/blinking, pop to front when owner online
        "recommended": recommended or "",
        "fix_plan": fix_plan or "",
        "inline": bool(inline),
        "status": "pending",          # pending | approved | rejected
        "applied": False,
        "created": store.now(),
        "decided": None,
        "note": "",                   # owner's optional note on decision
    }
    items = _all()
    items.append(item)
    _save(items)
    return item


def create_security(pid: str, member: str, title: str, summary: str = "",
                    recommended: str = "", fix_plan: str = "", commands: list | None = None) -> dict:
    """Convenience: raise a SECURITY ALARM approval (separate red channel, never in 'approve all')."""
    return create(pid, member, title, summary=summary, commands=commands, kind="security",
                  security=True, recommended=recommended, fix_plan=fix_plan)


def get(aid: str):
    return next((a for a in _all() if a["id"] == aid), None)


def list_pending(pid: str | None = None, bulk: bool = False) -> list:
    """Pending approvals. bulk=True EXCLUDES security-alarm approvals — those are never part of an
    'approve all' and must be decided individually."""
    out = [a for a in _all() if a["status"] == "pending"]
    if pid:
        out = [a for a in out if a["pid"] == pid]
    if bulk:
        out = [a for a in out if not a.get("security")]
    return sorted(out, key=lambda a: a["created"])


def approve_all_safe(pid: str | None = None) -> dict:
    """'Approve all' — approves every pending NON-security approval. Security-alarm approvals are LEFT
    pending on purpose (they require an individual, deliberate decision). Returns what was approved and
    what was deliberately skipped so the UI can say 'N approved · M security items need your attention'."""
    approved = []
    for a in list_pending(pid, bulk=True):
        decide(a["id"], True, note="approved via approve-all (non-security)")
        approved.append(a["id"])
    skipped = [a["id"] for a in list_pending(pid) if a.get("security")]
    return {"approved": approved, "approved_count": len(approved),
            "security_skipped": skipped, "security_skipped_count": len(skipped)}


def list_for(pid: str | None = None, limit: int = 50) -> list:
    out = _all()
    if pid:
        out = [a for a in out if a["pid"] == pid]
    return sorted(out, key=lambda a: a["created"], reverse=True)[:limit]


def decide(aid: str, approved: bool, note: str = "") -> dict | None:
    items = _all()
    for a in items:
        if a["id"] == aid:
            a["status"] = "approved" if approved else "rejected"
            a["decided"] = store.now()
            a["note"] = note or ""
            _save(items)
            return a
    return None


def mark_applied(aid: str, result: str = "") -> None:
    items = _all()
    for a in items:
        if a["id"] == aid:
            a["applied"] = True
            a["result"] = (result or "")[:4000]
            _save(items)
            return


def pending_count(pid: str | None = None) -> int:
    return len(list_pending(pid))
