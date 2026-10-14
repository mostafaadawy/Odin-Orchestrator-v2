#!/usr/bin/env python3
"""G13 test (no LLM): a NEEDED new platform -> a proposal to ADD the skill to the reused builder agent;
nothing changes until approval; on approval the skill is added, nothing removed, logged and reversible."""
import sys, os, pathlib, json
root = pathlib.Path(sys.argv[1]).resolve(); os.chdir(root); sys.path.insert(0, str(root / "server"))
import projects, approvals, agents_registry, api_v2
import workspace_mw as mw
fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:300]}]" if info and not c else ""))
    if not c: fails.append(n)
R = {(r.path, list(r.methods)[0]): r.endpoint for r in api_v2.build_router().routes if hasattr(r, "endpoint")}
cap = root / "workspace/agents/fullstack/capability.md"
before = cap.read_text()
S1_READY = [  # the real S1 r4 intake readiness
  {"item": "Next.js + NestJS web app (our usual stack)", "status": "ready", "by": "team", "need": ""},
  {"item": "Supabase Auth + Storage (new platform — project, keys, buckets)", "status": "needs", "by": "connector",
   "need": "Connect Supabase: create a Supabase project and provide its URL + anon key"},
  {"item": "Deployment to Azure VM", "status": "ready", "by": "azure", "need": "Not needed this run"},
  {"item": "Cloud deploy / hosting", "status": "needs", "by": "azure", "need": "confirm the Azure VM"}]
team = [{"name": "Fullstack", "role": "Full-Stack Engineer"}, {"name": "Security", "role": "Security & Threat Hunting"}, {"name": "QA", "role": "QA & Testing"}]
try:
    p = projects.create_project("G13 Supabase", "customers + orders; Supabase auth/storage", members=team, identifier="g13-supa", readiness=S1_READY)
except TypeError:
    p = projects.create_project("G13 Supabase", "customers + orders; Supabase auth/storage", members=team, identifier="g13-supa")
pend = [a for a in approvals.list_pending(p["id"]) if a.get("kind") == "strengthen"]
check("1: one strengthen proposal for the NEEDED new platform", len(pend) == 1, pend)
a = pend[0] if pend else {}
check("2: ...for the builder agent Fullstack, skill 'Supabase Auth + Storage'", a.get("strengthen_agent") == "Fullstack" and a.get("strengthen_skill") == "Supabase Auth + Storage", a)
check("3: no proposal for ready items or an Azure/hosting need", len(pend) <= 1)
check("4: nothing changed before approval", cap.read_text() == before)
if a:
    res = R[("/approvals/{aid}/approve", "POST")](a["id"], {})
    after = cap.read_text()
    check("5: after approval the skill is in Fullstack's Skills", "- Supabase Auth + Storage" in after, res)
    lost = [l for l in before.splitlines() if l.strip() and l not in after.splitlines() and l.strip() not in ("- (none yet)", "- (none)")]
    check("6: nothing removed (every earlier line kept, title same)", not lost and after.splitlines()[0] == before.splitlines()[0], lost)
    ro = agents_registry.get_agent(p["id"], "Fullstack") or {}
    check("7: this project's roster lists the new skill", "Supabase Auth + Storage" in ro.get("skills", []), ro.get("skills"))
    check("8: approval marked applied", (approvals.get(a["id"]) or {}).get("applied") is True, approvals.get(a["id"]))
    bid = (res.get("strengthen") or {}).get("batch", "")
    log = [d for d in mw.change_log(bid) if d.get("batch") == bid] if bid else []
    check("9: the change is logged as one batch", bool(log) and log[0].get("file", "").endswith("fullstack/capability.md"), log[:1])
    rv = mw.revert_batch(bid, hold=False) if bid else {}
    check("10: one-command revert restores the file byte-identical", cap.read_text() == before, rv)
    mw._append_raw  # noqa
# a second project needing the same platform after the skill exists -> no duplicate proposal
if a:
    R[("/approvals/{aid}/approve", "POST")]  # (skill was reverted above; re-apply via a fresh project)
p2 = None
try:
    p2 = projects.create_project("G13 Plain", "no new platform", members=team[:1], identifier="g13-plain", readiness=[S1_READY[0]])
except TypeError:
    p2 = projects.create_project("G13 Plain", "no new platform", members=team[:1], identifier="g13-plain")
check("11: no proposal when nothing new is needed", not [x for x in approvals.list_pending(p2["id"]) if x.get("kind") == "strengthen"])
p3 = projects.create_project("G13 Old", "old client, no readiness", members=team[:1], identifier="g13-old")
check("12: old clients without readiness still work, no proposal", p3 and not [x for x in approvals.list_pending(p3["id"]) if x.get("kind") == "strengthen"])
# rejection changes nothing
try:
    p4 = projects.create_project("G13 Rej", "x", members=team[:1], identifier="g13-rej", readiness=[S1_READY[1]])
    b4 = cap.read_text(); pr = [x for x in approvals.list_pending(p4["id"]) if x.get("kind") == "strengthen"]
    if pr: R[("/approvals/{aid}/reject", "POST")](pr[0]["id"], {})
    check("13: a rejected proposal changes nothing", bool(pr) and cap.read_text() == b4, pr)
except TypeError:
    check("13: a rejected proposal changes nothing", False, "readiness not supported")
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
