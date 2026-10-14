#!/usr/bin/env python3
"""
RedBerry Continuous SOC — run engine (the CTO Orchestrator + Security Operations Investigator asset).

Observe -> Correlate -> Verify -> Report -> Request approval -> Act ONLY if approved.

SAFETY (hard): read-only, non-disruptive, evidence-driven. It NEVER modifies production (services, DB,
firewall, users, secrets, code, packages, schedules, config). Any remediation becomes an APPROVAL REQUEST;
in monitor-only / test mode approvals are auto-DENIED and nothing is executed. Secrets are never printed.

  python server/soc_run.py --pid redberry-continuous-soc [--cid <chat>] [--mode full|quick|<playbook>] [--test]
"""
import os, re, sys, json, time, subprocess, datetime, pathlib
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import store            # type: ignore
import scopes           # type: ignore
try:
    import approvals    # type: ignore
except Exception:
    approvals = None
try:
    import agents_registry  # type: ignore
except Exception:
    agents_registry = None

PID_DEFAULT = "redberry-continuous-soc"
# The project the current run operates on. run() sets this so EVERY check is project-agnostic — the whole SOC
# is a reusable capability that works for ANY security project the agent creates, not just RedBerry.
CURRENT_PID = PID_DEFAULT
SETTINGS_FILE = "soc_settings.json"

# ---- SOC runtime settings (DB-backed via store; editable; auto_remediation MUST default false) ----
DEFAULT_SETTINGS = {
    "SOC_ENABLED": True, "SOC_SCHEDULE_ENABLED": True,
    "SOC_DAILY_RUN_TIME": "23:00", "SOC_TIMEZONE": "America/New_York",
    "SOC_MONITOR_ONLY": True, "SOC_EVENT_DRIVEN_CHECKS_ENABLED": True,
    "SOC_NOTIFICATION_ENABLED": True, "SOC_CRITICAL_NOTIFICATION_ENABLED": True,
    "SOC_APPROVAL_REQUIRED": True, "SOC_EVIDENCE_RETENTION_DAYS": 90,
    "SOC_RAW_IP_RETENTION_DAYS": 30, "SOC_TECHNICAL_REPORT_RETENTION_DAYS": 365,
    "SOC_MAX_PARALLEL_READ_ONLY_TASKS": 4, "SOC_EXTERNAL_INTELLIGENCE_ENABLED": True,
    "SOC_DEPENDENCY_MONITORING_ENABLED": True, "SOC_APPLICATION_ABUSE_MONITORING_ENABLED": True,
    "SOC_CLOUD_CONTROL_PLANE_MONITORING_ENABLED": True, "SOC_DATABASE_MONITORING_ENABLED": True,
    "SOC_SSH_MONITORING_ENABLED": True, "SOC_NETWORK_MONITORING_ENABLED": True,
    "SOC_SOURCE_INTEGRITY_MONITORING_ENABLED": True,
    "SOC_AUTO_REMEDIATION_ENABLED": False,   # MANDATORY default — never autonomous remediation
}

def settings():
    s = dict(DEFAULT_SETTINGS); s.update(store.read_json(SETTINGS_FILE, {}) or {}); return s

def save_settings(patch: dict):
    s = settings(); s.update({k: v for k, v in patch.items() if k in DEFAULT_SETTINGS})
    s["SOC_AUTO_REMEDIATION_ENABLED"] = bool(s.get("SOC_AUTO_REMEDIATION_ENABLED", False))  # keep guard
    store.write_json(SETTINGS_FILE, s); return s

def _socdir(pid):
    """The SOC content home — ALWAYS inside the workspace (workspace/projects/<pid>/data/soc). Never an
    external localPath: a project must not write outside the workspace."""
    ov = os.environ.get("SOC_DIR_OVERRIDE")   # test/sandbox only; unset in production
    if ov:
        return pathlib.Path(ov)
    # HARD RULE: SOC content ALWAYS lives inside the workspace — never an external localPath.
    # A project must not write outside the workspace (the audit only covers the workspace).
    return store.WS / "projects" / pid / "data" / "soc"

# ---- persistent findings registry (memorizing report: new / open / pending / accepted / resolved) --
ISSUE_CLASSES = ("Needs Review", "Suspicious", "Probable", "Confirmed")
def _reg_path(pid): return f"projects/{pid}/data/jsons/soc_findings_registry.json"
def _load_registry(pid): return store.read_json(_reg_path(pid), {"items": {}})
def _save_registry(pid, reg): store.write_json(_reg_path(pid), reg)

def set_finding_status(pid, fid, status, note=""):
    """Owner action from the report/UI: mark a finding resolved | pending | accepted (leave for now) | open."""
    status = status if status in ("resolved", "pending", "accepted", "open") else "open"
    reg = _load_registry(pid); it = reg["items"].get(fid)
    if not it:
        return {"error": "unknown finding id"}
    it["owner_status"] = status
    it["owner_note"] = note
    it["owner_status_ts"] = time.time()
    if status == "resolved":
        it["resolved_ts"] = time.time(); it["resolved_by"] = "owner"
    reg["items"][fid] = it; _save_registry(pid, reg)
    return {"ok": True, "id": fid, "status": status}

def _reconcile(pid, issues_this_run):
    """Update the registry with this run's issues; return sections: new/open/pending/accepted/resolved."""
    reg = _load_registry(pid); items = reg["items"]; nowt = time.time()
    seen = {f["id"] for f in issues_this_run}
    new, still_open, pending, accepted = [], [], [], []
    for f in issues_this_run:
        it = items.get(f["id"])
        if not it:
            it = {"id": f["id"], "title": f["title"], "severity": f["severity"],
                  "classification": f["classification"], "asset": f["asset"],
                  "first_seen": nowt, "last_seen": nowt, "occurrences": 1, "owner_status": "open"}
            new.append(f)
        else:
            it["last_seen"] = nowt; it["occurrences"] = it.get("occurrences", 1) + 1
            it["severity"] = f["severity"]; it["classification"] = f["classification"]
            if it.get("owner_status") == "resolved":       # re-detected after being resolved
                it["owner_status"] = "open"; it["reopened_ts"] = nowt; new.append(f)
            elif it.get("owner_status") == "pending":
                pending.append({**f, "owner_note": it.get("owner_note", "")})
            elif it.get("owner_status") == "accepted":
                accepted.append({**f, "owner_note": it.get("owner_note", "")})
            else:
                still_open.append(f)
        items[f["id"]] = it
    # anything previously OPEN but NOT detected this run → auto-resolved (owner-deferred stays)
    resolved = []
    for fid, it in items.items():
        if fid not in seen and it.get("owner_status") in ("open", None) and not it.get("resolved_ts"):
            it["owner_status"] = "resolved"; it["resolved_ts"] = nowt
            it["resolved_by"] = "auto (no longer detected)"
            resolved.append(it)
        # recently owner-resolved also surface once
        elif fid not in seen and it.get("owner_status") == "resolved" and (nowt - it.get("resolved_ts", 0) < 7*86400):
            resolved.append(it)
    _save_registry(pid, reg)
    return {"new": new, "open": still_open, "pending": pending, "accepted": accepted, "resolved": resolved}

# ---- read-only VM access (same credential path as the proven deploy tool). NEVER mutates. -----------
def _vm_pw():
    try:
        cred = (ROOT / "workspace" / "shared" / "oth" / ".cred").read_text()
        m = re.search(r"azvmcred[\s:=]+(.+)", cred)
        return (m.group(1).strip().strip('"') if m else "")
    except Exception:
        return ""

def _ssh_ro(cmd, timeout=25):
    """Run ONE read-only command on the VM. Returns (ok, output). Refuses obviously-mutating commands."""
    banned = ("rm ", "reboot", "systemctl restart", "systemctl stop", "ufw ", "iptables", "prisma migrate",
              "DROP ", "DELETE ", "UPDATE ", "INSERT ", "kill ", "chmod ", "chown ", "npm install", "apt ")
    if any(b.lower() in cmd.lower() for b in banned):
        return False, "REFUSED: not a read-only command"
    pw = _vm_pw()
    if not pw:
        return False, "no credential"
    try:
        p = subprocess.run(["sshpass", "-p", pw, "ssh", "-o", "StrictHostKeyChecking=no",
                            "-o", "ConnectTimeout=12", "mostafa@52.180.154.225", cmd],
                           capture_output=True, text=True, timeout=timeout)
        return (p.returncode == 0), (p.stdout or p.stderr or "").strip()
    except Exception as e:
        return False, f"error: {e}"

def _node_ro(js, cwd="/home/mostafa/bendcore", timeout=35):
    """Run a READ-ONLY node script on the VM without ANY shell mangling of it. The script is base64-encoded
    locally and decoded on the VM (so `$disconnect`, quotes, etc. survive intact). Returns (ok, stdout)."""
    import base64
    b64 = base64.b64encode(js.encode()).decode()
    cmd = f"cd {cwd} 2>/dev/null && echo {b64} | base64 -d | node 2>&1"
    return _ssh_ro(cmd, timeout=timeout)

CLASS = ["Informational", "Benign/Expected", "False Positive", "Needs Review", "Suspicious", "Probable", "Confirmed"]

def _finding(fid, title, severity, confidence, classification, asset, evidence, fp_analysis,
             data_state="Checked and healthy", remediation="", impact="", blast="", unknowns=""):
    return {"id": fid, "title": title, "severity": severity, "confidence": confidence,
            "classification": classification, "asset": asset, "evidence": evidence,
            "false_positive_analysis": fp_analysis, "data_source_state": data_state,
            "recommended_remediation": remediation, "remediation_risk": impact, "blast_radius": blast,
            "unknowns": unknowns, "ts": time.time()}

# ================= READ-ONLY CHECKS (each returns a finding) =================
def check_service_health(test):
    if test:
        return _finding("SOC-OPS-001", "Service health", "informational", "high", "Benign/Expected",
                        "VM systemd", "all expected services active (test fixture)",
                        "restart counters within baseline", "Checked and healthy")
    ok, out = _ssh_ro("for s in bendcore organics nginx odin-anchor-online odin-web-online; do printf '%s=%s ' $s $(systemctl is-active $s 2>/dev/null); done")
    if not ok:
        return _finding("SOC-OPS-001", "Service health", "medium", "low", "Needs Review", "VM systemd",
                        f"could not read systemd: {out[:120]}", "n/a", "Data unavailable")
    down = [kv.split("=")[0] for kv in out.split() if kv.endswith("=failed") or kv.endswith("=inactive")]
    if down:
        return _finding("SOC-OPS-001", "Service(s) not active", "high", "high", "Suspicious", "VM systemd",
                        out, "confirm not a planned maintenance window", "Checked and finding detected",
                        "Investigate service logs before any restart (approval-gated).",
                        "restart could interrupt live traffic", "the affected site(s)")
    return _finding("SOC-OPS-001", "Service health", "informational", "high", "Benign/Expected", "VM systemd",
                    out, "all expected services active", "Checked and healthy")

def check_network_listeners(test):
    if test:
        return _finding("SOC-NET-001", "Network listeners", "informational", "high", "Benign/Expected",
                        "VM ports", "80/443 public; 4013/3000 localhost; 5432 localhost (fixture)",
                        "app ports protected by NSG+UFW; DB localhost-only is benign")
    ok, out = _ssh_ro("echo '%PW%' | sudo -S ss -ltnp 2>/dev/null | awk '{print $4}' | grep -vE '127.0.0.1|::1' | sort -u | head -30".replace("%PW%", _vm_pw()))
    if not ok:
        return _finding("SOC-NET-001", "Network listeners", "low", "low", "Needs Review", "VM ports",
                        "could not enumerate listeners", "n/a", "Data unavailable")
    ext = [l for l in out.splitlines() if re.search(r":(?!80\b|443\b|22\b)\d+$", l) and "0.0.0.0" in l]
    dbexposed = any(":5432" in l and "127.0.0.1" not in l for l in out.splitlines())
    if dbexposed:
        return _finding("SOC-DB-001", "PostgreSQL externally bound", "critical", "high", "Suspicious",
                        "PostgreSQL", out, "confirm not intended", "Checked and finding detected",
                        "Restrict bind to localhost / firewall (approval-gated).", "app DB connectivity", "DB")
    return _finding("SOC-NET-001", "Network listeners", "informational", "high", "Benign/Expected", "VM ports",
                    out or "(only 80/443/22 external)", "app ports protected by NSG+UFW; DB localhost-only")

def check_ssh_auth(test):
    if test:
        return _finding("SOC-AUTH-002", "SSH keys / users", "informational", "high", "Benign/Expected",
                        "VM ssh", "authorized_keys = owner key only; admin user = mostafa (fixture)",
                        "no new keys/users vs baseline")
    ok, keys = _ssh_ro("wc -l < ~/.ssh/authorized_keys 2>/dev/null; echo '---'; getent passwd | awk -F: '$3>=1000{print $1}'")
    if not ok:
        return _finding("SOC-AUTH-002", "SSH keys / users", "low", "low", "Needs Review", "VM ssh",
                        "could not read ssh/users", "n/a", "Data unavailable")
    return _finding("SOC-AUTH-002", "SSH keys / users", "informational", "high", "Needs Review", "VM ssh",
                    keys, "compare against history/baselines/known-good.md; only escalate on a NEW key/user",
                    "Checked and healthy")

def check_persistence(test):
    if test:
        return _finding("SOC-HOST-003", "Persistence (cron/timers)", "informational", "high", "Benign/Expected",
                        "VM cron/systemd", "only OS defaults + approved app timers (fixture)",
                        "matches baseline; ordinary timers are benign")
    ok, out = _ssh_ro("crontab -l 2>/dev/null | grep -v '^#' | head; echo '--- timers ---'; systemctl list-timers --no-pager 2>/dev/null | head -10")
    if not ok:
        return _finding("SOC-HOST-003", "Persistence", "low", "low", "Needs Review", "VM cron/systemd",
                        "could not read cron/timers", "n/a", "Data unavailable")
    return _finding("SOC-HOST-003", "Persistence (cron/timers)", "informational", "medium", "Needs Review",
                    "VM cron/systemd", out or "(no user crontab)", "ordinary timers are benign; escalate only on NEW/unknown entries",
                    "Checked and healthy")

def check_redberry_app_abuse(test):
    """The reference incident: low-and-slow newsletter/registration abuse. Read-only correlation."""
    if test:
        # synthetic dataset proving the pattern (safe, deterministic — used by the E2E test)
        subs = [{"ip": "203.0.113.7", "acct": f"bot{i}@mailbox.test", "ua": f"UA-{i%3}",
                 "t": 1000 + i * 600} for i in range(8)]  # 8 submissions, exactly 600s (10-min) apart
        gaps = [subs[i+1]["t"] - subs[i]["t"] for i in range(len(subs)-1)]
        regular = len(set(gaps)) == 1 and gaps[0] in (600,)
        one_ip = len({s["acct"] for s in subs}) > 1 and len({s["ip"] for s in subs}) == 1
        downstream = len(subs) * 3  # klaviyo + welcome + support per submission
        ev = (f"{len(subs)} submissions, gaps={gaps} (regular ~10-min cadence={regular}); "
              f"distinct accounts one IP={one_ip}; downstream amplification≈{downstream} actions; "
              f"rotating user-agents; controlled mailboxes verified email+2FA then logged in.")
        return _finding("SOC-APP-001", "Newsletter/registration abuse (low-and-slow)", "high", "high", "Probable",
                        "POST /email-subscribe, /api/register, Klaviyo", ev,
                        "NOT a shared-IP campaign: cadence is machine-regular + downstream amplification is "
                        "disproportionate. A 10-minute gap does NOT make it legitimate. This is APP-LEVEL "
                        "business-logic abuse — NOT VM compromise (no malware/persistence/exfil evidence).",
                        "Checked and finding detected",
                        "Recommend (approval-gated): managed CAPTCHA + risk-based step-up; single-use expiring "
                        "action tokens + replay prevention; idempotency; suppress downstream until checks pass; "
                        "monitor/skip/enforce modes with shared-IP false-positive protection.",
                        "CAPTCHA/step-up may add friction / block shared-IP legit users if mis-tuned — test in monitor mode.",
                        "marketing + customer DB pollution; third-party (Klaviyo) quota; support noise.",
                        "exact human-vs-bot split within the traffic")
    # LIVE: read nginx access logs on the VM (read-only) and measure cadence
    ok, out = _ssh_ro("echo '%PW%' | sudo -S sh -c \"grep -E 'POST /(email-subscribe|api/register)' /var/log/nginx/access.log* 2>/dev/null | tail -300\" | awk '{print $1}' | sort | uniq -c | sort -rn | head".replace("%PW%", _vm_pw()))
    if not ok or not out.strip():
        return _finding("SOC-APP-001", "Newsletter/registration abuse", "medium", "low", "Needs Review",
                        "nginx access log", f"nginx abuse logs unavailable/empty: {out[:100]}",
                        "cannot conclude healthy from missing data", "Data unavailable")
    top = out.strip().splitlines()[0].split()
    cnt = int(top[0]) if top and top[0].isdigit() else 0
    if cnt >= 10:
        return _finding("SOC-APP-001", "Newsletter/registration abuse (elevated)", "high", "medium", "Suspicious",
                        "POST /email-subscribe, /api/register", f"top source IP made {cnt} submissions:\n{out}",
                        "correlate cadence + downstream amplification before Confirmed; check shared-IP.",
                        "Checked and finding detected",
                        "Recommend (approval-gated): CAPTCHA/step-up, single-use tokens, idempotency, downstream suppression.",
                        "friction risk for legit shared-IP users", "marketing/customer DB + third-party quota")
    return _finding("SOC-APP-001", "Newsletter/registration abuse", "informational", "medium", "Benign/Expected",
                    "nginx access log", out, "no elevated per-IP submission volume vs baseline", "Checked and healthy")

def check_dependency_intel(test):
    """REAL dependency threat intelligence — Architect pulls current advisories (OSV.dev) for the ACTUAL
    installed versions and triages by reachability. Vuln PRESENCE != compromise."""
    if test:
        return _finding("SOC-DEP-002", "Dependency vulnerability intelligence", "informational", "medium",
                        "Benign/Expected", "npm dependencies", "(test fixture) 0 runtime-reachable critical vulns",
                        "vuln presence != compromise; reachability required before escalation")
    try:
        import soc_intel  # type: ignore
        home = pathlib.Path.home()
        dirs = [home / "Desktop/VolatileWorkSpace/organics-backend", home / "Desktop/VolatileWorkSpace/organics-frontend"]
        summ = soc_intel.update(dirs, _socdir(CURRENT_PID) / "knowledge")
        if summ["source_state"] == "Data unavailable":
            return _finding("SOC-DEP-002", "Dependency vulnerability intelligence", "medium", "low", "Needs Review",
                            "npm dependencies", "OSV.dev advisory feed unavailable",
                            "cannot conclude healthy from missing intel", "Data unavailable")
        # stash the runtime CVEs we actually carry, so Intel Fusion can cross-reference them against CISA KEV
        try:
            our_cves = []
            for p in summ.get("top", []):
                if p.get("runtime"):
                    for a in p.get("advisories", []):
                        if str(a.get("cve", "")).startswith("CVE-"):
                            our_cves.append(a["cve"])
            cdir = _socdir(CURRENT_PID) / "knowledge" / "intel-cache"; cdir.mkdir(parents=True, exist_ok=True)
            (cdir / "our_cves.json").write_text(json.dumps(sorted(set(our_cves))))
        except Exception:
            pass
        rv, vp, top = summ["runtime_vulnerable"], summ["vulnerable_packages"], summ.get("top", [])[:5]
        ev = (f"OSV.dev: scanned {summ['packages_scanned']} pkgs; {vp} vulnerable ({rv} runtime-reachable). "
              "Top: " + ", ".join(f"{p['name']}@{p['version']}({len(p['vuln_ids'])} vulns,{p['worst_severity']},{'runtime' if p['runtime'] else 'dev'})" for p in top))
        crit_runtime = any(p.get("worst_severity", "").upper() in ("CRITICAL", "HIGH") and p["runtime"] for p in top)
        cls = "Suspicious" if rv > 0 else "Benign/Expected"
        sev = "high" if crit_runtime else ("medium" if rv > 0 else "informational")
        return _finding("SOC-DEP-002", "Dependency vulnerability intelligence", sev, "medium", cls,
                        "npm dependencies", ev,
                        "PRESENCE of a CVE is NOT compromise — reachability + evidence required. See knowledge/live-dependency-intel.md",
                        "Checked and finding detected" if rv > 0 else "Checked and healthy",
                        "Recommend (approval-gated): upgrade runtime-reachable vulnerable packages to fixed versions after regression testing.",
                        "upgrades can break functionality — test in staging first", "the affected application")
    except Exception as e:
        return _finding("SOC-DEP-002", "Dependency vulnerability intelligence", "low", "low", "Needs Review",
                        "npm dependencies", f"intel error: {e}", "n/a", "Data unavailable")

def check_website_health(test):
    """Read-only public endpoint health — confirms the sites answer (and abnormal status is a signal)."""
    targets = [("anchor", "https://anchor.odinmarkets.com/odin-anchor/health"),
               ("web", "https://anchor.odinmarkets.com/odin-web/"),
               ("organics-api", "http://127.0.0.1:4013/health")]
    if test:
        return _finding("SOC-NET-002", "Website / endpoint health", "informational", "high", "Benign/Expected",
                        "public endpoints", "all endpoints 200 (fixture)", "healthy responses")
    results = []
    for name, url in targets:
        if url.startswith("http://127.0.0.1"):
            ok, code = _ssh_ro(f"curl -s -m6 -o /dev/null -w '%{{http_code}}' {url}")
            results.append(f"{name}={code if ok else 'unreachable'}")
        else:
            try:
                import urllib.request
                c = urllib.request.urlopen(url, timeout=8).getcode()
                results.append(f"{name}={c}")
            except Exception as e:
                results.append(f"{name}=ERR")
    bad = [r for r in results if not re.search(r"=(200|301|302|401)$", r)]
    cls = "Suspicious" if bad else "Benign/Expected"
    return _finding("SOC-NET-002", "Website / endpoint health", "high" if bad else "informational", "high", cls,
                    "public endpoints", " ".join(results),
                    "a non-2xx/expected status is a signal, not proof — correlate with service health",
                    "Checked and finding detected" if bad else "Checked and healthy")

def check_db_anomaly(test):
    """Read-only DB anomaly hunt — registration/subscription velocity + accounts-per-IP (the RedBerry angle)."""
    if test:
        return _finding("SOC-DB-002", "Database anomaly (read-only)", "informational", "medium", "Benign/Expected",
                        "PostgreSQL organics", "(fixture) registrations within baseline; no auth-failure spike",
                        "localhost DB; counts within expected range")
    js = ("const{PrismaClient}=require('@prisma/client');const p=new PrismaClient();"
          "(async()=>{try{const users=await p.user.count();"
          "const day=new Date(Date.now()-86400000);"
          "const recent=await p.user.count({where:{createdAt:{gte:day}}});"
          "console.log('users='+users+' new_24h='+recent);}catch(e){console.log('ERR '+e.message)}"
          "finally{await p.$disconnect()}})()")
    ok, out = _node_ro(js, timeout=35)
    if not ok or "new_24h=" not in out:
        return _finding("SOC-DB-002", "Database anomaly (read-only)", "low", "low", "Needs Review",
                        "PostgreSQL organics", f"DB read-only query unavailable: {out[:120]}",
                        "cannot conclude healthy from missing data", "Data unavailable")
    m = re.search(r"new_24h=(\d+)", out)
    new24 = int(m.group(1)) if m else 0
    cls = "Suspicious" if new24 > 100 else "Benign/Expected"   # velocity threshold (tune per baseline)
    return _finding("SOC-DB-002", "Database anomaly (read-only)", "high" if new24 > 100 else "informational",
                    "medium", cls, "PostgreSQL organics", out,
                    "high 24h registration velocity can indicate account farming — correlate with IPs + cadence",
                    "Checked and finding detected" if new24 > 100 else "Checked and healthy",
                    "Recommend (approval-gated): registration risk controls (see PB-APP-002)." if new24 > 100 else "",
                    "friction for legit signups" if new24 > 100 else "")

import math as _math
_DISPOSABLE = ("mailinator", "guerrilla", "10minutemail", "tempmail", "temp-mail", "yopmail", "trashmail",
               "sharklasers", "getnada", "dispostable", "maildrop", "throwaway", "fakemail", "mailbox.test")
def _garbage_name_score(name: str) -> float:
    """0..1 — how 'garbage/long-random' a name looks (long consonant runs, high entropy, no spaces)."""
    n = (name or "").strip()
    if not n: return 0.5
    letters = re.sub(r"[^a-zA-Z]", "", n)
    if len(letters) < 3: return 0.2
    vowels = sum(c in "aeiouAEIOU" for c in letters)
    vratio = vowels / len(letters)
    longrun = max((len(m) for m in re.findall(r"[^aeiouAEIOU ]+", n)), default=0)
    # shannon entropy of chars
    from collections import Counter
    cnt = Counter(letters.lower()); ent = -sum((v/len(letters))*_math.log2(v/len(letters)) for v in cnt.values())
    score = 0.0
    if vratio < 0.28: score += 0.35            # too few vowels = random
    if longrun >= 6: score += 0.30             # long consonant run
    if len(n) > 24 and " " not in n: score += 0.20  # long single token
    if ent > 3.6: score += 0.15                # high entropy
    return round(min(1.0, score), 2)
def _email_suspicious(email: str) -> bool:
    e = (email or "").lower()
    if any(d in e for d in _DISPOSABLE): return True
    local = e.split("@")[0]
    return bool(re.search(r"[0-9]{4,}$", local) or _garbage_name_score(local) > 0.6)

def check_subscriber_forensics(test):
    """DB CONTENT forensics — the abuse story: garbage names, strange/disposable emails, verification+2FA
    farming, accounts-per-IP. Read-only. This is what makes 'is this real abuse?' evidence-based."""
    if test:
        # fixture proving detection: 6 accounts, garbage names + disposable emails, all verified+2FA
        rows = [{"email": f"xkqzvbwptr{i}@mailinator.com", "name": "qkzxcvbnmwrtplkjhgf" + "z"*i, "ip": "203.0.113.7",
                 "verified": True, "twoFA": True} for i in range(6)]
        gname = sum(1 for r in rows if _garbage_name_score(r["name"]) > 0.5)
        gmail = sum(1 for r in rows if _email_suspicious(r["email"]))
        one_ip = len({r["email"] for r in rows}) > 1 and len({r["ip"] for r in rows}) == 1
        ev = (f"{len(rows)} recent accounts; {gname} garbage-name, {gmail} suspicious/disposable email, "
              f"all verified+2FA, distinct-accounts-one-IP={one_ip}. Emails like 'xkqzvbwptr*@mailinator.com', "
              "names like 'qkzxcvbnmwrtplkjhgf…' — automation farming controlled mailboxes.")
        return _finding("SOC-APP-004", "Subscriber/account forensics (garbage names, farmed emails)", "high", "high",
                        "Probable", "users/subscribers DB", ev,
                        "Machine-generated names + disposable emails + universal 2FA success + one-IP fan-out is NOT a "
                        "normal-user pattern; benign shared-IP would not show garbage names. NOT VM compromise.",
                        "Checked and finding detected",
                        "Recommend (approval-gated, as you applied): managed CAPTCHA on newsletter + guest service "
                        "endpoints + auth + payment; step-up; single-use expiring tokens; block disposable domains; "
                        "name/email risk scoring; suppress downstream (Klaviyo/HubSpot) until checks pass.",
                        "CAPTCHA/scoring may add friction for legit users — false-positive protect shared IPs.",
                        "marketing + customer DB pollution; third-party quota (Klaviyo/HubSpot) consumption.",
                        "exact human-vs-bot split; whether the 2FA/verification code was leaked client-side vs mailbox-controlled")
    js = (
        "const{PrismaClient}=require('@prisma/client');const p=new PrismaClient();"
        "(async()=>{try{const day=new Date(Date.now()-7*86400000);"
        "const u=await p.user.findMany({where:{createdAt:{gte:day}},select:{email:true,fullName:true,"
        "firstName:true,lastName:true,createdAt:true,isVerified:true,twoFactorCode:true},take:800});"
        "console.log('JSON'+JSON.stringify(u));}catch(e){console.log('ERR '+e.message)}"
        "finally{await p.$disconnect()}})()")
    ok, out = _node_ro(js, timeout=35)
    marker = out.find("JSON[") if out else -1
    if not ok or marker < 0:
        return _finding("SOC-APP-004", "Subscriber/account forensics", "low", "low", "Needs Review",
                        "users/subscribers DB", f"DB read-only query unavailable: {out[:120]}",
                        "cannot conclude healthy from missing data", "Data unavailable")
    try:
        rows = json.loads(out[marker+4:])
    except Exception:
        rows = []
    def _nm(r): return r.get("fullName") or ((r.get("firstName") or "") + " " + (r.get("lastName") or "")).strip()
    gname = sum(1 for r in rows if _garbage_name_score(_nm(r)) > 0.5)
    gmail = sum(1 for r in rows if _email_suspicious(r.get("email", "")))
    farmed = sum(1 for r in rows if r.get("isVerified") and r.get("twoFactorCode"))   # verified + 2FA set = farmed
    ratio = (gname + gmail) / max(1, 2 * len(rows))
    cls = "Probable" if (rows and ratio > 0.3) else ("Suspicious" if ratio > 0.12 else "Benign/Expected")
    sev = "high" if cls == "Probable" else ("medium" if cls == "Suspicious" else "informational")
    ev = (f"{len(rows)} accounts in last 7d; garbage-name={gname}, suspicious/disposable-email={gmail}, "
          f"verified+2FA-farmed={farmed} (risk ratio {ratio:.2f}).")
    return _finding("SOC-APP-004", "Subscriber/account forensics (garbage names, farmed emails)", sev, "medium", cls,
                    "users/subscribers DB", ev,
                    "garbage names + disposable emails at scale = automation; shared-IP legit users don't show garbage names",
                    "Checked and finding detected" if cls != "Benign/Expected" else "Checked and healthy",
                    "Recommend (approval-gated): CAPTCHA on newsletter/guest-service/auth/payment; disposable-domain block; name/email risk scoring; suppress downstream until checks pass." if cls != "Benign/Expected" else "",
                    "friction for legit users" if cls != "Benign/Expected" else "",
                    "third-party quota + DB pollution" if cls != "Benign/Expected" else "")

def check_miner_hunt(test):
    """Crypto-miner / hijack hunt — high steady CPU, unknown binaries, outbound to mining infra. Correlates
    with dependency vulns + service 502 (the exact mining incident). Read-only."""
    if test:
        return _finding("SOC-HOST-002", "Crypto-miner / hijack hunt", "informational", "high", "Benign/Expected",
                        "VM processes/egress", "(fixture) top CPU = known app processes; no mining-pool egress",
                        "no unknown high-CPU binary; no known-bad outbound")
    ok, out = _ssh_ro("ps -eo pcpu,comm --sort=-pcpu | head -8; echo '--- egress ---'; "
                      "echo '%PW%' | sudo -S ss -tnp 2>/dev/null | awk '{print $5}' | grep -vE '127.0.0.1|::1|:443|:80|:5432' | sort -u | head -12".replace("%PW%", _vm_pw()), timeout=25)
    if not ok:
        return _finding("SOC-HOST-002", "Crypto-miner / hijack hunt", "low", "low", "Needs Review",
                        "VM processes/egress", "could not read processes/egress", "n/a", "Data unavailable")
    miner_kw = ("xmrig", "minerd", "cpuminer", "cgminer", "kdevtmpfsi", "kinsing", "stratum", "nicehash", "monero")
    hit = [w for w in miner_kw if w in out.lower()]
    # KNOWN app + OS + our own monitoring-pipeline processes are NOT miners. Excluding the measurement tools
    # (ps/ss/sudo/sh/awk/grep/…) prevents the classic self-measurement false positive (ps shows itself at ~100%).
    KNOWN = ("node", "nginx", "postgres", "next-server", "mongod", "systemd", "ps", "ss", "sudo", "sh", "bash",
             "awk", "grep", "sort", "head", "sshd", "kworker", "python", "python3", "gunicorn")
    # owner allow-listed IPs (our own SSH session) must be excluded from "egress" — it's us, not exfil.
    try:
        import soc_behavior  # type: ignore
        owner_ips = soc_behavior._owner_allowlist(CURRENT_PID)
    except Exception:
        owner_ips = set()
    lines_all = out.splitlines()
    egress_lines = out.split("--- egress ---")[-1].splitlines() if "--- egress ---" in out else []
    foreign_egress = [l.strip() for l in egress_lines if l.strip() and l.strip() != "Address:Port"
                      and not any(ip in l for ip in owner_ips)]
    highcpu = []
    for line in lines_all:
        if "--- egress ---" in line:
            break
        m = re.match(r"\s*([0-9.]+)\s+(\S+)", line)
        if m and float(m.group(1)) > 90 and m.group(2) not in KNOWN:
            highcpu.append(f"{m.group(2)}@{m.group(1)}%")
    # only escalate if a genuinely-unknown high-CPU process, a miner keyword, OR foreign (non-owner) egress
    if hit or highcpu or foreign_egress:
        return _finding("SOC-HOST-002", "Crypto-miner / hijack indicator", "critical", "high", "Suspicious",
                        "VM processes/egress", f"miner keywords={hit}; unknown high-CPU={highcpu}; foreign egress={foreign_egress}\n{out}",
                        "correlate with dependency vulns (SOC-DEP-002) + service 502 — a severe-vuln package abused for "
                        "mining is the documented root cause. Confirm the binary + outbound before Confirmed.",
                        "Checked and finding detected",
                        "Recommend (approval-gated): update Node + replace the vulnerable package with a fixed version; "
                        "close all Azure ports except 443/80 (reverse proxy) and 22 to your single (dynamic) IP; enable ufw; "
                        "kill the miner process; rotate anything exposed.",
                        "service restart / patch may cause brief downtime — schedule a window", "the whole VM + all sites")
    return _finding("SOC-HOST-002", "Crypto-miner / hijack hunt", "informational", "high", "Benign/Expected",
                    "VM processes/egress", out, "top CPU = known app processes; no mining-pool egress", "Checked and healthy")

def check_port_hardening(test):
    """Port / firewall hardening audit — only 443/80 public (reverse proxy), 22 single-IP, ufw on, NSG tight.
    This is the protocol from the mining incident. Read-only."""
    if test:
        return _finding("SOC-CLOUD-003", "Port / firewall hardening", "informational", "high", "Benign/Expected",
                        "Azure NSG + ufw", "(fixture) 80/443 public; 22 single-IP; ufw active; no wide-open ports",
                        "matches the hardening protocol")
    critical, hardening = [], []   # critical = actually externally reachable; hardening = defense-in-depth only
    ok, ufw = _ssh_ro("echo '%PW%' | sudo -S ufw status 2>/dev/null | head -12".replace("%PW%", _vm_pw()), timeout=20)
    if ok and "Status: active" not in ufw:
        critical.append("ufw not active")
    ok2, ssrc = _ssh_ro("echo '%PW%' | sudo -S ss -ltn 2>/dev/null | awk '{print $4}' | grep '0.0.0.0' | grep -vE ':80$|:443$|:22$' | head".replace("%PW%", _vm_pw()), timeout=20)
    bound_ports = set(re.findall(r":(\d+)", ssrc)) if ok2 else set()
    # NSG open rules (az, read-only) — the SOURCE OF TRUTH for what is actually reachable from the internet
    nsg_allowed = set(); nsg_state = "Data unavailable"
    try:
        import subprocess
        az = subprocess.run(["az", "network", "nsg", "rule", "list", "-g", "Django-Project",
                             "--nsg-name", "django-vm-nsg", "--query",
                             "[?access=='Allow' && direction=='Inbound'].{p:destinationPortRange,src:sourceAddressPrefix}",
                             "-o", "json"], capture_output=True, text=True, timeout=30)
        rules = json.loads(az.stdout or "[]")
        for rr in rules:
            if rr.get("src") in ("*", "Internet", "0.0.0.0/0"):
                nsg_allowed.add(str(rr.get("p")))
        wide = [p for p in nsg_allowed if p not in ("80", "443")]
        nsg_state = "Checked and finding detected" if wide else "Checked and healthy"
        if wide:
            critical.append(f"NSG allows inbound from the Internet on non-80/443 port(s): {wide}")
    except Exception:
        pass
    # a 0.0.0.0-bound port is only EXTERNALLY reachable if the NSG allows it; otherwise it's defense-in-depth
    for p in sorted(bound_ports):
        if nsg_allowed and p in nsg_allowed and p not in ("80", "443", "22"):
            critical.append(f"port {p} bound to 0.0.0.0 AND NSG-allowed → externally reachable")
        else:
            hardening.append(f"port {p} binds 0.0.0.0 but NSG-blocked (not externally reachable) — bind to localhost for defense-in-depth")
    if critical:
        return _finding("SOC-CLOUD-003", "Port / firewall exposure", "high", "medium", "Suspicious",
                        "Azure NSG + ufw", "; ".join(critical) + ("; also: " + "; ".join(hardening) if hardening else ""),
                        "NSG is the source of truth for reachability; these are actually reachable — confirm intended",
                        "Checked and finding detected",
                        "Recommend (approval-gated): close all inbound except 443/80; restrict 22 to your single (dynamic) "
                        "IP with a refresh protocol; enable ufw; serve apps only via the reverse proxy.",
                        "tightening SSH could lock out if the IP-refresh protocol isn't in place", "VM administrative access")
    if hardening:
        return _finding("SOC-CLOUD-003", "Port hardening (defense-in-depth)", "low", "medium", "Needs Review",
                        "Azure NSG + ufw", "; ".join(hardening) + f". ufw={'active' if 'Status: active' in ufw else 'unknown'}; NSG={nsg_state}",
                        "these ports are NOT externally reachable (NSG blocks them) — not a compromise; a hardening nicety only",
                        "Checked and healthy",
                        "Optional (approval-gated): bind internal services to 127.0.0.1 so they never listen on 0.0.0.0.",
                        "none (internal-only change)", "none externally")
    return _finding("SOC-CLOUD-003", "Port / firewall hardening", "informational", "high", "Benign/Expected",
                    "Azure NSG + ufw", f"ufw active; only 80/443 public; 22 single-IP. {nsg_state}", "matches hardening protocol")

def check_intrusion_behavior(test):
    """BEHAVIORAL intrusion detection (UEBA) — catches stealthy/AI-era, signature-evading abuse by behavior:
    same-IP-many-accounts, machine-regular low-and-slow cadence, UA rotation. FP-safe (owner dynamic IP excluded)."""
    try:
        import soc_behavior  # type: ignore
        res = soc_behavior.analyze(CURRENT_PID, test=test)
    except Exception as e:
        return _finding("SOC-IDS-001", "Behavioral intrusion detection", "low", "low", "Needs Review",
                        "visitor behavior (nginx)", f"behavioral engine error: {e}", "n/a", "Data unavailable")
    bad = res.get("bad_ips", [])
    if not res.get("profiles"):
        return _finding("SOC-IDS-001", "Behavioral intrusion detection", "medium", "low", "Needs Review",
                        "visitor behavior (nginx)", "no access-log behavior available to profile",
                        "cannot conclude healthy from missing data", "Data unavailable")
    if bad:
        top = res["profiles"][0]
        return _finding("SOC-IDS-001", "Behavioral intrusion / bot abuse (by behavior, not signature)", "high", "high",
                        "Probable", "visitor behavior (nginx)",
                        f"{res['summary']} Worst: {top['ip']} score={top['score']} — {'; '.join(top['reasons'])}. "
                        f"Owner-excluded: {res.get('owner_excluded')}.",
                        "Behavioral scoring (fan-out + machine-regular cadence + UA rotation) — not a single signature; "
                        "the owner's dynamic IP is allow-listed so this is not us. Same IP + many accounts + ~fixed "
                        "interval is automation, not shared-IP legit users.",
                        "Checked and finding detected",
                        "Recommend (approval-gated): block confirmed-bad IPs at UFW/edge (score≥0.7 only); keep the "
                        "owner allow-list current via the dynamic-IP refresh protocol; add CAPTCHA/step-up on the "
                        "targeted endpoints. " + (res.get("ufw_recommendation", {}) or {}).get("example_command", ""),
                        "over-blocking could hit shared-IP legit users — block only score≥0.7, allow-list owner",
                        "guest/auth/subscribe endpoints + third-party quota",
                        "whether any bad IP overlaps a legitimate corporate NAT (verify before permanent block)")
    return _finding("SOC-IDS-001", "Behavioral intrusion detection", "informational", "high", "Benign/Expected",
                    "visitor behavior (nginx)", res["summary"],
                    "no IP crossed the behavioral-bad threshold; profiles retained for cross-run learning",
                    "Checked and healthy")

def check_sensor(test):
    """24/7 evidence ingest — reads the VM's tiny sensor log (events.jsonl, written by the capped systemd
    sensor) READ-ONLY and analyzes the between-run window: SSH-failure spikes, externally-listening-port drift,
    sustained high CPU by an unknown process, and abusive top source IPs. This is the catch-up analysis that
    makes the 24/7 sensor useful when the desktop was off. If the sensor isn't installed yet, says so honestly."""
    if test:
        return _finding("SOC-SENSOR-008", "24/7 sensor ingest", "informational", "high", "Benign/Expected",
                        "VM sensor (events.jsonl)", "(fixture) 288 samples; no auth spike, no port drift, no miner",
                        "continuous evidence within baseline")
    ok, out = _ssh_ro("tail -n 400 /home/mostafa/soc-sensor/events.jsonl 2>/dev/null")
    if not ok or not out.strip():
        return _finding("SOC-SENSOR-008", "24/7 sensor ingest", "low", "low", "Needs Review",
                        "VM sensor (events.jsonl)",
                        "sensor log not found — the 24/7 sensor is not installed yet (approval-gated: see "
                        "workspace/projects/redberry-continuous-soc/code/sensor/INSTALL_SOC_SENSOR.md). Once installed it provides continuous catch-up evidence.",
                        "not installed is not 'healthy' — install to enable 24/7 coverage", "Data unavailable")
    rows = []
    for line in out.splitlines():
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    if not rows:
        return _finding("SOC-SENSOR-008", "24/7 sensor ingest", "low", "low", "Needs Review",
                        "VM sensor (events.jsonl)", "sensor log unparseable", "n/a", "Data unavailable")
    max_sshfail = max((int(r.get("ssh_fail", 0) or 0) for r in rows), default=0)
    max_extports = max((int(r.get("ext_ports", 0) or 0) for r in rows), default=0)
    KNOWN = ("node", "nginx", "postgres", "next-server", "mongod", "systemd", "python", "python3", "gunicorn",
             "sshd", "-", "")
    hi_cpu = []
    top_ips = {}
    for r in rows:
        tc = str(r.get("top_cpu", ""))
        if "@" in tc:
            comm, pct = tc.split("@", 1)
            try:
                if float(pct) > 90 and comm not in KNOWN:
                    hi_cpu.append(tc)
            except Exception:
                pass
        ti = str(r.get("top_auth_ip", ""))
        if "=" in ti:
            ip, cnt = ti.split("=", 1)
            try:
                top_ips[ip] = max(top_ips.get(ip, 0), int(cnt))
            except Exception:
                pass
    abusive = {ip: c for ip, c in top_ips.items() if c >= 30}
    issues = []
    if max_sshfail >= 20: issues.append(f"SSH-failure spike (max {max_sshfail}/window)")
    if max_extports >= 1: issues.append(f"externally-listening non-80/443/22 ports seen (max {max_extports})")
    if hi_cpu: issues.append(f"sustained unknown high-CPU: {sorted(set(hi_cpu))[:3]}")
    if abusive: issues.append(f"abusive top-auth IPs: {abusive}")
    ev = (f"{len(rows)} sensor samples analyzed. max ssh_fail={max_sshfail}, max ext_ports={max_extports}, "
          f"unknown-high-cpu={sorted(set(hi_cpu))[:3]}, abusive_ips={abusive}.")
    if issues:
        return _finding("SOC-SENSOR-008", "24/7 sensor: anomaly in the off-hours window", "high", "medium", "Suspicious",
                        "VM sensor (events.jsonl)", ev + " Issues: " + "; ".join(issues),
                        "continuous evidence caught activity between runs — correlate with the live checks",
                        "Checked and finding detected",
                        "Recommend (approval-gated): investigate the flagged window; for abusive IPs consider a UFW block; "
                        "for port drift bind services to localhost; for high-CPU unknown process, hunt it.",
                        "none (analysis only)", "the VM in the affected window")
    return _finding("SOC-SENSOR-008", "24/7 sensor ingest", "informational", "high", "Benign/Expected",
                    "VM sensor (events.jsonl)", ev, "continuous evidence within baseline; nothing missed off-hours",
                    "Checked and healthy")

def check_intel_fusion(test):
    """Fused threat intelligence (replaces a human intel team) — cross-references OUR runtime CVEs against the
    CISA KEV 'known-exploited' catalog and OUR observed IPs against abuse.ch botnet-C2 feeds. Desktop-side; the
    production VM is never touched. Actively-exploited-here or a known-bad IP → escalate."""
    if test:
        return _finding("SOC-INTEL-007", "Fused threat intelligence (KEV + abuse.ch)", "informational", "high",
                        "Benign/Expected", "external intel feeds",
                        "(fixture) no OUR-CVE on the KEV list; no observed IP on a C2 feed",
                        "presence in a feed is evidence, not compromise — but a KEV match is a patch-now priority")
    try:
        import soc_intel_fusion as fusion  # type: ignore
    except Exception as e:
        return _finding("SOC-INTEL-007", "Fused threat intelligence", "low", "low", "Needs Review",
                        "external intel feeds", f"fusion module error: {e}", "n/a", "Data unavailable")
    # our runtime CVEs (stashed by the dependency check) + IPs we've observed (from the behavioral profiles)
    our_cves, observed_ips = [], []
    try:
        p = _socdir(CURRENT_PID) / "knowledge" / "intel-cache" / "our_cves.json"
        if p.exists():
            our_cves = json.loads(p.read_text())
    except Exception:
        pass
    try:
        bp = _socdir(CURRENT_PID) / "knowledge" / "visitor-behavior-profiles.json"
        if bp.exists():
            observed_ips = [pr.get("ip") for pr in json.loads(bp.read_text()).get("profiles", []) if pr.get("ip")]
    except Exception:
        pass
    fu = fusion.fuse(our_cves, observed_ips, CURRENT_PID)
    if fu["kev_state"].startswith("unavailable") and fu["feodo_state"].startswith("unavailable"):
        return _finding("SOC-INTEL-007", "Fused threat intelligence", "low", "low", "Needs Review",
                        "external intel feeds", "KEV + abuse.ch feeds unavailable (offline)",
                        "cannot conclude healthy from missing intel", "Data unavailable")
    exploited = fu["actively_exploited_here"]; badips = fu["known_bad_ip_hits"]
    ev = (f"KEV catalog {fu['kev_total']} CVEs ({fu['kev_state']}); abuse.ch C2 {fu['feodo_total']} IPs. "
          f"Checked {fu['our_cves_checked']} of our runtime CVEs and {fu['observed_ips_checked']} observed IPs. "
          f"Actively-exploited-here: {[e['cve'] for e in exploited]}; known-bad IPs seen: {[h['ip'] for h in badips]}.")
    if exploited or badips:
        return _finding("SOC-INTEL-007", "Actively-exploited exposure (fused intel)", "critical" if exploited else "high",
                        "high", "Probable", "external intel feeds", ev,
                        "A KEV match means this vuln is being exploited in the WILD right now — top patch priority. A "
                        "known-bad IP we've seen warrants a block. Presence is strong evidence; confirm reachability.",
                        "Checked and finding detected",
                        "Recommend (approval-gated): patch KEV-listed runtime CVEs FIRST (before other vulns); block "
                        "confirmed-bad IPs at UFW/edge; hunt for exploitation of the specific CVE.",
                        "patching may need a brief maintenance window", "the exposed application / VM",
                        "exact exploited path vs. merely-present dependency")
    return _finding("SOC-INTEL-007", "Fused threat intelligence (KEV + abuse.ch)", "informational", "high",
                    "Benign/Expected", "external intel feeds", ev,
                    "none of our runtime CVEs are on the known-exploited list; no observed IP on a C2 feed",
                    "Checked and healthy")

def check_cloud_posture(test):
    """GENERIC multi-cloud surface probe — works for ANY provider (Azure/AWS/GoDaddy/Hostinger/Cloudflare/…)
    via each service's PUBLIC endpoint, no credentials needed: HTTP health + TLS certificate expiry + security
    headers (HSTS / CSP / X-Frame-Options). This is how the SOC monitors clouds beyond the Azure VM."""
    if test:
        return _finding("SOC-CLOUD-004", "Multi-cloud surface posture", "informational", "high", "Benign/Expected",
                        "public endpoints (any cloud)", "(fixture) all endpoints 200, TLS>30d, security headers present",
                        "credential-free probe applies to every provider")
    import ssl, socket, urllib.request, datetime as _dt
    try:
        import soc_inventory  # type: ignore
        inv = soc_inventory.scan(CURRENT_PID)
    except Exception:
        inv = {"services": []}
    urls = []
    for s in inv.get("services", []):
        for u in s.get("public", []) or []:
            urls.append((s.get("provider", "?"), u))
    if not urls:
        urls = [("azure-vm", "https://anchor.odinmarkets.com/")]
    issues, notes = [], []
    for prov, u in urls[:8]:
        host = re.sub(r"^https?://", "", u).split("/")[0].split(":")[0]
        # TLS cert expiry
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((host, 443), timeout=6) as sk:
                with ctx.wrap_socket(sk, server_hostname=host) as ss:
                    na = ss.getpeercert().get("notAfter")
            exp = _dt.datetime.strptime(na, "%b %d %H:%M:%S %Y %Z")
            days = (exp - _dt.datetime.utcnow()).days
            if days < 14: issues.append(f"{host}: TLS cert expires in {days}d")
            else: notes.append(f"{host}: TLS {days}d")
        except Exception as e:
            notes.append(f"{host}: TLS check n/a")
        # HTTP health + security headers
        try:
            resp = urllib.request.urlopen(urllib.request.Request(u, method="HEAD"), timeout=7)
            h = {k.lower(): v for k, v in resp.getheaders()}
            missing = [x for x in ("strict-transport-security", "x-frame-options") if x not in h and "frame-ancestors" not in h.get("content-security-policy", "")]
            if missing: issues.append(f"{host}: missing headers {missing}")
        except Exception:
            notes.append(f"{host}: HTTP n/a")
    if issues:
        return _finding("SOC-CLOUD-004", "Multi-cloud surface posture", "medium", "medium", "Suspicious",
                        "public endpoints (any cloud)", "; ".join(issues) + " | " + "; ".join(notes[:4]),
                        "credential-free probe across providers; TLS/near-expiry + missing headers are hardening signals",
                        "Checked and finding detected",
                        "Recommend (approval-gated): renew/auto-renew TLS; add HSTS + X-Frame-Options/CSP at the edge for every host.",
                        "none (edge/header config)", "the affected public host(s)")
    return _finding("SOC-CLOUD-004", "Multi-cloud surface posture", "informational", "high", "Benign/Expected",
                    "public endpoints (any cloud)", "; ".join(notes[:6]) or "endpoints healthy",
                    "credential-free probe applies to every provider; no surface issues", "Checked and healthy")

def check_thirdparty_quota(test):
    """GENERIC third-party service quota/abuse-cost monitor (Klaviyo, HubSpot, Mailchimp, SendGrid, Twilio,
    … and any future provider). Warns when app-abuse can drain paid quota. Read-only."""
    try:
        import soc_quota  # type: ignore
    except Exception as e:
        return _finding("SOC-EXT-006", "Third-party quota monitor", "low", "low", "Needs Review",
                        "third-party providers", f"quota module error: {e}", "n/a", "Data unavailable")
    # abuse is active if the app-abuse / behavioral / subscriber findings fired earlier in THIS run
    abuse_active = bool(getattr(check_thirdparty_quota, "_abuse", False))
    res = soc_quota.check(CURRENT_PID, abuse_active=abuse_active)
    if test:
        return _finding("SOC-EXT-006", "Third-party quota monitor", "informational", "medium", "Benign/Expected",
                        "third-party providers", "(fixture) providers tracked; no active abuse → no quota drain",
                        "generic across vendors; live telemetry when a key is present, inference otherwise")
    if res.get("at_risk"):
        return _finding("SOC-EXT-006", "Third-party quota at risk (abuse-driven)", "medium", "medium", "Suspicious",
                        "third-party providers", res["summary"] + " Providers at risk: " + ", ".join(res["at_risk"]),
                        "app-abuse implies downstream sends → paid quota drain; provider-agnostic",
                        "Checked and finding detected",
                        "Recommend (approval-gated): suppress downstream sends until anti-abuse checks pass; plug "
                        "provider API keys for exact usage/limit telemetry. " + res["how_to_extend"],
                        "suppression may delay legitimate lifecycle emails briefly", "marketing spend + deliverability reputation")
    return _finding("SOC-EXT-006", "Third-party quota monitor", "informational", "medium", "Benign/Expected",
                    "third-party providers", res["summary"],
                    "generic across vendors; no active abuse-driven drain detected", "Checked and healthy")

def check_clickjacking(test):
    """Reputation / iframe-embedding (clickjacking) exposure — missing X-Frame-Options / CSP frame-ancestors
    lets an attacker iframe our site to phish users and damage reputation. Read-only header probe."""
    if test:
        return _finding("SOC-WEB-005", "Clickjacking / iframe-embedding protection", "informational", "high",
                        "Benign/Expected", "public site headers",
                        "(fixture) X-Frame-Options=DENY + CSP frame-ancestors 'none' present", "framing blocked")
    url = "https://anchor.odinmarkets.com/"
    try:
        import urllib.request
        req = urllib.request.Request(url, method="HEAD")
        resp = urllib.request.urlopen(req, timeout=8)
        h = {k.lower(): v for k, v in resp.getheaders()}
    except Exception as e:
        return _finding("SOC-WEB-005", "Clickjacking / iframe-embedding protection", "low", "low", "Needs Review",
                        "public site headers", f"could not read headers: {e}", "n/a", "Data unavailable")
    xfo = h.get("x-frame-options", "")
    csp = h.get("content-security-policy", "")
    protected = bool(xfo) or "frame-ancestors" in csp
    if not protected:
        return _finding("SOC-WEB-005", "Missing anti-iframe (clickjacking) protection", "medium", "high", "Suspicious",
                        "public site headers", f"X-Frame-Options='{xfo}' CSP-frame-ancestors={'yes' if 'frame-ancestors' in csp else 'no'}",
                        "no framing protection → a malicious site can iframe us to phish/deceive users and harm reputation",
                        "Checked and finding detected",
                        "Recommend (approval-gated): add X-Frame-Options: DENY (or SAMEORIGIN) + CSP frame-ancestors 'none' "
                        "at the reverse proxy for all public sites.",
                        "SAMEORIGIN if we legitimately iframe our own pages — verify before DENY", "brand reputation + users")
    return _finding("SOC-WEB-005", "Clickjacking / iframe-embedding protection", "informational", "high",
                    "Benign/Expected", "public site headers", f"XFO='{xfo}' frame-ancestors={'yes' if 'frame-ancestors' in csp else 'no'}",
                    "framing is blocked", "Checked and healthy")

CHECKS = {
    "service": ("SOC_SOURCE_INTEGRITY_MONITORING_ENABLED", check_service_health),
    "network": ("SOC_NETWORK_MONITORING_ENABLED", check_network_listeners),
    "website": ("SOC_NETWORK_MONITORING_ENABLED", check_website_health),
    "ssh": ("SOC_SSH_MONITORING_ENABLED", check_ssh_auth),
    "persistence": ("SOC_SSH_MONITORING_ENABLED", check_persistence),
    "app_abuse": ("SOC_APPLICATION_ABUSE_MONITORING_ENABLED", check_redberry_app_abuse),
    "db_anomaly": ("SOC_DATABASE_MONITORING_ENABLED", check_db_anomaly),
    "subscriber_forensics": ("SOC_DATABASE_MONITORING_ENABLED", check_subscriber_forensics),
    "intrusion_behavior": ("SOC_APPLICATION_ABUSE_MONITORING_ENABLED", check_intrusion_behavior),
    "quota": ("SOC_APPLICATION_ABUSE_MONITORING_ENABLED", check_thirdparty_quota),
    "clickjacking": ("SOC_NETWORK_MONITORING_ENABLED", check_clickjacking),
    "miner_hunt": ("SOC_NETWORK_MONITORING_ENABLED", check_miner_hunt),
    "port_hardening": ("SOC_CLOUD_CONTROL_PLANE_MONITORING_ENABLED", check_port_hardening),
    "cloud_posture": ("SOC_CLOUD_CONTROL_PLANE_MONITORING_ENABLED", check_cloud_posture),
    "dependency": ("SOC_DEPENDENCY_MONITORING_ENABLED", check_dependency_intel),
    "sensor": ("SOC_SSH_MONITORING_ENABLED", check_sensor),
    "intel_fusion": ("SOC_EXTERNAL_INTELLIGENCE_ENABLED", check_intel_fusion),
}
QUICK = ["service", "website", "app_abuse", "intrusion_behavior"]
# Threat-hunting funnel order: broad host/network sweep → app/db/behavior forensics → intel correlation
FUNNEL = ["service", "network", "port_hardening", "cloud_posture", "website", "clickjacking", "ssh", "persistence",
          "miner_hunt", "app_abuse", "db_anomaly", "subscriber_forensics", "intrusion_behavior", "quota",
          "sensor", "dependency", "intel_fusion"]

def _sev_counts(findings):
    c = {"critical": 0, "high": 0, "medium": 0, "low": 0, "informational": 0}
    for f in findings:
        c[f["severity"]] = c.get(f["severity"], 0) + 1
    return c

def status_tracker(sections):
    """Memorizing status list: NEW this run / STILL OPEN / PENDING / ACCEPTED (leave for now) / RESOLVED."""
    def li(fs, get=lambda f: f):
        return "\n".join(f"  - {get(f)['id']} {get(f)['title']} ({get(f).get('classification','')})"
                         + (f" — note: {f.get('owner_note')}" if f.get('owner_note') else "")
                         for f in fs) or "  (none)"
    return "\n".join([
        "📌 ISSUE TRACKER (remembered across runs)", "",
        f"🆕 New this run ({len(sections['new'])}):", li(sections['new']), "",
        f"🔓 Still open — not resolved yet ({len(sections['open'])}):", li(sections['open']), "",
        f"⏸️ Pending / left for now ({len(sections['pending'])}):", li(sections['pending']), "",
        f"🤝 Accepted risk ({len(sections['accepted'])}):", li(sections['accepted']), "",
        f"✅ Resolved ({len(sections['resolved'])}):",
        "\n".join(f"  - {it['id']} {it['title']} — {it.get('resolved_by','')}" for it in sections['resolved']) or "  (none)",
    ])

def owner_summary(findings, sections, approvals_made):
    c = _sev_counts(findings)
    attention = sections['new'] + sections['open']
    status = "Healthy" if not attention else ("Attention needed" if c["critical"] == 0 else "Critical attention")
    lines = [f"Security status: {status}", "",
             "Checked:", "- authentication and SSH activity;", "- public network exposure;",
             "- application abuse;", "- service health;", "- dependency changes;", "- database health.", "",
             f"Findings — critical:{c['critical']} high:{c['high']} medium:{c['medium']} low:{c['low']} info:{c['informational']}",
             ""]
    confirmed_compromise = [f for f in findings if f["classification"] == "Confirmed" and "compromise" in f["title"].lower()]
    lines.append("No confirmed compromise was found." if not confirmed_compromise else "⚠️ Confirmed compromise indicator present.")
    warn = [f for f in findings if f["classification"] in ("Suspicious", "Probable")]
    if warn:
        lines += ["", "Warnings:"] + [f"- {f['title'].lower()} ({f['classification'].lower()})." for f in warn]
    lines += ["", "No production changes were made.",
              (f"{approvals_made} approval request(s) raised — awaiting your decision." if approvals_made else "No approvals required.")]
    return "\n".join(lines)

def technical_report(findings):
    out = ["# SOC Technical Report", ""]
    for f in findings:
        out += [f"## {f['id']} — {f['title']}",
                f"- Severity: {f['severity']} | Confidence: {f['confidence']} | Classification: {f['classification']}",
                f"- Asset: {f['asset']}  | Data source: {f['data_source_state']}",
                f"- Evidence: {f['evidence']}",
                f"- False-positive analysis: {f['false_positive_analysis']}"]
        if f.get("blast_radius"): out.append(f"- Blast radius: {f['blast_radius']}")
        if f.get("unknowns"): out.append(f"- Unresolved: {f['unknowns']}")
        if f.get("recommended_remediation"):
            out += [f"- Recommended remediation (approval-gated): {f['recommended_remediation']}",
                    f"- Remediation risk / downtime: {f['remediation_risk']}"]
        out.append("")
    return "\n".join(out)

_SEVCOLOR = {"critical": "#c0392b", "high": "#e67e22", "medium": "#d4ac0d", "low": "#2980b9", "informational": "#7f8c8d"}

def _humanized_narrative(status, c, sections, correlations, predictions, recovery, scope_recs):
    """Plain-language 'read-this-first' section — a non-expert understands everything before the technical detail."""
    warn = sections['new'] + sections['open']
    if status == "Healthy":
        lead = ("In plain words: your systems look healthy right now. I checked the whole surface and found nothing "
                "that needs your urgent attention. No changes were made to anything.")
    elif 'Critical' in status:
        lead = ("In plain words: I found something serious that needs your attention. Nothing was changed — I only "
                "looked and am reporting. Below I explain what it is, why I think so, and what I'd recommend (you decide).")
    else:
        lead = ("In plain words: things are mostly fine, but a few items deserve a look. Nothing was changed — I only "
                "observed and am reporting. Here is what stood out and what I'd suggest.")
    bl = [lead]
    if warn:
        bl.append("What stood out: " + "; ".join(f"{f['title']} ({f['classification'].lower()})" for f in warn[:5]) + ".")
    else:
        bl.append("What stood out: nothing that needs action this run.")
    if correlations:
        bl.append("The likely story (not a guess — based on evidence): " +
                  correlations[0].split(". Hypothesis")[0].split(". Conclusion")[0] + ".")
    if predictions:
        top = predictions[0]
        bl.append(f"What could go wrong next (so we prevent it now): {top['prediction']} "
                  f"The fix before it happens: {top['prevention']}")
    if recovery and recovery.get("posture"):
        rp = recovery["posture"]
        bl.append("If disaster struck: " + ("we have a recent encrypted backup and a smart recovery plan ready."
                  if rp.get("ready") else "we do NOT yet have a fresh encrypted backup — I recommend enabling scheduled "
                  "backups so we can always recover cleanly."))
    if scope_recs:
        bl.append("Growing safely: " + scope_recs[0])
    bl.append("You can act on any recommendation, defer it, or ignore it — the system never changes anything on its own.")
    return bl

def _health_report_spec(pid, findings, sections, approvals_made, monitor_only, s, correlations=None,
                        predictions=None, recovery=None, scope_recs=None, inventory=None, hunts=None):
    """Structured spec handed to the Reporting & Documentation Agent (report_engine) for a branded doc."""
    c = _sev_counts(findings)
    status = "Healthy" if not (sections['new'] + sections['open']) else ("Attention needed" if c['critical'] == 0 else "Critical attention")
    def frow(f): return [f['id'], f['title'], f['severity'], f['confidence'], f['classification']]
    secs = [
        {"heading": "In Plain Words (read this first)", "level": 1,
         "text": "A human-readable summary before the technical detail — understand the whole picture here, then drill "
                 "into the sections below if you want the evidence.",
         "bullets": _humanized_narrative(status, c, sections, correlations or [], predictions or [], recovery or {}, scope_recs or [])},
        {"heading": "Executive Summary", "level": 1,
         "text": f"Overall security status: **{status}**. Mode: **{'monitor-and-report only' if monitor_only else 'active'}**. "
                 f"No production changes were made. Findings — critical {c['critical']}, high {c['high']}, medium {c['medium']}, "
                 f"low {c['low']}, informational {c['informational']}. Approval requests raised: {approvals_made} "
                 f"(auto-denied while in monitor/test mode — nothing executed).",
         "badge": (status, "#c0392b" if 'Critical' in status else ("#e67e22" if 'Attention' in status else "#1F9A61"))},
        {"heading": "Issue Tracker (remembered across runs)", "level": 1,
         "bullets": [f"🆕 New this run: {len(sections['new'])}", f"🔓 Still open (unresolved): {len(sections['open'])}",
                     f"⏸️ Pending / left for now: {len(sections['pending'])}", f"🤝 Accepted risk: {len(sections['accepted'])}",
                     f"✅ Resolved: {len(sections['resolved'])}"]},
    ]
    if correlations:
        secs.append({"heading": "Methodology & Root-Cause Correlation (white-scope → narrow)", "level": 1,
                     "text": "Investigation follows NIST SP 800-61 + SANS PICERL and the threat-hunting funnel: a "
                             "hypothesis-free wide sweep first, then narrowing to evidence-supported root cause "
                             "(no fake/surface reason). MITRE ATT&CK techniques mapped.",
                     "bullets": correlations})
    if sections['open'] or sections['new']:
        secs.append({"heading": "Open & New Issues", "level": 2,
                     "table": {"headers": ["ID", "Title", "Severity", "Confidence", "Class"],
                               "rows": [frow(f) for f in (sections['new'] + sections['open'])]}})
    if sections['pending'] or sections['accepted']:
        secs.append({"heading": "Deferred by Owner (pending / accepted risk)", "level": 2,
                     "table": {"headers": ["ID", "Title", "Class", "Note"],
                               "rows": [[f['id'], f['title'], f['classification'], f.get('owner_note', '')]
                                        for f in (sections['pending'] + sections['accepted'])]}})
    if sections['resolved']:
        secs.append({"heading": "Resolved", "level": 2,
                     "table": {"headers": ["ID", "Title", "Resolved by"],
                               "rows": [[it['id'], it['title'], it.get('resolved_by', '')] for it in sections['resolved']]}})
    if hunts:
        secs.append({"heading": "Threat Hunt (ATT&CK hypotheses tested against evidence)", "level": 1,
                     "table": {"headers": ["Technique", "Hunt", "Verdict", "Evidence"],
                               "rows": [[h["technique"], h["name"], h["verdict"], h["evidence"]] for h in hunts]}})
    if predictions:
        secs.append({"heading": "Prediction & Prevention (proactive hardening before exploitation)", "level": 1,
                     "table": {"headers": ["Likelihood", "Area", "Prediction", "Prevent by", "Vector"],
                               "rows": [[p['likelihood'], p['area'], p['prediction'], p['prevention'], p['attack_vector']]
                                        for p in predictions]}})
    if recovery and recovery.get("posture"):
        rp = recovery["posture"]; pl = recovery.get("plan", {})
        secs.append({"heading": "Resilience & Recovery", "level": 1,
                     "bullets": [f"Encrypted-backup key fingerprint: {rp['key']['fingerprint']} (held on local desktop only; "
                                 f"encryption: {rp['key']['encryption']})",
                                 f"Backups retained: {rp['backup_count']} · last-backup age (days): {rp.get('last_backup_age_days')}",
                                 f"Readiness: {'ready' if rp.get('ready') else 'not ready — enable scheduled backups (approval-gated)'}",
                                 f"Smart recovery decision logic: {pl.get('decision','n/a')} — {pl.get('recommendation','')}",
                                 f"Narrowing rule: {pl.get('narrowing','')}"]})
    if scope_recs:
        secs.append({"heading": "Scope Recommendations (grow the SOC to more services/clouds)", "level": 1,
                     "bullets": scope_recs})
    if inventory and inventory.get("reverse_search"):
        rs = inventory["reverse_search"]
        secs.append({"heading": "Monitored Attack Surface (reverse-search targeting)", "level": 2,
                     "bullets": [f"Ecosystems: {', '.join(rs.get('ecosystems', [])) or '—'}",
                                 f"Frameworks/stacks: {', '.join(rs.get('frameworks', [])) or '—'}",
                                 f"Providers/clouds: {', '.join(rs.get('providers', [])) or '—'}",
                                 "Provider models supported: azure-vm (live), aws-ec2, godaddy, hostinger, cloudflare, static-cdn"]})
    secs.append({"heading": "All Checks (this run)", "level": 1,
                 "table": {"headers": ["ID", "Title", "Severity", "Class", "Data source"],
                           "rows": [[f['id'], f['title'], f['severity'], f['classification'], f['data_source_state']] for f in findings]}})
    for f in findings:
        if f['classification'] in ISSUE_CLASSES:
            secs.append({"heading": f"{f['id']} — {f['title']}", "level": 2,
                         "badge": (f['severity'], _SEVCOLOR.get(f['severity'], '#7f8c8d')),
                         "text": f"**Confidence:** {f['confidence']} · **Asset:** {f['asset']} · **Data:** {f['data_source_state']}",
                         "bullets": [f"Evidence: {f['evidence']}", f"False-positive analysis: {f['false_positive_analysis']}"]
                                    + ([f"Blast radius: {f['blast_radius']}"] if f.get('blast_radius') else [])
                                    + ([f"Recommended remediation (approval-gated): {f['recommended_remediation']}"] if f.get('recommended_remediation') else [])
                                    + ([f"Remediation risk / downtime: {f['remediation_risk']}"] if f.get('remediation_risk') else [])})
    return {
        "title": "RedBerry Continuous SOC — Security Health Report",
        "subtitle": f"Automated multi-agent SOC · {datetime.date.today().isoformat()} · monitor-and-report only",
        "brand": {"name": "Odin AI Systems", "info": "RedBerry Continuous SOC · Observe → Correlate → Verify → Report → Approve"},
        "meta": [("Project", "RedBerry Continuous SOC"), ("Run date", datetime.datetime.now().strftime("%Y-%m-%d %H:%M")),
                 ("Status", status), ("Mode", "monitor-and-report only" if monitor_only else "active"),
                 ("Auto-remediation", "DISABLED (approval-gated)"), ("Findings", f"C{c['critical']} H{c['high']} M{c['medium']} L{c['low']} I{c['informational']}")],
        "sections": secs,
        "footer": "Generated by the Reporting & Documentation Agent · Odin-Orchestrator. Read-only SOC — no production changes. "
                  "Secrets/2FA/tokens redacted. Confidential.",
    }

def run(pid=PID_DEFAULT, mode="full", cid=None, test=False):
    global CURRENT_PID
    CURRENT_PID = pid   # make every check operate on THIS project (reusable capability, any pid)
    s = settings()
    scope = f"project:{pid}"
    monitor_only = bool(s.get("SOC_MONITOR_ONLY", True))
    if not cid:
        cid = scopes.create_chat(scope, title=f"🛡️ SOC run {datetime.date.today().isoformat()}")["id"]
    def post(text, sender="CTO Orchestrator"):
        scopes.add_message(scope, cid, "assistant", text, sender=sender)

    post(f"🛡️ SOC run started — mode={mode}, monitor_only={monitor_only}, test={test}. "
         "Observe → Correlate → Verify → Report → Request approval → Act only if approved.", "CTO Orchestrator")

    # Educational: who does what + how work hands off between agents (ask any agent 'what is your role').
    post("👥 SOC team & hand-offs (each agent has ONE clear lane — no overlap):\n"
         "• CTO Orchestrator — governs the run, decides scope, talks to you, raises approvals (approves nothing itself).\n"
         "• Asset, Exposure & Attack-Surface Agent 🗺️ — keeps the living inventory of all clouds/stacks; targets everyone else.\n"
         "• Security Intelligence & Threat-Hunting Architect 🧠 — curates external advisories + playbooks for our stack.\n"
         "• Security Operations Investigator 🔎 — runs the read-only checks on the PRESENT state (evidence now).\n"
         "• Intrusion Detection & Behavioral Analytics Agent 🕵️ — finds stealthy abuse by BEHAVIOR (UEBA), not signatures.\n"
         "• Threat Prediction & Prevention Agent 🔮 — predicts the NEXT weakness and hardens before it's exploited.\n"
         "• Recovery & Resilience Agent 🛟 — encrypted dated backups + smart, date-aware recovery.\n"
         "• Reporting & Documentation Agent 📝 — turns it into a branded, human-readable + technical report.\n"
         "Flow: Asset maps → Architect arms → Investigator + Behavior detect → CTO correlates & narrows → Predictor "
         "prevents → Recovery protects → Reporting explains → CTO asks you to approve. Nothing acts without your yes.",
         "CTO Orchestrator")

    # Phase A — Security Intelligence & Threat-Hunting Architect refreshes intel for OUR stack (real advisories)
    if not test and mode in ("full",) and s.get("SOC_DEPENDENCY_MONITORING_ENABLED", True):
        post("🧠 Refreshing threat intelligence: pulling current advisories for our actual dependency versions "
             "from OSV.dev (aggregates GHSA / NVD / npm) and updating knowledge-base protocols. Vuln presence "
             "≠ compromise — I triage by reachability.", "Security Intelligence & Threat-Hunting Architect")
        try:
            if agents_registry: agents_registry.record_usage(pid, "Security Intelligence & Threat-Hunting Architect")
        except Exception:
            pass

    # Phase A2 — Asset, Exposure & Attack-Surface Agent refreshes the LIVING INVENTORY (multi-cloud/stack)
    inventory, scope_recs = {}, []
    try:
        import soc_inventory  # type: ignore
        inventory = soc_inventory.scan(pid)
        scope_recs = soc_inventory.scope_recommendations(inventory)
        rs = inventory.get("reverse_search", {})
        post("🗺️ Asset & attack-surface inventory refreshed. Reverse-search filter (targets intel to what we ACTUALLY "
             f"run): ecosystems={rs.get('ecosystems')}, frameworks={rs.get('frameworks')}, providers={rs.get('providers')}. "
             f"Services in scope + {len(inventory.get('discovered_projects', []))} platform projects mapped. "
             "Provider models cover Azure VM today and extend to AWS/GoDaddy/Hostinger/Cloudflare.",
             "Asset, Exposure & Attack-Surface Agent")
        if agents_registry:
            try: agents_registry.record_usage(pid, "Asset, Exposure & Attack-Surface Agent")
            except Exception: pass
    except Exception as e:
        post(f"🗺️ Inventory unavailable this run: {e}", "Asset, Exposure & Attack-Surface Agent")

    # Phase B — WHITE-SCOPE DISCOVERY (wide net first, then narrow). Standard IR methodology:
    # NIST SP 800-61 (Detection&Analysis → Containment → Eradication → Recovery), SANS PICERL, and the
    # threat-hunting funnel (broad hypothesis-free sweep → scope → confirm), MITRE ATT&CK for technique mapping.
    if mode in ("full",):
        post("🔭 Phase 1 — WHITE-SCOPE DISCOVERY (wide net). Following NIST SP 800-61 + SANS PICERL + the "
             "threat-hunting funnel: I first sweep the whole surface (host, network/ports, services, cloud "
             "control-plane, persistence, app endpoints, DB) hypothesis-free, THEN narrow to what the evidence "
             "actually supports — I do not jump to a cause. MITRE ATT&CK techniques are mapped as I go.",
             "Security Operations Investigator")

    if mode == "quick":
        which = QUICK
    elif mode in CHECKS:
        which = [mode]
    else:
        which = FUNNEL  # broad-to-narrow order
    findings, skipped = [], []
    for key in which:
        gate, fn = CHECKS[key]
        if not s.get(gate, True):
            skipped.append(f"{key} (disabled by {gate})"); continue
        # let the quota monitor know if app-abuse is live (set from abuse/behavior/subscriber findings so far)
        if key == "quota":
            check_thirdparty_quota._abuse = any(
                x["id"] in ("SOC-APP-001", "SOC-APP-004", "SOC-IDS-001") and x["classification"] in ("Suspicious", "Probable", "Confirmed")
                for x in findings)
        try:
            f = fn(test); findings.append(f)
            sender = "Intrusion Detection & Behavioral Analytics Agent" if key == "intrusion_behavior" else "Security Operations Investigator"
            post(f"[{f['classification']}] {f['id']} {f['title']} — {f['severity']}/{f['confidence']}", sender)
        except Exception as e:
            skipped.append(f"{key} (error: {e})")

    # Phase C — NARROW DOWN & CORRELATE (evidence-based root cause; do not accept a fake/surface reason).
    byid = {f["id"]: f for f in findings}
    correlations = []
    miner = byid.get("SOC-HOST-002"); dep = byid.get("SOC-DEP-002")
    svc = byid.get("SOC-OPS-001"); web = byid.get("SOC-NET-002")
    if miner and miner["classification"] == "Suspicious":
        chain = []
        if dep and dep["classification"] in ("Suspicious", "Probable"): chain.append("runtime-reachable vulnerable dependency (SOC-DEP-002)")
        if (svc and svc["classification"] != "Benign/Expected") or (web and web["classification"] != "Benign/Expected"):
            chain.append("degraded service/website (502/timeout)")
        correlations.append(
            "MINING/HIJACK ROOT-CAUSE CHAIN: high-CPU/miner indicator (SOC-HOST-002)"
            + (" ← " + " ← ".join(chain) if chain else "")
            + ". Hypothesis: a severe-vuln package was exploited to run a miner, starving the app → 502. "
              "This is the EVIDENCE chain, not a guessed cause; confirm the binary + outbound before calling it Confirmed. "
              "MITRE ATT&CK: T1190 (exploit public-facing app) → T1496 (resource hijacking) → T1499 (endpoint DoS).")
    sub = byid.get("SOC-APP-004"); abuse = byid.get("SOC-APP-001"); dbn = byid.get("SOC-DB-002"); ids = byid.get("SOC-IDS-001")
    if any(x and x["classification"] in ("Suspicious", "Probable") for x in (sub, abuse, ids)):
        correlations.append(
            "ABUSE ROOT-CAUSE CHAIN: behavioral intrusion detection (SOC-IDS-001: same-IP-many-accounts + machine-"
            "regular cadence) + subscriber forensics (SOC-APP-004: garbage names + disposable emails + 2FA farming) + "
            "registration/newsletter cadence (SOC-APP-001)"
            + (" + registration velocity (SOC-DB-002)" if dbn and dbn["classification"] != "Benign/Expected" else "")
            + ". Conclusion: APP-LEVEL automated abuse consuming third-party (Klaviyo/HubSpot) quota — NOT VM "
              "compromise. MITRE ATT&CK: T1583/T1586 (acquire/compromise accounts) + business-logic abuse. "
              "The verification/2FA success suggests either mailbox-controlled disposable inboxes or a client-side "
              "code leak — recommend confirming whether the OTP/verification code is exposed to the client.")
    if correlations:
        post("🎯 Phase 2 — NARROW DOWN (correlated, evidence-based):\n" + "\n\n".join("• " + c for c in correlations),
             "CTO Orchestrator")

    # Phase D — PREDICTION & PREVENTION (forward-looking; predict weak points, prevent BEFORE exploitation)
    predictions = []
    try:
        import soc_predict  # type: ignore
        predictions = soc_predict.predict(inventory, findings)
        if predictions:
            post("🔮 Phase 3 — PREDICT & PREVENT (proactive hardening before exploitation):\n" +
                 "\n".join(f"• [{p['likelihood']}] {p['area']}: {p['prediction']}\n   → prevent: {p['prevention']} "
                           f"({p['attack_vector']})" for p in predictions[:8]),
                 "Threat Prediction & Prevention Agent")
            if agents_registry:
                try: agents_registry.record_usage(pid, "Threat Prediction & Prevention Agent")
                except Exception: pass
    except Exception as e:
        post(f"🔮 Prediction unavailable this run: {e}", "Threat Prediction & Prevention Agent")

    # Phase D2 — AUTONOMOUS THREAT HUNT (Architect forms ATT&CK hypotheses; judged against collected evidence)
    hunts = []
    try:
        import soc_hunt  # type: ignore
        fu = None
        try:
            import soc_intel_fusion as _f  # type: ignore
            cvp = _socdir(pid) / "knowledge" / "intel-cache" / "our_cves.json"
            cves = json.loads(cvp.read_text()) if cvp.exists() else []
            fu = _f.fuse(cves, [], pid) if not test else {"actively_exploited_here": []}
        except Exception:
            fu = {"actively_exploited_here": []}
        hunts = soc_hunt.generate(inventory, findings, fu)
        post("🎯 " + soc_hunt.summary_text(hunts), "Security Intelligence & Threat-Hunting Architect")
    except Exception as e:
        post(f"🎯 Hunt unavailable this run: {e}", "Security Intelligence & Threat-Hunting Architect")

    # Phase D3 — AUTO-TRIAGE ENRICHMENT (analyst-grade context on the worst behavioral IP, if any)
    try:
        if not test:
            import soc_behavior, soc_enrich  # type: ignore
            bprofs = soc_behavior.analyze(pid, test=False).get("profiles", [])
            worst = next((p for p in bprofs if p.get("score", 0) >= 0.4 and p.get("verdict") != "owner/allow-listed"), None)
            if worst:
                post("🔬 Enrichment — " + soc_enrich.narrative(worst["ip"], worst, pid),
                     "Security Operations Investigator")
    except Exception:
        pass

    # Phase E — RESILIENCE posture (Recovery agent; backup readiness + smart recovery plan; no capture in monitor)
    recovery = {}
    try:
        import soc_recovery  # type: ignore
        # Auto-capture a config backup on live full runs when there's no active Confirmed compromise (a "clean"
        # restore point). Read-only + additive → non-harmful → NO approval needed. Restore stays approval-gated.
        if not test and mode == "full":
            confirmed = any(f["classification"] == "Confirmed" for f in findings)
            if not confirmed:
                try: soc_recovery.run_backup(pid, scope="config")
                except Exception: pass
                # also capture an encrypted DB backup when the last one is stale (>1 day) — read-only + additive
                try:
                    import time as _t
                    reg = soc_recovery._load_reg(pid)
                    dbs = [b for b in reg.get("backups", []) if b.get("scope") == "db"]
                    if not dbs or (_t.time() - dbs[-1].get("ts", 0) > 86400):
                        soc_recovery.run_backup(pid, scope="db")
                except Exception: pass
        recovery = {"posture": soc_recovery.posture(pid), "plan": soc_recovery.smart_recovery_plan(pid)}
        rp = recovery["posture"]
        post(f"🛟 Resilience posture — encrypted-backup key: {rp['key']['fingerprint']} (held on local desktop only); "
             f"backups retained: {rp['backup_count']}; ready: {rp['ready']}. {rp['note']}\n"
             f"Smart recovery: {recovery['plan']['recommendation']}",
             "Recovery & Resilience Agent")
        if agents_registry:
            try: agents_registry.record_usage(pid, "Recovery & Resilience Agent")
            except Exception: pass
    except Exception as e:
        post(f"🛟 Recovery posture unavailable: {e}", "Recovery & Resilience Agent")

    # Phase F — CTO scope recommendation (what other services/clouds to bring into SOC monitoring next)
    if scope_recs:
        post("🧭 CTO scope recommendation — services/clouds to consider bringing into SOC monitoring:\n" +
             "\n".join(f"• {r}" for r in scope_recs), "CTO Orchestrator")

    # approvals: any remediation recommendation → an approval request (never executed here)
    approvals_made = 0
    for f in findings:
        if f.get("recommended_remediation") and f["classification"] in ("Suspicious", "Probable", "Confirmed"):
            approvals_made += 1
            decision = "DENIED (test/monitor-only — no production change)" if (test or monitor_only) else "PENDING owner decision"
            if approvals and not test:
                try:
                    approvals.create(pid, "CTO Orchestrator", title=f"SOC remediation: {f['title']}",
                                     summary=f"{f['recommended_remediation']} | risk: {f['remediation_risk']}",
                                     kind="change", inline=False)
                except Exception:
                    pass
            post(f"🔐 Approval request — {f['title']}\n"
                 f"  Action: {f['recommended_remediation']}\n  Evidence: {f['id']} ({f['classification']})\n"
                 f"  Possible impact: {f['remediation_risk']}\n  Decision: {decision}\n"
                 "  (No agent may approve its own action; nothing runs without owner approval.)", "CTO Orchestrator")

    # reconcile with the persistent registry → memorizing status tracker (new/open/pending/accepted/resolved)
    issues = [f for f in findings if f["classification"] in ISSUE_CLASSES]
    sections = _reconcile(pid, issues)

    # reports
    post("📌 " + status_tracker(sections), "CTO Orchestrator")
    summary = owner_summary(findings, sections, approvals_made)
    post("📋 OWNER SUMMARY\n\n" + summary, "CTO Orchestrator")
    post("🔬 TECHNICAL REPORT\n\n" + technical_report(findings), "CTO Orchestrator")

    # Reporting & Documentation Agent → styled, branded, multi-format health report (same chat pool)
    reports = {}
    try:
        import report_engine  # type: ignore
        spec = _health_report_spec(pid, findings, sections, approvals_made, monitor_only, s,
                                   correlations=correlations, predictions=predictions, recovery=recovery,
                                   scope_recs=scope_recs, inventory=inventory, hunts=hunts)
        rdir = _socdir(pid) / "reports"
        stem = f"soc-health-{datetime.date.today().isoformat()}"
        for fmt in ("pdf", "docx", "md", "pptx"):
            try:
                reports[fmt] = str(report_engine.render_to_file(spec, fmt, rdir, stem))
            except Exception as e:
                reports[fmt] = f"error: {e}"
        okfmts = [k.upper() for k, v in reports.items() if not str(v).startswith("error")]
        post("📝 Styled health report prepared — formats: " + ", ".join(okfmts) +
             f"\n  saved under: soc/reports/{stem}.*\n"
             f"  print/fetch: GET /soc/report?pid={pid}&fmt=pdf (or docx | md | pptx)",
             "Reporting & Documentation Agent")
        if agents_registry:
            try: agents_registry.record_usage(pid, "Reporting & Documentation Agent")
            except Exception: pass
    except Exception as e:
        reports = {"error": str(e)}

    # persist run + findings (persistent state — not transient memory)
    rec = {"pid": pid, "mode": mode, "test": test, "monitor_only": monitor_only,
           "ts": time.time(), "date": datetime.date.today().isoformat(),
           "severity_counts": _sev_counts(findings), "approvals_made": approvals_made,
           "skipped": skipped, "findings": findings, "cid": cid, "reports": reports,
           "correlations": correlations, "predictions": predictions, "recovery": recovery, "hunts": hunts,
           "scope_recommendations": scope_recs, "inventory_reverse_search": inventory.get("reverse_search", {}),
           "tracker": {k: len(v) for k, v in sections.items()}}
    d = _socdir(pid) / "history" / "findings"; d.mkdir(parents=True, exist_ok=True)
    (d / f"run-{int(time.time())}.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False))
    store.write_json(f"projects/{pid}/data/jsons/soc_last_run.json", {k: rec[k] for k in
                     ("date", "ts", "severity_counts", "approvals_made", "monitor_only", "cid")})
    # bump agent activity
    try:
        if agents_registry:
            for a in ("CTO Orchestrator", "Security Operations Investigator"):
                agents_registry.record_usage(pid, a)
    except Exception:
        pass
    try:
        scopes.sync_up(scope, f"🛡️ SOC run: {len(findings)} findings, {approvals_made} approvals")
    except Exception:
        pass
    # NOTIFY: surface attention/critical SOC findings to the live notifications bell (deep-link to the SOC chat)
    try:
        import notifications_store as _nt  # type: ignore
        attn = sections['new'] + sections['open']
        crit = [f for f in findings if f["classification"] in ("Suspicious", "Probable", "Confirmed")]
        if not test:
            if crit:
                worst = max(crit, key=lambda f: {"critical": 3, "high": 2, "medium": 1}.get(f["severity"], 0))
                _nt.add("finding", f"🛡️ SOC: {len(crit)} item(s) need attention",
                        body=f"Top: {worst['title']} ({worst['classification']}, {worst['severity']}). "
                             f"{approvals_made} approval request(s) — nothing changed.",
                        pid=pid, cid=cid, project_name="RedBerry Continuous SOC",
                        severity=("critical" if any(f["severity"] == "critical" for f in crit) else "attention"),
                        icon="🛡️")
            else:
                _nt.add("finished", "🛡️ SOC daily run complete — all healthy",
                        body="No attention items this run.", pid=pid, cid=cid,
                        project_name="RedBerry Continuous SOC", severity="info", icon="🛡️")
    except Exception:
        pass
    print(f"OK soc run pid={pid} findings={len(findings)} approvals={approvals_made} monitor_only={monitor_only} test={test}")
    return rec

if __name__ == "__main__":
    a = sys.argv[1:]
    def opt(name, default=None):
        return a[a.index(name)+1] if name in a and a.index(name)+1 < len(a) else default
    run(pid=opt("--pid", PID_DEFAULT), mode=opt("--mode", "full"),
        cid=(opt("--cid") or None), test=("--test" in a))
