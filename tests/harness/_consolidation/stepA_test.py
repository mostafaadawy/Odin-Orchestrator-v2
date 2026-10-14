#!/usr/bin/env python3
"""Step A test (no LLM): F-25, F-27, F-28, F-29, F-30, F-31. python stepA_test.py <root>"""
import sys, os, pathlib, threading, time, json, subprocess
root = pathlib.Path(sys.argv[1]).resolve(); os.chdir(root)
sys.path.insert(0, str(root / "server")); sys.path.insert(0, str(root / "orchestrator"))
import api_v2, projects
fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:300]}]" if info and not c else ""))
    if not c: fails.append(n)
H = lambda name: hasattr(api_v2, name)
# ---------- F-29: status shortcut only for a plain run-status question
st = getattr(api_v2, "_is_run_status_question", None)
COMPLAINT = "i did not asked to ask about y shipping status i will not buy or sell that is voilation"   # the real v1 message
check("F29-1: the real v1 complaint does NOT get the deploy-status answer", st is not None and not st(COMPLAINT))
check("F29-2: 'shipping status?' / 'order status' do NOT", st is not None and not st("shipping status?") and not st("what is the order status"))
check("F29-3: plain run questions still do: 'status?', 'what's the status', 'did it deploy?', '?'",
      st is not None and all(st(x) for x in ("status?", "what's the status", "did it deploy?", "?")))
# ---------- F-28: never re-add excluded or not-requested parts
fm = getattr(api_v2, "_filter_missing", None)
if fm:
    keep, skipped = fm("Add a contact form to the landing page. Do not deploy.",
                       ["Deploy the backend to the VM", "Add a contact form with validation", "Set up Supabase storage buckets"], {"deploy"})
else:
    keep, skipped = [], []
check("F28-1: an excluded action ('deploy') is not re-added", fm is not None and not any("Deploy" in k for k in keep), keep)
check("F28-2: a part not in the request (from the brief) is not re-added", fm is not None and not any("Supabase" in k for k in keep), keep)
check("F28-3: a real omission from the request IS re-added", fm is not None and keep == ["Add a contact form with validation"], keep)
check("F28-4: what was skipped is reported with the reason", fm is not None and len(skipped) == 2 and all("(" in s for s in skipped), skipped)
src = (root / "server/api_v2.py").read_text()
check("F28-5: the coverage gate applies the filter", "_filter_missing(_req_src, _missing, _forbid)" in src)
# ---------- F-30: the same message in the same chat is not started twice
SEEN = []
def _slow_engine(prompt, *a, **k):
    SEEN.append(prompt); time.sleep(3); return iter([{"kind": "final", "text": "done"}])
api_v2._engine_stream = _slow_engine
p = projects.create_project("StepA Chat", "x", identifier="stepa-chat")
def chat(scope, text, out):
    for ev in api_v2._scoped_gen(scope, text, "en", "C1", from_owner=True):
        out.append(str(ev))
o1, o2 = [], []
msg = "Please refactor the header component and add a dark mode toggle"
t1 = threading.Thread(target=chat, args=(f"project:{p['id']}", msg, o1)); t1.start(); time.sleep(1)
t2 = threading.Thread(target=chat, args=(f"project:{p['id']}", msg, o2)); t2.start(); t2.join(30); t1.join(30)
check("F30-1: the second identical message is answered 'already working' and starts nothing",
      H("_inflight_claim") and "already working on this exact message" in " ".join(o2) and len(SEEN) == 1, (len(SEEN), " ".join(o2)[:200]))
o3 = []; chat(f"project:{p['id']}", msg, o3)
check("F30-2: once the first finished, the same message can run again", len(SEEN) == 2, len(SEEN))
# ---------- F-27: a scheduled / ▶ Run project-level run is a TEAM run
cap = {}
api_v2._bg_orchestrate = lambda pid, goal: cap.update(dict(api_v2._RUNS.get(pid, {})))
api_v2.orchestrate_blocking(p["id"], "Run this project's recurring/daily task now")
check("F27-1: a scheduled project run is flagged as a TEAM run", cap.get("force_team") is True, cap)
api_v2._RUNS.pop(p["id"], None); cap.clear()
api_v2.start_run(p["id"], "fix the header"); time.sleep(0.5)
check("F27-2: an owner's normal run is NOT forced (the CTO may still handle a scoped ask directly)", not cap.get("force_team"), cap)
check("F27-3: the orchestration turns a 'direct' classification into a team run when flagged",
      'if _cls.get("mode") == "direct" and (_RUNS.get(pid) or {}).get("force_team"):' in src)
# ---------- F-31: never an empty reason; a gated scheduled run says it did NOT run
import dispatcher
d = dispatcher.default_dispatcher
d.route = lambda text, lang="en": {"leadAgent": "Backend", "agents": ["Backend"],
                                   "approval": {"required": True, "categories": [], "why": ""}}
r = d.respond("Run the backend task", "en")
check("F31-1: the dispatcher never shows an empty reason '()'", "()" not in r and "it would change files or state" in r, r)
import scheduler, scopes
_sc = f"member:{p['id']}:Backend"; _cid = scopes.create_chat(_sc)["id"]
t = {"id": "t1", "pid": p["id"], "title": "Backend nightly", "prompt": "Run the backend nightly task", "assignee": "Backend", "cid": _cid}
scheduler._run_task(t)
allchat = json.dumps(scopes.get_chat(_sc, _cid) or {}, ensure_ascii=False)
check("F31-2: a gated scheduled run says plainly it did NOT execute, with the reason", "did NOT execute" in allchat and "it would change files or state" in allchat, allchat[:300])
check("F31-3: ...and it does not claim an approval request was prepared", "I'll prepare an approval request" not in allchat)
# ---------- F-25
r = subprocess.run([sys.executable, str(root / "_consolidation/stepA_f25.py")], capture_output=True, text=True, cwd=root)
txt = (root / "workspace/shared/directions/core-rules.md").read_text() + (root / "workspace/shared/runbooks/azure-secure-connection.md").read_text()
check("F25-1: the guidance files now say ~/bendcore (no 'Bendcore')", "Bendcore" not in txt and "bendcore" in txt, r.stdout[-200:] + r.stderr[-300:])
bid = [l.split()[1] for l in r.stdout.splitlines() if l.startswith("BATCH")]
import workspace_mw as mw
rv = mw.revert_batch(bid[0], hold=False) if bid else {}
txt2 = (root / "workspace/shared/directions/core-rules.md").read_text()
check("F25-2: one-command revert restores the old text", "Bendcore" in txt2, rv)
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
