#!/usr/bin/env python3
"""
Intrusion Detection & Behavioral Analytics (UEBA) — the Intrusion Detection & Behavioral Analytics Agent.

Catches stealthy, signature-EVADING attacks by BEHAVIOR, not signatures. Modern attacks (often AI-assisted)
deliberately stay under simple thresholds and leave as few known signatures as possible, so we score how
entities BEHAVE over time:

  • builds a visitor/entity behavior profile per source IP (request cadence, endpoints touched, accounts
    created, user-agent rotation, timing regularity/entropy);
  • flags SAME-IP-MANY-ACCOUNTS and machine-REGULAR low-and-slow cadence (e.g. an account every ~10 min from
    one IP — the RedBerry pattern) even when each individual action is below a naive rate limit;
  • SMARTLY separates the owner's legitimate (dynamic) IP from real bad actors using an allow-list + an
    interactive-vs-automated behavior signature, to minimize false positives;
  • recommends UFW / edge blocks for confirmed-bad IPs — ALWAYS approval-gated, never auto-applied.

Read-only. Persists rolling behavior profiles to the SOC knowledge base so detection improves across runs.
"""
from __future__ import annotations
import re, json, math, statistics, pathlib, datetime, time

def _profiles_path(pid="redberry-continuous-soc"):
    try:
        import soc_run  # type: ignore
        return soc_run._socdir(pid) / "knowledge" / "visitor-behavior-profiles.json"
    except Exception:
        import store  # type: ignore
        return store.WS / "projects" / pid / "data" / "soc" / "knowledge" / "visitor-behavior-profiles.json"

def _owner_allowlist(pid="redberry-continuous-soc") -> set:
    """The owner's own (possibly dynamic) IPs — never auto-flag these. Seeded from the current SSH source +
    an editable allow-list file; the SSH-source refresh protocol keeps this current for dynamic IPs."""
    ips = set()
    try:
        import soc_run  # type: ignore
        ok, out = soc_run._ssh_ro("echo $SSH_CLIENT | awk '{print $1}'", timeout=12)
        if ok and out.strip():
            ips.add(out.strip())
    except Exception:
        pass
    try:
        p = _profiles_path(pid).parent / "owner-ip-allowlist.txt"
        if p.exists():
            ips |= {l.strip() for l in p.read_text().splitlines() if l.strip() and not l.startswith("#")}
    except Exception:
        pass
    return ips

def _regularity(times: list) -> float:
    """0..1 — how machine-regular the gaps are (low variance vs mean = automation). Human traffic is bursty."""
    if len(times) < 3:
        return 0.0
    gaps = [b - a for a, b in zip(sorted(times), sorted(times)[1:]) if b > a]
    if len(gaps) < 2:
        return 0.0
    mean = statistics.mean(gaps)
    if mean <= 0:
        return 0.0
    cv = statistics.pstdev(gaps) / mean            # coefficient of variation
    return round(max(0.0, 1.0 - min(cv, 1.0)), 2)  # ~1.0 = perfectly regular (bot); ~0 = bursty (human)

def _score_ip(prof: dict, owner_ips: set) -> dict:
    """Behavioral anomaly score for one IP profile. Evidence-based, FP-aware."""
    ip = prof["ip"]
    if ip in owner_ips:
        return {**prof, "score": 0.0, "verdict": "owner/allow-listed", "reasons": ["owner dynamic IP — excluded"]}
    reasons, score = [], 0.0
    if prof.get("accounts", 0) >= 3:
        score += 0.4; reasons.append(f"{prof['accounts']} accounts from one IP (fan-out)")
    reg = prof.get("regularity", 0.0)
    if reg >= 0.7 and prof.get("hits", 0) >= 4:
        score += 0.35; reasons.append(f"machine-regular cadence (regularity={reg}) — low-and-slow automation")
    if prof.get("ua_variety", 1) >= 3 and prof.get("accounts", 0) >= 2:
        score += 0.15; reasons.append(f"{prof['ua_variety']} user-agents (rotation)")
    if prof.get("sensitive_hits", 0) >= 5:
        score += 0.1; reasons.append(f"{prof['sensitive_hits']} hits on guest/auth/subscribe endpoints")
    score = round(min(1.0, score), 2)
    verdict = ("bad — recommend block" if score >= 0.7 else
               "suspicious — watch" if score >= 0.4 else
               "elevated — profile" if score >= 0.2 else "normal")
    return {**prof, "score": score, "verdict": verdict, "reasons": reasons}

def analyze(pid="redberry-continuous-soc", test=False) -> dict:
    """Return {profiles:[...], bad_ips:[...], summary, ufw_recommendation}. Read-only."""
    owner_ips = set() if test else _owner_allowlist(pid)
    if test:
        # deterministic fixture proving behavioral detection incl. FP-safety for the owner IP
        raw = {
            "203.0.113.7": {"times": [1000 + i*600 for i in range(8)], "accounts": 8, "uas": {"UA-0","UA-1","UA-2"},
                            "sensitive": 8},                                   # bot: 8 accts, exact 10-min cadence
            "198.51.100.9": {"times": [5, 9, 210, 213, 900], "accounts": 1, "uas": {"UA-x"}, "sensitive": 1},  # human
            "OWNER": {"times": [1, 2, 3, 4], "accounts": 5, "uas": {"UA-o"}, "sensitive": 5},                    # owner-like
        }
        owner_ips = {"OWNER"}
    else:
        raw = _collect_live(pid)
    profiles = []
    for ip, d in raw.items():
        prof = {"ip": ip, "hits": len(d["times"]), "accounts": d.get("accounts", 0),
                "ua_variety": len(d.get("uas", set())), "sensitive_hits": d.get("sensitive", 0),
                "regularity": _regularity(d["times"]),
                "first_seen": min(d["times"]) if d["times"] else 0, "last_seen": max(d["times"]) if d["times"] else 0}
        profiles.append(_score_ip(prof, owner_ips))
    profiles.sort(key=lambda p: -p["score"])
    bad = [p for p in profiles if p["verdict"] == "bad — recommend block"]
    _persist(pid, profiles)
    ufw = None
    if bad:
        ips = " ".join(p["ip"] for p in bad)
        ufw = {"action": "approval-gated UFW/edge block", "ips": [p["ip"] for p in bad],
               "example_command": f"sudo ufw deny from <IP>  # for: {ips}  (owner runs / approves; never auto-applied)",
               "fp_guard": "owner dynamic IP is allow-listed and excluded; only block IPs with behavioral score ≥ 0.7"}
    return {"profiles": profiles, "bad_ips": [p["ip"] for p in bad], "owner_excluded": list(owner_ips),
            "ufw_recommendation": ufw,
            "summary": f"{len(profiles)} source IPs profiled; {len(bad)} behaviorally-bad (recommend block); "
                       f"owner/dynamic IPs excluded from flagging."}

def _collect_live(pid) -> dict:
    """Read-only nginx access-log mining → per-IP behavior (cadence, endpoints, accounts, UA variety)."""
    import soc_run  # type: ignore
    # NOTE: the nginx combined format is `IP - - [date] "METHOD path HTTP/x" ...` — the method is preceded by a
    # DOUBLE-QUOTE, not a space. Match on the quote so we actually catch `"GET`/`"POST` (earlier bug: leading space).
    cmd = ("echo '%PW%' | sudo -S sh -c \"grep -ahE '\\\"(POST|GET) /(email-subscribe|api/register|api/auth|login|"
           "signup|register|contact|newsletter)' /var/log/nginx/access.log* 2>/dev/null | tail -4000\"").replace("%PW%", soc_run._vm_pw())
    ok, out = soc_run._ssh_ro(cmd, timeout=30)
    raw = {}
    if not ok or not out.strip():
        return raw
    for line in out.splitlines():
        m = re.match(r'(\S+) .*\[([^\]]+)\].*"(POST|GET) (\S+).*?" \d+ \d+ "[^"]*" "([^"]*)"', line)
        if not m:
            ipm = re.match(r'(\S+)', line)
            if not ipm:
                continue
            ip = ipm.group(1); method = ""; ep = ""; ua = ""; t = time.time()
        else:
            ip, method, ep, ua = m.group(1), m.group(3), m.group(4), m.group(5)
            try:
                t = datetime.datetime.strptime(m.group(2).split()[0], "%d/%b/%Y:%H:%M:%S").timestamp()
            except Exception:
                t = time.time()
        d = raw.setdefault(ip, {"times": [], "accounts": 0, "uas": set(), "sensitive": 0})
        d["times"].append(t); d["uas"].add(ua or "-")
        # account CREATION = POST to register/signup/auth (a GET /login is just a page view, not a new account)
        if method == "POST" and re.search(r"/(api/register|signup|register|api/auth)", ep):
            d["accounts"] += 1
        if re.search(r"/(email-subscribe|api/register|api/auth|login|signup|register|contact|newsletter)", ep):
            d["sensitive"] += 1
    return raw

def _persist(pid, profiles):
    p = _profiles_path(pid)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"date": datetime.date.today().isoformat(), "profiles": profiles},
                                indent=2, ensure_ascii=False))
    except Exception:
        pass

if __name__ == "__main__":
    print(json.dumps(analyze(test=True), indent=2, ensure_ascii=False, default=str))
