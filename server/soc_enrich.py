#!/usr/bin/env python3
"""
Auto-triage & enrichment — replaces the tier-1 analyst who enriches and writes up an alert.

Given an IP (or a finding), it adds context from FREE sources (ASN / org / country / hosting-vs-residential)
and produces a short analyst-style narrative so alerts arrive decision-ready. Desktop-side; never touches the
production VM. Read-only; caches lookups; degrades gracefully offline.

F-21 (owner 2026-10-12): geo/ASN context comes from a LOCAL GeoLite2 database — visitor IPs are never sent to a
third party (the old ip-api.com lookup over plain HTTP is gone). Files (MaxMind GeoLite2, free; DB-IP Lite works
too, same .mmdb format): GeoLite2-City.mmdb and GeoLite2-ASN.mmdb in data/geoip/ (or ODIN_GEOIP_DIR). Without them
the enrichment says "geo database not installed" — it never falls back to a network lookup.
Reputation cross-check reuses soc_intel_fusion (abuse.ch).
"""
from __future__ import annotations
import json, os, re, time, pathlib

_TTL = 24 * 3600
_ROOT = pathlib.Path(__file__).resolve().parent.parent
_HOSTING = re.compile(r"amazon|aws|google|microsoft|azure|digitalocean|ovh|hetzner|linode|akamai|vultr|oracle|"
                      r"alibaba|tencent|contabo|leaseweb|choopa|m247|hosting|host|cloud|data ?cent(er|re)|server|"
                      r"colo|vps", re.I)
_READERS: dict = {}


def _geo_dir() -> pathlib.Path:
    return pathlib.Path(os.environ.get("ODIN_GEOIP_DIR") or (_ROOT / "data" / "geoip"))


def _reader(kind: str):
    """Open (once) the local .mmdb for kind 'City' or 'ASN'; None when it is not installed."""
    d = _geo_dir()
    key = (str(d), kind)
    if key in _READERS:
        return _READERS[key]
    r = None
    for name in (f"GeoLite2-{kind}.mmdb", f"dbip-{kind.lower()}-lite.mmdb"):
        f = d / name
        if f.is_file():
            try:
                import maxminddb  # type: ignore
                r = maxminddb.open_database(str(f))
            except Exception:
                r = None
            break
    _READERS[key] = r
    return r


def _local_lookup(ip: str) -> dict:
    city, asn = _reader("City"), _reader("ASN")
    if city is None and asn is None:
        return {"state": "geo database not installed (local GeoLite2; no network lookup)"}
    out = {"state": "ok"}
    try:
        c = (city.get(ip) if city else None) or {}
        out["country"] = ((c.get("country") or {}).get("names") or {}).get("en")
        subs = c.get("subdivisions") or []
        out["region"] = ((subs[0].get("names") or {}).get("en")) if subs else None
        out["city"] = ((c.get("city") or {}).get("names") or {}).get("en")
    except Exception:
        pass
    try:
        a = (asn.get(ip) if asn else None) or {}
        org = a.get("autonomous_system_organization")
        num = a.get("autonomous_system_number")
        out.update({"isp": org, "org": org, "asn": f"AS{num} {org}" if num else None,
                    "hosting": bool(org and _HOSTING.search(org)) if org else None,
                    "proxy": None, "mobile": None})   # not in GeoLite2 — left unknown, never guessed
    except Exception:
        pass
    return out


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
    out.update(_local_lookup(ip))   # F-21: local database only — the IP never leaves this Mac
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
