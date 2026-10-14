#!/usr/bin/env python3
"""PC-2 / F-16 test (no LLM): generic replies can never pass a step; wrong-format replies get one correction
retry. python pc2_test.py <root> <iso>"""
import sys, os, pathlib, json, glob, time
root = pathlib.Path(sys.argv[1]).resolve(); iso = pathlib.Path(sys.argv[2]).resolve()
os.chdir(root); sys.path.insert(0, str(root / "server"))
fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:300]}]" if info and not c else ""))
    if not c: fails.append(n)
try:
    import reply_guard as rg
except Exception as e:
    rg = None
TASK = "Build the order sync service for the shop and add tests"
generic = ["", "Done.", "I've completed the task. Let me know if you need anything else!",
           "Sure! I'll help with that and take care of everything for the shop.",
           "Build the order sync service for the shop and add tests — done for the shop service."]
real = ["Created workspace/projects/shop/code/sync.py and ran `pytest` — 12 tests passed.",
        "```proposal\n{\"summary\": \"add sync\", \"files\": [{\"path\": \"code/sync.py\"}]}\n```",
        'KEY_REQUEST: {"service": "klaviyo", "name": "KLAVIYO_KEY", "why": "needed"}',
        "Deployed; curl https://shop.example/health returned HTTP 200 in 140 ms."]
g = [bool(rg and rg.generic_reply(x, TASK)) for x in generic]; r = [bool(rg and rg.generic_reply(x, TASK)) for x in real]
check("1: generic replies are detected (empty, one line, boilerplate, task echo)", all(g), g)
check("2: replies with concrete work are not flagged", rg is not None and not any(r), r)
# 3: false-positive rate on REAL step reports (v1 + copy member chats)
reps = []
for f in glob.glob(str(iso / "workspace/chats/scopes/member__*/chats/*.json")) + glob.glob(str(iso.parent / "Odin-Orchestrator/workspace/chats/scopes/member__*/chats/*.json")):
    try: d = json.load(open(f))
    except Exception: continue
    pu = ""
    for m in (d.get("messages") if isinstance(d, dict) else d) or []:
        if not isinstance(m, dict): continue
        if m.get("role") == "user": pu = m.get("content", "")
        c = m.get("content") or ""
        if m.get("role") == "assistant" and len(c) >= 200 and not c.startswith(("↳", "▶", "[Done]")): reps.append((pu, c))
fp = [c[:80] for t, c in reps if rg and rg.generic_reply(c, t)]
check(f"3: no false alarm on {len(reps)} real step reports (v1 + copy)", rg is not None and len(reps) > 100 and not fp, fp[:3])
import api_v2
V = 'VERDICT: {"verdict": "PASSED", "evidence_files": [], "reason": "done"}'
try:
    o1, d1 = api_v2._step_outcome("revealer-6978", TASK, "Confirmed: ok.\n" + V, True, True, False, time.time(), "", reply="Done.")
except TypeError:
    o1, d1 = "PASSED", {"checks": ["no reply parameter"]}
check("4: a step whose reply is generic is NOT_DONE even when the review says PASSED", o1 == "NOT_DONE" and any("generic reply" in c for c in d1["checks"]), (o1, d1.get("checks")))
o2, d2 = api_v2._step_outcome("revealer-6978", TASK, "Confirmed: ok.\n" + V, True, True, False, time.time(), "",
                              **({"reply": real[0]} if "reply" in api_v2._step_outcome.__code__.co_varnames else {}))
check("5: a reply with concrete work is not blocked by the guard", not any("generic reply" in c for c in d2.get("checks", [])), d2.get("checks"))
import projects
calls = []
projects._engine = lambda p, **k: (calls.append(p), '{"recommend": true, "why": "real code"}')[1]
jr = getattr(projects, "json_retry", None)
v = jr("I think yes, QA matters here because of real code changes.", "object", '{"recommend": true|false}') if jr else None
check("6: wrong format: ONE correction retry turns the reply into the required JSON", v == {"recommend": True, "why": "real code"} and len(calls) == 1, (v, len(calls)))
src = (root / "server" / "api_v2.py").read_text()
check("7: the CTO review gets ONE retry for a missing VERDICT line; QA and fixer decisions use the retry",
      "wrong format — ask ONCE for the missing VERDICT line" in src and src.count("projects.json_retry(") >= 2)
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
