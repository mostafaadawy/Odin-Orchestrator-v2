#!/usr/bin/env python3
"""F-06 test (no LLM; engine stubbed to capture the prompt): a main-chat question first looks up EXISTING capability
in odin_core (directions) — visible to the owner and given to the CTO; read-only. python f06_test.py <root>"""
import sys, os, pathlib, threading
root = pathlib.Path(sys.argv[1]).resolve(); os.chdir(root); sys.path.insert(0, str(root / "server"))
import api_v2, directions
fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:300]}]" if info and not c else ""))
    if not c: fails.append(n)
SEEN = []
api_v2._engine_stream = lambda prompt, *a, **k: (SEEN.append(prompt), iter([]))[1]
def chat(scope, text):
    out = []
    def go():
        try:
            for ev in api_v2._scoped_gen(scope, text, "en", ""):
                out.append(str(ev))
        except Exception as e:
            out.append(f"EXC {e}")
    t = threading.Thread(target=go, daemon=True); t.start(); t.join(60)
    return " ".join(out)
def counts():
    return {t: directions._rows(f"SELECT count(*) c FROM {t}")[0].get("c") for t in ("projects", "agents", "files", "shared_capabilities")}
Q = "How is the health of the VM for our organics production deployment?"
c0 = counts()
has_lookup = hasattr(directions, "lookup")
r = directions.lookup(Q) if has_lookup else {"projects": []}
check("1: lookup finds the organics production deployment project", any("organics" in p["id"] for p in r["projects"]), r.get("projects"))
SEEN.clear(); ev = chat("company", Q)
check("2: the owner SEES the lookup in the main chat", "Looked up existing capability" in ev and "organics" in ev, ev[:400])
check("3: the CTO's prompt starts from the existing capability", bool(SEEN) and "[EXISTING CAPABILITY" in SEEN[-1] and "organics" in SEEN[-1], (SEEN[-1][:300] if SEEN else "no prompt"))
SEEN.clear(); ev = chat("company", "Write me a haiku about autumn leaves")
check("4: an unrelated question says nothing matching was found (no invented list)",
      bool(SEEN) and "nothing matching found" in SEEN[-1] and "- project " not in SEEN[-1], (SEEN[-1][:300] if SEEN else ""))
SEEN.clear(); ev5 = chat("project:revealer-6978", "How many tests does this project have?")
check("5: project chats are unchanged (no company lookup block)", bool(SEEN) and all("[EXISTING CAPABILITY" not in x for x in SEEN), ev5[:400])
c1 = counts(); directions.lookup(Q) if has_lookup else None; directions.lookup_note(Q) if has_lookup else None
check("6: the lookup itself is read-only (database counts unchanged around it)", has_lookup and counts() == c1, (c1, counts()))
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
