#!/usr/bin/env python3
"""
security_sentinel.py — the VM SECURITY SENTINEL (a 'vertical' monitor).

Reads the VM's OWN facts (the on-VM soc-sensor's events.jsonl: load, mem, disk, ssh_fail, ext_ports,
top_auth_ip) plus the SOC's already-scored behavioural IP profiles — NOT AI guesses — and returns a simple
RED / GREEN health verdict for the owner.

On RED it raises SECURITY-ALARM approvals (a SEPARATE, individually-approved red channel — never part of
'approve all') with a recommended action and a fix plan (package/code fixes: LOCAL first, then DEPLOY —
never hot-patched on the VM) and fires a red notification. On GREEN it fires a green 'healthy' notification.

Nothing is ever auto-applied. The owner's dynamic admin IP is allow-listed so it is never flagged/blocked.
Lightweight by design: one small read of the sensor file + the local profiles — it does NOT run heavy scans
on the VM (so it never exhausts it).
"""
from __future__ import annotations
import json, datetime, pathlib

PID = "vm-sentinel"
SOC_PID = "redberry-continuous-soc"


def _sensor_events(n: int = 40):
    """One small read of the VM's own sensor log (facts produced ON the VM, not by AI)."""
    try:
        import soc_run  # type: ignore
        pw = soc_run._vm_pw()
        cmd = "echo " + repr(pw) + " | sudo -S bash -c \"tail -" + str(int(n)) + " /home/mostafa/soc-sensor/events.jsonl 2>/dev/null\""
        ok, out = soc_run._ssh_ro(cmd, timeout=22)
    except Exception:
        return False, []
    evs = []
    for line in (out or "").splitlines():
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                evs.append(json.loads(line))
            except Exception:
                pass
    return bool(ok), evs


def _owner_ips() -> set:
    try:
        import soc_behavior  # type: ignore
        return soc_behavior._owner_allowlist(SOC_PID)
    except Exception:
        return set()


def _top_suspicious() -> list:
    """The SOC's ALREADY-computed behavioural profiles (read the persisted file — no heavy re-scan)."""
    p = pathlib.Path("workspace/projects/" + SOC_PID + "/data/soc/knowledge/visitor-behavior-profiles.json")
    try:
        d = json.loads(p.read_text()) if p.exists() else {}
    except Exception:
        d = {}
    profs = d.get("profiles", []) if isinstance(d, dict) else []
    return sorted([x for x in profs if x.get("score", 0) >= 0.4], key=lambda x: -x.get("score", 0))


def vm_health() -> dict:
    """RED / GREEN verdict from the VM's own facts. RED lists findings + recommended (gated) actions."""
    ok, evs = _sensor_events(40)
    latest = evs[-1] if evs else {}
    findings = []

    disk = latest.get("disk_pct")
    if isinstance(disk, (int, float)) and disk >= 90:
        findings.append({"kind": "disk", "fact": f"disk {disk}% full",
                         "recommended": "free space / rotate logs; find what filled it",
                         "fix_plan": "diagnose, fix in LOCAL, apply via DEPLOY — not ad-hoc on the VM"})

    mem = latest.get("mem_avail_kb")
    if isinstance(mem, (int, float)) and mem < 200000:
        findings.append({"kind": "memory", "fact": f"only {mem} KB free — possible data-flood/abuse or leak",
                         "recommended": "find the process/endpoint eating memory; add input & rate limits",
                         "fix_plan": "reproduce & fix in LOCAL (limits/patch), then DEPLOY; never hot-patch the VM"})

    sshf = [e.get("ssh_fail", 0) for e in evs if isinstance(e.get("ssh_fail"), (int, float))]
    if sshf and max(sshf) >= 20:
        findings.append({"kind": "ssh-bruteforce", "fact": f"SSH failed logins spiked to {max(sshf)}",
                         "recommended": "propose an edge/UFW block for the source IP",
                         "fix_plan": "edge block AFTER your approval; your own dynamic IP stays allow-listed"})

    ports = [e.get("ext_ports") for e in evs if isinstance(e.get("ext_ports"), (int, float))]
    if ports and latest.get("ext_ports", 0) > min(ports):
        findings.append({"kind": "new-listener", "fact": f"external listening ports changed ({min(ports)}→{latest.get('ext_ports')})",
                         "recommended": "identify the new listener; confirm expected or close it",
                         "fix_plan": "investigate first; any close/config change goes via DEPLOY, gated"})

    owner = _owner_ips()
    for s in _top_suspicious():
        ip = s.get("ip")
        if ip in owner or s.get("score", 0) < 0.45:
            continue
        findings.append({"kind": "attacker", "fact": f"IP {ip} score {s.get('score')} — {'; '.join(s.get('reasons', [])[:2])}",
                         "recommended": f"propose edge block for {ip} / its proxy range",
                         "fix_plan": "edge/UFW block, your IP allow-listed; on-demand, gated"})

    status = "red" if findings else "green"
    return {"status": status, "sensor_reachable": ok, "checked": datetime.datetime.now().isoformat(),
            "latest": latest, "findings": findings,
            "summary": ("All clear — VM healthy; attacker attempts are being prevented." if status == "green"
                        else f"{len(findings)} security item(s) need your attention.")}


def run_sentinel(pid: str = PID, create_alarms: bool = True) -> dict:
    """Full sentinel run: verdict → red/green notification → (on RED) individual SECURITY-ALARM approvals →
    a red/green message posted into the project so the ▶ Run button shows the status in place. Applies nothing."""
    h = vm_health()
    green = h["status"] == "green"

    try:
        import notifications_store as nt  # type: ignore
        if green:
            nt.add("finding", "🟢 VM healthy — all clear", body=h["summary"], pid=pid,
                   project_name="VM Security Sentinel", severity="info", icon="🟢")
        else:
            nt.add("finding", "🔴 SECURITY ALARM — action needed", body=h["summary"], pid=pid,
                   project_name="VM Security Sentinel", severity="critical", icon="🔴")
    except Exception:
        pass

    approvals_made = []
    if create_alarms and not green:
        try:
            import approvals  # type: ignore
            for f in h["findings"]:
                a = approvals.create_security(
                    pid, "Intrusion Detection & Behavioral Analytics Agent",
                    title=f["fact"], summary=f.get("recommended", ""),
                    recommended=f.get("recommended", ""), fix_plan=f.get("fix_plan", ""))
                approvals_made.append(a["id"])
        except Exception:
            pass

    try:
        import scopes  # type: ignore
        scope = f"project:{pid}"
        cid = scopes.create_chat(scope, title="▶ VM status")["id"]
        emoji = "🟢" if green else "🔴"
        body = f"{emoji} **VM {h['status'].upper()}** — {h['summary']}\n\nlatest VM facts: `{h.get('latest')}`\n"
        for f in h["findings"]:
            body += f"\n- 🔴 **{f['fact']}** → recommended: {f['recommended']}  _(fix: {f['fix_plan']})_"
        if not green:
            body += "\n\n_These are SECURITY-ALARM approvals — decide each one individually; they are never part of 'approve all'._"
        scopes.add_message(scope, cid, "assistant", body)
        scopes.sync_up(scope, f"▶ VM status: {h['status']}")
    except Exception:
        pass

    h["approvals_made"] = approvals_made
    return h
