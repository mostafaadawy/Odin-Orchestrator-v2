#!/usr/bin/env python3
"""F-10 test (no LLM): after an audit violation the audit PROPOSES a rule for the agent that caused it; the owner
approves; nothing changes automatically; approving ADDS the rule (no rule lost, reversible). python f10_test.py <root>"""
import sys, os, pathlib, json, subprocess
root = pathlib.Path(sys.argv[1]).resolve(); os.chdir(root); sys.path.insert(0, str(root / "server"))
import workspace_mw as mw, workspace_audit as au, approvals, api_v2
WS = root / "workspace"; fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:300]}]" if info and not c else ""))
    if not c: fails.append(n)
R = {(r.path, list(r.methods)[0]): r.endpoint for r in api_v2.build_router().routes if hasattr(r, "endpoint")}
A = "revealer-6978"
au.set_config(enabled=False)   # owner's audit switch OFF: detect + report only (F-37)
for _ in range(3): au.heal(force=True)
_ags = sorted(d.name for d in (WS / "agents").iterdir() if (d / "capability.md").is_file())
AG1, AG2 = _ags[0], _ags[1]
cap = WS / "agents" / AG1 / "capability.md"; cap2 = WS / "agents" / AG2 / "capability.md"
b1, b2 = cap.read_bytes(), cap2.read_bytes()
old_rules = [l for l in cap.read_text().splitlines() if l.strip() and l.strip() not in ("- (none yet)", "- (none)")]
def loose(name, agent):
    p = WS / "projects" / A / name; p.write_text("x = 1\n"); mw.sync_row(p)
    mw.set_creator(p, mw.make_creator(agent=agent, project=A, via="test"), only_if_null=False); return p
loose("loose_f10.py", AG1); loose("loose2_f10.py", AG2)
au.sentinel(notify=False)
props = [a for a in approvals.list_pending(None) if a.get("kind") == "rule_change"]
pa = [a for a in props if a.get("rule_agent") == AG1]
check("1: a violation by an agent creates a PENDING rule proposal for that agent", len(pa) == 1 and "canonical slots" in pa[0].get("rule_text", ""), props)
check("2: nothing changes automatically (capability.md byte-identical after the audit)", cap.read_bytes() == b1 and cap2.read_bytes() == b2)
au.sentinel(notify=False); au.heal(force=True)
props2 = [a for a in approvals.list_pending(None) if a.get("kind") == "rule_change" and a.get("rule_agent") == AG1]
check("3: running the audit again does not duplicate the proposal, and heal never edits rules", len(props2) == 1 and cap.read_bytes() == b1)
aid = pa[0]["id"] if pa else ""
res = R[("/approvals/{aid}/approve", "POST")](aid, {"channel": "desktop"}) if aid else {}
txt = cap.read_text()
check("4: on the owner's approval the rule is ADDED under Custom rules", "- RULE: Write only into your project's canonical slots" in txt
      and txt.index("## Custom rules") < txt.index("- RULE: Write only"), res)
check("5: no existing rule or line is lost", all(l in txt.splitlines() for l in old_rules), [l for l in old_rules if l not in txt.splitlines()])
st = approvals.get(aid) or {}
check("6: the approval is applied and records the owner", st.get("applied") and st.get("decided_by") == "owner", st)
bid = (res.get("rule") or {}).get("batch")
rv = subprocess.run([sys.executable, str(root / "server" / "rewrite_log.py"), "revert", str(bid)], capture_output=True, text=True, cwd=str(root))
check("7: one-command revert restores the file byte-identical", bid and cap.read_bytes() == b1, rv.stdout[-200:] + rv.stderr[-200:])
pe = [a for a in approvals.list_pending(None) if a.get("kind") == "rule_change" and a.get("rule_agent") == AG2]
if pe: R[("/approvals/{aid}/reject", "POST")](pe[0]["id"], {"channel": "desktop"})
check("8: rejecting a proposal changes nothing", bool(pe) and cap2.read_bytes() == b2)
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
