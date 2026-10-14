"""SOC API — status + runtime settings for the dashboard/notifications (web/mobile/desktop)."""
from __future__ import annotations
import io, pathlib
from fastapi import APIRouter
from fastapi.responses import StreamingResponse, JSONResponse
import store  # type: ignore

PID = "redberry-continuous-soc"


def build_router() -> APIRouter:
    r = APIRouter()

    @r.get("/soc/status")
    def status(pid: str = PID):
        import soc_run, scheduler
        last = store.read_json(f"projects/{pid}/data/jsons/soc_last_run.json", {})
        tasks = [t for t in scheduler.list_tasks(pid)]
        nextrun = tasks[0].get("nextRun") if tasks else None
        s = soc_run.settings()
        return {"pid": pid, "enabled": s.get("SOC_ENABLED"), "monitor_only": s.get("SOC_MONITOR_ONLY"),
                "auto_remediation": s.get("SOC_AUTO_REMEDIATION_ENABLED"),
                "daily_run": f"{s.get('SOC_DAILY_RUN_TIME')} {s.get('SOC_TIMEZONE')}",
                "last_run": last, "next_run": nextrun}

    @r.get("/soc/settings")
    def get_settings():
        import soc_run
        return {"settings": soc_run.settings()}

    @r.post("/soc/settings")
    def set_settings(body: dict):
        import soc_run
        return {"settings": soc_run.save_settings(body or {})}

    @r.post("/soc/run")
    def run_now(body: dict | None = None):
        import scheduler
        b = body or {}
        return scheduler.run_now(b.get("pid", PID), prompt="", cid=b.get("cid", ""))

    @r.get("/soc/report")
    def report(pid: str = PID, fmt: str = "pdf"):
        """Download the latest styled SOC health report in pdf | docx | md | pptx (Reporting Agent output)."""
        import soc_run
        rdir = soc_run._socdir(pid) / "reports"
        ext = fmt if fmt in ("pdf", "docx", "md", "pptx") else "pdf"
        files = sorted(rdir.glob(f"*.{ext}")) if rdir.exists() else []
        if not files:
            return JSONResponse({"error": f"no {ext} report yet — run the SOC first"}, status_code=404)
        latest = files[-1]
        mimes = {"pdf": "application/pdf", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                 "md": "text/markdown", "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation"}
        return StreamingResponse(io.BytesIO(latest.read_bytes()), media_type=mimes[ext],
                                 headers={"Content-Disposition": f'attachment; filename="{latest.name}"'})

    @r.get("/soc/inventory")
    def inventory(pid: str = PID):
        """Living asset & attack-surface inventory (multi-cloud/stack) + reverse-search targeting + scope recs."""
        import soc_inventory
        inv = soc_inventory.scan(pid)
        return {"inventory": inv, "scope_recommendations": soc_inventory.scope_recommendations(inv)}

    @r.get("/soc/recovery")
    def recovery(pid: str = PID, problem_date: str | None = None):
        """Resilience posture + smart, date-aware recovery plan (never restores — plan only)."""
        import soc_recovery
        return {"posture": soc_recovery.posture(pid),
                "plan": soc_recovery.smart_recovery_plan(pid, problem_date)}

    @r.post("/soc/backup")
    def backup(body: dict):
        """APPROVAL-GATED encrypted backup capture (scope: config | db). Requires approved=true."""
        import soc_recovery
        b = body or {}
        return soc_recovery.run_backup(b.get("pid", PID), b.get("scope", "config"), approved=bool(b.get("approved")))

    @r.post("/soc/escrow")
    def escrow(body: dict):
        """APPROVAL-GATED: escrow an encrypted copy of the backup key to a VM folder (DR). Requires approved=true."""
        import soc_recovery
        b = body or {}
        return soc_recovery.escrow_key_to_vm(b.get("pid", PID), approved=bool(b.get("approved")))

    @r.get("/soc/quota")
    def quota(pid: str = PID):
        """Generic third-party service quota/abuse-cost monitor (any provider)."""
        import soc_quota
        return soc_quota.check(pid, abuse_active=False)

    @r.get("/soc/behavior")
    def behavior(pid: str = PID):
        """Behavioral (UEBA) visitor profiles + behaviorally-bad IPs + approval-gated UFW recommendation."""
        import soc_behavior
        return soc_behavior.analyze(pid, test=False)

    @r.post("/soc/finding")
    def finding(body: dict):
        """Owner action: mark a finding resolved | pending | accepted | open (memorizing tracker)."""
        import soc_run
        b = body or {}
        return soc_run.set_finding_status(b.get("pid", PID), b.get("id", ""), b.get("status", "open"), b.get("note", ""))

    # ---- VM SECURITY SENTINEL (the 'vertical' daily monitor) --------------------------------------
    @r.get("/sentinel/status")
    def sentinel_status():
        """Lightweight RED/GREEN VM health from the VM's own sensor facts. Read-only; raises nothing."""
        import security_sentinel
        return security_sentinel.vm_health()

    @r.post("/sentinel/run")
    def sentinel_run(body: dict | None = None):
        """Full run (the ▶ Run button / daily task): verdict → red/green notification → individual
        SECURITY-ALARM approvals on RED → status message in the project. Applies nothing."""
        import security_sentinel
        b = body or {}
        return security_sentinel.run_sentinel(b.get("pid", "vm-sentinel"), create_alarms=b.get("create_alarms", True))

    # ---- SAFE 'approve all' — approves NON-security items only; security alarms stay individual ----
    @r.post("/approvals/approve-all")
    def approvals_approve_all(pid: str = ""):
        import approvals
        return approvals.approve_all_safe(pid or None)

    return r
