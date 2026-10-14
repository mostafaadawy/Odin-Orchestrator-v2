#!/usr/bin/env python3
"""
Auto-triage & enrichment — replaces the tier-1 analyst who enriches and writes up an alert.

Given an IP (or a finding), it adds context from FREE sources (ASN / org / country / hosting-vs-residential)
and produces a short analyst-style narrative so alerts arrive decision-ready. Desktop-side; never touches the
production VM. Read-only; caches lookups; degrades gracefully offline.

Free source: ip-api.com (no key, generous free tier). Reputation cross-check reuses soc_intel_fusion (abuse.ch).
"""
from __future__ import annotations
import json, time, urllib.request, pathlib

_TTL = 24 * 3600


def _cache(pid="redberry-continuous-soc"):
    try:
        import soc_run  # type: ignore
        d = soc_run._socdir(pid) / "knowledge" / "enrich-cache"
    except Exception:
        import store  # type: ignore
        d = store.WS / "projects" / pid / "data" / "soc" / "knowledge" / "enrich-cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def enrich_ip(ip: str, pid="redberry-continuous-soc") -> dict:
    if not ip or ip.count(".") != 3:
        return {"ip": ip, "state": "skip (not an IPv4)"}
    cf = _cache(pid) / f"{ip.replace(':', '_')}.json"
    if cf.exists() and (time.time() - cf.stat().st_mtime) < _TTL:
        try:
            return json.loads(cf.read_text())
        except Exception:
            pass
    out = {"ip": ip}
    try:
        url = f"http://ip-api.com/json/{ip}?fields=status,country,regionName,city,isp,org,as,hosting,proxy,mobile"
        d = json.loads(urllib.request.urlopen(url, timeout=8).read())
        if d.get("status") == "success":
            out.update({"country": d.get("country"), "region": d.get("regionName"), "city": d.get("city"),
                        "isp": d.get("isp"), "org": d.get("org"), "asn": d.get("as"),
                        "hosting": d.get("hosting"), "proxy": d.get("proxy"), "mobile": d.get("mobile"),
                        "state": "ok"})
        else:
            out["state"] = "lookup-failed"
    except Exception as e:
        out["state"] = f"unavailable: {e}"
    # reputation cross-check (abuse.ch C2 list via fusion cache)
    try:
        import soc_intel_fusion as fusion  # type: ignore
        bad = fusion.fetch_bad_ips(pid)
        out["known_c2"] = ip in bad.get("map", {})
    except Exception:
        out["known_c2"] = None
    try:
        cf.write_text(json.dumps(out))
    except Exception:
        pass
    return out


def narrative(ip: str, prof: dict | None = None, pid="redberry-continuous-soc") -> str:
    """A short analyst-style write-up for an IP, combining behavior profile + enrichment."""
    e = enrich_ip(ip, pid)
    bits = [f"IP {ip}"]
    if e.get("state") == "ok":
        loc = ", ".join(x for x in [e.get("city"), e.get("country")] if x)
        bits.append(f"is hosted by {e.get('isp') or e.get('org') or 'unknown'} ({e.get('asn','')}){' in ' + loc if loc else ''}")
        tags = []
        if e.get("hosting"): tags.append("datacenter/hosting (not a home user)")
        if e.get("proxy"): tags.append("proxy/VPN")
        if e.get("mobile"): tags.append("mobile carrier")
        if tags: bits.append("— flagged as " + ", ".join(tags))
    if e.get("known_c2"):
        bits.append("⚠️ and appears on the abuse.ch botnet-C2 list (known-bad)")
    if prof:
        bits.append(f"— behavior: {prof.get('hits',0)} hits, {prof.get('accounts',0)} accounts, "
                    f"regularity {prof.get('regularity',0)}, score {prof.get('score',0)} ({prof.get('verdict','')})")
    concl = "Datacenter-hosted + machine-regular behavior is consistent with automation, not a normal visitor." \
        if (e.get("hosting") and prof and prof.get("regularity", 0) >= 0.7) else \
        "Context added; correlate with behavior before any action."
    return " ".join(bits) + ". " + concl


if __name__ == "__main__":
    print(enrich_ip("8.8.8.8"))
    print(narrative("45.142.212.61", {"hits": 8, "accounts": 8, "regularity": 0.95, "score": 0.85, "verdict": "bad"}))
