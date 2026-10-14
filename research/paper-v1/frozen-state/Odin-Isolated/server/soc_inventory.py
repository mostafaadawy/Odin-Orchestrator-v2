#!/usr/bin/env python3
"""
Asset, Exposure & Attack-Surface inventory — the Asset & Attack-Surface Agent's capability.

Builds and MAINTAINS a living inventory of everything the org runs, across clouds/providers and stacks,
so the SOC is NOT hard-wired to a single VM. It:
  1. enumerates every project/service the platform knows (projects.list_projects) + declared infra;
  2. fingerprints each stack (Node/Next.js, Laravel/PHP, Python, static/landing, DB) from local paths;
  3. models providers (Azure VM today; extensible to GoDaddy, Hostinger, AWS, generic-SSH) declaratively;
  4. produces a REVERSE-SEARCH filter list (the exact ecosystems/frameworks/providers WE use) so threat
     intelligence and prediction are targeted to what we actually run — not the whole internet.

Read-only. Never modifies anything. Persists the inventory to the SOC knowledge base (json + markdown).
"""
from __future__ import annotations
import json, pathlib, datetime, re

# --- provider model: how the SOC can monitor each kind of host/cloud (extensible; add a dict = new cloud) ---
PROVIDERS = {
    "azure-vm": {"label": "Microsoft Azure — Linux VM", "control_plane": "az CLI / NSG",
                 "monitors": ["ssh", "services", "ports/NSG", "ufw", "processes", "db", "nginx logs"],
                 "how": "read-only SSH + `az network nsg` (both already wired)"},
    "aws-ec2": {"label": "AWS EC2", "control_plane": "aws CLI / Security Groups",
                "monitors": ["ssh", "services", "security-groups", "processes", "db"],
                "how": "read-only SSH + `aws ec2 describe-security-groups` (adapter TODO — same check functions)"},
    "godaddy": {"label": "GoDaddy shared/VPS + DNS", "control_plane": "GoDaddy API",
                "monitors": ["dns records", "tls/cert expiry", "http health", "exposed panels"],
                "how": "GoDaddy Domains API (read) + public HTTP probes (no SSH on shared hosting)"},
    "hostinger": {"label": "Hostinger VPS/shared", "control_plane": "hPanel / SSH (VPS)",
                  "monitors": ["http health", "tls/cert expiry", "ssh (VPS)", "exposed panels"],
                  "how": "public HTTP probes + SSH where a VPS exposes it"},
    "cloudflare": {"label": "Cloudflare (edge/DNS/WAF)", "control_plane": "Cloudflare API",
                   "monitors": ["dns", "waf rules", "tls", "cache/exposure"],
                   "how": "Cloudflare API (read) — recommended edge in front of any origin"},
    "static-cdn": {"labels": "Static/CDN (Vercel/Netlify/Pages)", "control_plane": "provider API",
                   "monitors": ["http health", "tls", "headers", "secrets in bundle"],
                   "how": "public HTTP + header/CSP probes"},
}

# --- stack fingerprints: file marker -> (stack, ecosystem, typical exposure & top risk classes) ---
_FINGERPRINTS = [
    ("next.config.js", "Next.js (SSR/React)", "npm", "public web; SSR RCE/SSRF, header/CSP, auth, rate-limit"),
    ("next.config.mjs", "Next.js (SSR/React)", "npm", "public web; SSR RCE/SSRF, header/CSP, auth, rate-limit"),
    ("nest-cli.json", "NestJS (Node API)", "npm", "API; authz, input validation, dependency RCE"),
    ("composer.json", "Laravel/PHP", "packagist", "public web; mass-assignment, CSRF, file upload, dep RCE"),
    ("artisan", "Laravel/PHP", "packagist", "public web; mass-assignment, CSRF, file upload, dep RCE"),
    ("requirements.txt", "Python", "pypi", "API/service; deserialization, dep RCE, secrets"),
    ("pyproject.toml", "Python", "pypi", "API/service; deserialization, dep RCE, secrets"),
    ("go.mod", "Go", "go", "service; dep advisories, memory safety edge cases"),
    ("Gemfile", "Ruby/Rails", "rubygems", "public web; mass-assignment, dep RCE"),
    ("package.json", "Node.js", "npm", "service; dependency RCE, prototype pollution, secrets"),
    ("index.html", "Static/landing", "static", "landing; leaked keys in bundle, missing headers, form abuse"),
    ("schema.prisma", "Prisma/PostgreSQL", "db", "data store; injection, exposure, backup/DR"),
]

def _inv_paths(pid_default="redberry-continuous-soc"):
    import store  # type: ignore
    try:
        import soc_run  # type: ignore
        kb = soc_run._socdir(pid_default) / "knowledge"
    except Exception:
        kb = store.WS / "projects" / pid_default / "data" / "soc" / "knowledge"
    return kb

def _fingerprint_dir(path: pathlib.Path) -> list:
    stacks = []
    try:
        if not path or not path.exists():
            return stacks
        names = {p.name for p in path.iterdir()} if path.is_dir() else set()
        for marker, stack, eco, risk in _FINGERPRINTS:
            if marker in names:
                stacks.append({"stack": stack, "ecosystem": eco, "typical_risk": risk, "marker": marker})
    except Exception:
        pass
    # de-dup by stack
    seen, out = set(), []
    for s in stacks:
        if s["stack"] not in seen:
            seen.add(s["stack"]); out.append(s)
    return out

# Declared infrastructure the org runs (seed; the agent MERGES discovered projects on top). Extensible.
DECLARED_INFRA = [
    {"service": "organics + bendcore (Azure VM)", "provider": "azure-vm", "host": "52.180.154.225",
     "public": ["https://anchor.odinmarkets.com"], "stacks": ["Next.js (SSR/React)", "NestJS (Node API)", "Prisma/PostgreSQL"],
     "in_scope": True, "notes": "primary production VM — fully monitored today"},
    {"service": "Odin anchor + web (Azure VM)", "provider": "azure-vm", "host": "52.180.154.225",
     "public": ["https://anchor.odinmarkets.com/odin-anchor", "https://anchor.odinmarkets.com/odin-web"],
     "stacks": ["Node.js", "Static/landing"], "in_scope": True, "notes": "same VM, reverse-proxied"},
]

def _extra_hosts(pid_default) -> list:
    """Owner-added hosts on ANY cloud (AWS/GoDaddy/Hostinger/Cloudflare/…). Drop an entry in
    knowledge/extra-hosts.json and it is monitored immediately — HTTP/TLS/header probes credential-free, and
    SSH host checks when an ssh cred is supplied. This is what makes multi-cloud a LIVE capability, not a model.
      [{"service":"Landing (GoDaddy)","provider":"godaddy","public":["https://example.com"],
        "stacks":["Static/landing"], "ssh":{"host":"1.2.3.4","user":"root","cred_env":"MYVPS_PW"}}]"""
    try:
        p = _inv_paths(pid_default) / "extra-hosts.json"
        if p.exists():
            d = json.loads(p.read_text())
            return d.get("hosts", d if isinstance(d, list) else [])
    except Exception:
        pass
    return []


def scan(pid_default="redberry-continuous-soc", extra_paths=None) -> dict:
    """Enumerate projects + declared infra, fingerprint stacks, compute reverse-search list."""
    today = datetime.date.today().isoformat()
    services = [dict(x) for x in DECLARED_INFRA] + [dict(x) for x in _extra_hosts(pid_default)]
    discovered = []
    try:
        import projects  # type: ignore
        for pr in projects.list_projects():
            lp = pr.get("localPath")
            stacks = _fingerprint_dir(pathlib.Path(lp).expanduser()) if lp else []
            discovered.append({"service": pr.get("name") or pr.get("id"), "pid": pr.get("id"),
                               "provider": "local/project", "localPath": lp,
                               "stacks": [s["stack"] for s in stacks] or ["(unknown — no localPath markers)"],
                               "stack_detail": stacks, "in_scope": pr.get("id") == pid_default or None,
                               "notes": "platform project"})
    except Exception as e:
        discovered.append({"service": "(project enumeration failed)", "error": str(e)})
    for p in (extra_paths or []):
        st = _fingerprint_dir(pathlib.Path(p).expanduser())
        if st:
            services.append({"service": str(p), "provider": "path", "stacks": [s["stack"] for s in st],
                             "stack_detail": st, "in_scope": None, "notes": "scanned path"})

    # reverse-search filter list: the exact ecosystems/frameworks/providers WE run
    ecosystems, frameworks, providers_used = set(), set(), set()
    for grp in (services, discovered):
        for s in grp:
            providers_used.add(s.get("provider", ""))
            for st in s.get("stack_detail", []):
                ecosystems.add(st["ecosystem"]); frameworks.add(st["stack"])
            for name in s.get("stacks", []):
                frameworks.add(name)
    reverse_search = {"ecosystems": sorted(e for e in ecosystems if e and e != "static"),
                      "frameworks": sorted(f for f in frameworks if f and not f.startswith("(")),
                      "providers": sorted(p for p in providers_used if p)}

    inv = {"date": today, "services": services, "discovered_projects": discovered,
           "reverse_search": reverse_search, "provider_models": list(PROVIDERS.keys())}
    _write(inv, pid_default)
    return inv

def _write(inv, pid_default):
    kb = _inv_paths(pid_default)
    try:
        kb.mkdir(parents=True, exist_ok=True)
        (kb.parent / "soc_inventory.json").write_text(json.dumps(inv, indent=2, ensure_ascii=False))
    except Exception:
        pass
    rs = inv["reverse_search"]
    lines = [f"# Living Asset & Attack-Surface Inventory  ·  {inv['date']}", "",
             "Maintained by the Asset, Exposure & Attack-Surface Agent. The SOC monitors WHAT WE ACTUALLY RUN; "
             "threat intelligence + prediction are filtered to this list (reverse search) to save time and stay precise.",
             "", "## Reverse-search filter (targets intel to our real stack)",
             f"- Ecosystems: {', '.join(rs['ecosystems']) or '—'}",
             f"- Frameworks/stacks: {', '.join(rs['frameworks']) or '—'}",
             f"- Providers/clouds in use: {', '.join(rs['providers']) or '—'}", "",
             "## Services & exposure", "",
             "| Service | Provider | Public | Stacks | In SOC scope |", "|---|---|---|---|---|"]
    for s in inv["services"]:
        lines.append(f"| {s.get('service','')} | {s.get('provider','')} | {', '.join(s.get('public',[])) or '—'} "
                     f"| {', '.join(s.get('stacks',[]))} | {'yes' if s.get('in_scope') else '—'} |")
    lines += ["", "## Discovered platform projects (candidates for scope)", "",
              "| Project | Stacks | In scope |", "|---|---|---|"]
    for d in inv["discovered_projects"]:
        lines.append(f"| {d.get('service','')} | {', '.join(d.get('stacks',[]))} | {'yes' if d.get('in_scope') else 'candidate'} |")
    lines += ["", "## Supported provider models (extensible — one dict adds a cloud)", ""]
    for k, v in PROVIDERS.items():
        lines.append(f"- **{k}** — {v.get('label') or v.get('labels')}: monitors {', '.join(v.get('monitors',[]))}. {v.get('how','')}")
    lines += ["", f"_Updated by the Asset, Exposure & Attack-Surface Agent: {inv['date']}._"]
    try:
        (kb / "asset-inventory.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        pass

def scope_recommendations(inv: dict) -> list:
    """CTO input: which discovered services/clouds SHOULD be brought into SOC monitoring next."""
    recs = []
    for d in inv.get("discovered_projects", []):
        if d.get("in_scope"):
            continue
        stacks = d.get("stacks", [])
        if stacks and not stacks[0].startswith("(unknown"):
            recs.append(f"Bring '{d['service']}' into SOC scope — stack: {', '.join(stacks)}; "
                        "recommend enrolling it (health + dependency + surface checks apply directly).")
    # multi-cloud advisory
    used = set(inv.get("reverse_search", {}).get("providers", []))
    if "azure-vm" in used and "cloudflare" not in used:
        recs.append("Consider putting Cloudflare (WAF/edge) in front of the origin — adds rate-limiting/bot control "
                    "the SOC can then monitor; reduces app-abuse + DoS exposure at the edge.")
    return recs

if __name__ == "__main__":
    inv = scan()
    print(json.dumps({"reverse_search": inv["reverse_search"],
                      "services": len(inv["services"]), "discovered": len(inv["discovered_projects"]),
                      "recommendations": scope_recommendations(inv)}, indent=2, ensure_ascii=False))
