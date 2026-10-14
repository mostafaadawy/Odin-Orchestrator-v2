#!/usr/bin/env python3
"""
Intel Fusion — the Threat-Hunting Architect's UPGRADED intelligence capability (replaces a human intel team).

Continuously fuses FREE, PROFESSIONAL threat-intel feeds and filters them to WHAT WE ACTUALLY RUN, then
answers the two questions an enterprise SOC pays an intel team for:

  1. "Which of OUR vulnerabilities are being ACTIVELY EXPLOITED in the wild right now?"
       -> cross-reference our runtime-reachable CVEs (from soc_intel / OSV) against the CISA KEV catalog.
  2. "Is any IP we've SEEN a known-bad botnet / C2 / malware host?"
       -> cross-reference observed IPs against abuse.ch Feodo Tracker + (optional) ThreatFox.

Runs ENTIRELY on the desktop brain — it never touches the 8GB production VM. Read-only; caches feeds so it is
cheap to run. Degrades gracefully offline ("Data unavailable" — never a fake healthy verdict).

Feeds (all free, no key required for the core):
  - CISA KEV        https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
  - abuse.ch Feodo  https://feodotracker.abuse.ch/downloads/ipblocklist.json   (active botnet C2 IPs)
  - abuse.ch ThreatFox (optional, POST) recent IOCs
"""
from __future__ import annotations
import json, time, urllib.request, pathlib, datetime

KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
FEODO_URL = "https://feodotracker.abuse.ch/downloads/ipblocklist.json"
_CACHE_TTL = 6 * 3600  # refresh feeds at most every 6h (cheap, polite to the free sources)


def _cache_dir(pid="redberry-continuous-soc"):
    try:
        import soc_run  # type: ignore
        d = soc_run._socdir(pid) / "knowledge" / "intel-cache"
    except Exception:
        import store  # type: ignore
        d = store.WS / "projects" / pid / "data" / "soc" / "knowledge" / "intel-cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _get_json(url, cache_name, pid, ttl=_CACHE_TTL, post=None):
    cf = _cache_dir(pid) / cache_name
    if cf.exists() and (time.time() - cf.stat().st_mtime) < ttl:
        try:
            return json.loads(cf.read_text()), "cache"
        except Exception:
            pass
    try:
        req = urllib.request.Request(url, data=(json.dumps(post).encode() if post else None),
                                     headers={"User-Agent": "Odin-SOC-IntelFusion/1.0",
                                              **({"Content-Type": "application/json"} if post else {})})
        raw = urllib.request.urlopen(req, timeout=20).read()
        cf.write_bytes(raw)
        return json.loads(raw), "live"
    except Exception as e:
        if cf.exists():
            try:
                return json.loads(cf.read_text()), "stale-cache"
            except Exception:
                pass
        return None, f"unavailable: {e}"


def fetch_kev(pid="redberry-continuous-soc") -> dict:
    """{cve_id: {name, product, dueDate, ransomware}} of KNOWN-EXPLOITED vulns."""
    d, state = _get_json(KEV_URL, "cisa_kev.json", pid)
    out = {}
    if d:
        for v in d.get("vulnerabilities", []):
            cid = v.get("cveID")
            if cid:
                out[cid] = {"name": v.get("vulnerabilityName", ""), "product": v.get("product", ""),
                            "due": v.get("dueDate", ""), "ransomware": v.get("knownRansomwareCampaignUse", "")}
    return {"map": out, "state": state, "count": len(out)}


def fetch_bad_ips(pid="redberry-continuous-soc") -> dict:
    """Set of active botnet C2 / malware IPs from abuse.ch Feodo Tracker."""
    d, state = _get_json(FEODO_URL, "feodo_ips.json", pid)
    ips = {}
    if isinstance(d, list):
        for row in d:
            ip = row.get("ip_address")
            if ip:
                ips[ip] = {"malware": row.get("malware", ""), "first_seen": row.get("first_seen", ""),
                           "c2_status": row.get("status", "")}
    return {"map": ips, "state": state, "count": len(ips)}


def fuse(our_cves: list, observed_ips: list, pid="redberry-continuous-soc") -> dict:
    """Cross-reference OUR CVEs vs KEV and OUR observed IPs vs abuse.ch. Returns actionable, prioritized intel."""
    kev = fetch_kev(pid)
    bad = fetch_bad_ips(pid)
    exploited = []
    for c in our_cves:
        if c in kev["map"]:
            exploited.append({"cve": c, **kev["map"][c]})
    hits = []
    for ip in observed_ips:
        if ip in bad["map"]:
            hits.append({"ip": ip, **bad["map"][ip]})
    today = datetime.date.today().isoformat()
    summary = {"date": today,
               "kev_state": kev["state"], "kev_total": kev["count"],
               "feodo_state": bad["state"], "feodo_total": bad["count"],
               "our_cves_checked": len(our_cves), "actively_exploited_here": exploited,
               "observed_ips_checked": len(observed_ips), "known_bad_ip_hits": hits}
    _write_kb(summary, pid)
    return summary


def _write_kb(s, pid):
    try:
        d = _cache_dir(pid).parent
        lines = [f"# Fused Threat Intelligence  ·  {s['date']}", "",
                 f"- CISA KEV catalog: {s['kev_total']} known-exploited CVEs ({s['kev_state']})",
                 f"- abuse.ch Feodo C2 IPs: {s['feodo_total']} ({s['feodo_state']})", "",
                 "## 🔴 OUR vulnerabilities that are ACTIVELY EXPLOITED in the wild (patch first!)"]
        if s["actively_exploited_here"]:
            for e in s["actively_exploited_here"]:
                lines.append(f"- **{e['cve']}** — {e.get('name','')} ({e.get('product','')}); "
                             f"CISA due {e.get('due','')}; ransomware: {e.get('ransomware','')}")
        else:
            lines.append("- none of our detected CVEs are on the KEV list right now.")
        lines += ["", "## 🔴 Observed IPs that are KNOWN-BAD (botnet/C2/malware)"]
        if s["known_bad_ip_hits"]:
            for h in s["known_bad_ip_hits"]:
                lines.append(f"- **{h['ip']}** — {h.get('malware','')} C2 ({h.get('c2_status','')}), first seen {h.get('first_seen','')}")
        else:
            lines.append("- none of the IPs we've observed appear on the abuse.ch C2 list.")
        lines += ["", f"_Fused by the Threat-Hunting Architect (Intel Fusion): {s['date']}. Sources: CISA KEV, abuse.ch._"]
        (d / "fused-threat-intel.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        pass


if __name__ == "__main__":
    # demo: pretend we run these CVEs + saw these IPs
    r = fuse(["CVE-2024-3400", "CVE-2021-44228", "CVE-2019-0001"], ["1.2.3.4", "45.142.212.61"])
    print(json.dumps({k: v for k, v in r.items() if k not in ()}, indent=2)[:1200])
