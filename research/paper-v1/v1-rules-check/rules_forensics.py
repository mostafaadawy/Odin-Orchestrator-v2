#!/usr/bin/env python3
"""READ-ONLY forensic check of v1 (Odin-Orchestrator): which agent rules were ever saved, and which are missing
from the agent's current shared capability.md. Reads files and git history (git --no-optional-locks) only;
writes nothing inside v1. Usage: rules_forensics.py <v1_root> <out_json>"""
import sys, os, json, re, subprocess, pathlib, glob
V1 = pathlib.Path(sys.argv[1]).resolve(); OUT = pathlib.Path(sys.argv[2])
def git(*a):
    return subprocess.run(["git", "--no-optional-locks", "-C", str(V1), *a], capture_output=True, text=True).stdout
def norm(s): return re.sub(r"\s+", " ", str(s or "")).strip().removeprefix("RULE:").strip()
def slug(n): return re.sub(r"[^a-z0-9]+", "-", str(n).lower()).strip("-") or "agent"
def cap_rules(txt):
    out, sec = [], None
    for l in (txt or "").splitlines():
        if l.startswith("## "): sec = l[3:].strip().lower(); continue
        s = l.strip()
        if s.startswith("- RULE:"): out.append(norm(s[2:]))
        elif sec == "custom rules" and s.startswith("- ") and s not in ("- (none yet)", "- (none)"): out.append(norm(s[2:]))
    return [r for r in out if r]
seen = {}   # slug -> {rule: [sources]}
def add(sl, rule, src):
    r = norm(rule)
    if r: seen.setdefault(sl, {}).setdefault(r, []).append(src)
current = {}
# 1) shared capability.md — current and every committed version
for p in sorted((V1 / "workspace/agents").glob("*/capability.md")):
    sl = p.parent.name; current[sl] = set(cap_rules(p.read_text(errors="replace")))
    for r in current[sl]: add(sl, r, "current capability.md")
    rel = str(p.relative_to(V1))
    for c in git("log", "--format=%h %cs", "--", rel).split("\n"):
        if not c.strip(): continue
        h, d = c.split()
        for r in cap_rules(git("show", f"{h}:{rel}")): add(sl, r, f"git {h} ({d}) capability.md")
# 2) project rosters — working tree and every committed version
def roster_rules(txt, src):
    try: doc = json.loads(txt)
    except Exception: return
    for a in (doc.get("agents", []) if isinstance(doc, dict) else doc or []):
        for r in a.get("rules", []) or []:
            add(slug(a.get("name", "")), r.get("rule") if isinstance(r, dict) else r, src)
for p in sorted((V1 / "workspace/projects").glob("*/agents.json")):
    roster_rules(p.read_text(errors="replace"), f"current roster {p.parent.name}")
for line in git("log", "--format=%h %cs", "--name-only", "--", "workspace/projects/*/agents.json").split("\n\n"):
    ls = [x for x in line.strip().split("\n") if x.strip()]
    if not ls: continue
    if " " in ls[0] and not ls[0].endswith(".json"):
        h, d = ls[0].split()[:2]; files = ls[1:]
    else:
        continue
    for f in files:
        roster_rules(git("show", f"{h}:{f}"), f"git {h} ({d}) roster {f.split('/')[2]}")
# 3) company definitions — agents/*/index.json and the old company_agents.json registry
for p in sorted((V1 / "workspace/agents").glob("*/index.json")):
    try: cfg = json.loads(p.read_text())
    except Exception: continue
    for r in cfg.get("rules", []) or []: add(p.parent.name, r.get("rule") if isinstance(r, dict) else r, "current index.json (company def)")
for c in git("log", "--format=%h %cs", "--", "workspace/shared/core-registry/company_agents.json").split("\n"):
    if not c.strip(): continue
    h, d = c.split()
    try: doc = json.loads(git("show", f"{h}:workspace/shared/core-registry/company_agents.json"))
    except Exception: continue
    for a in (doc.get("agents", doc) if isinstance(doc, dict) else doc) or []:
        if isinstance(a, dict):
            for r in a.get("rules", []) or []: add(slug(a.get("name", "")), r.get("rule") if isinstance(r, dict) else r, f"git {h} ({d}) company_agents.json")
# 4) lost = ever saved for the agent, but not in its current shared file
lost = []
for sl, rules in sorted(seen.items()):
    if sl not in current:   # agent has no shared folder (roster-only member): nothing shared to lose
        continue
    for r, srcs in rules.items():
        if r not in current[sl]:
            lost.append({"agent": sl, "rule": r, "sources": sorted(set(srcs))})
# 5) chats: where was each lost rule stated?
chat_files = [p for p in (V1 / "workspace").rglob("*") if p.is_file() and ("chat" in str(p).lower()) and p.suffix in (".json", ".jsonl", ".md")]
for L in lost:
    key = L["rule"][:60]
    hits = []
    for p in chat_files:
        try:
            if key in p.read_text(errors="replace"): hits.append(str(p.relative_to(V1)))
        except Exception: pass
    L["chats"] = hits[:5]
    L["recoverable"] = bool(L["sources"])
    L["still_in_a_current_roster"] = [s for s in L["sources"] if s.startswith("current roster")]
OUT.write_text(json.dumps({"agents_with_shared_file": len(current), "rules_ever_seen": sum(len(v) for v in seen.values()),
                           "lost": lost}, indent=1, ensure_ascii=False))
print(f"agents={len(current)} rules_ever_seen={sum(len(v) for v in seen.values())} lost={len(lost)}")
for L in lost:
    print(f"- {L['agent']}: {L['rule'][:110]} | sources={len(L['sources'])} first={L['sources'][0][:60]} | chats={len(L['chats'])}")
