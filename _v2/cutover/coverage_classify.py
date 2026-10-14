#!/usr/bin/env python3
import json, os, pathlib, collections, hashlib
WS = pathlib.Path.home()/"Desktop/AiAgentWorkSpace"; V2 = WS/"Odin-Orchestrator-v2"; C = WS/"Odin-Consolidated"
d = json.load(open(V2/"_v2/results/phase9_coverage.json"))
# rebuild full missing list (sample was capped) by re-running the walk on Consolidated only
import importlib.util
spec = importlib.util.spec_from_file_location("cp", V2/"_v2/cutover/coverage_proof.py")
SKIPD = {".git","node_modules",".venv","venv","__pycache__",".dart_tool","build","release","dist",".pytest_cache","iso_root","Pods",".gradle",".idea","DerivedData"}
v2names = collections.defaultdict(list)
for dp, dn, fn in os.walk(V2):
    dn[:] = [x for x in dn if x not in SKIPD]
    for f in fn: v2names[f].append(os.path.join(dp, f))
def sha(p):
    h=hashlib.sha256(); h.update(open(p,'rb').read()); return h.hexdigest()
v2sizes = collections.defaultdict(set)
for dp, dn, fn in os.walk(V2):
    dn[:] = [x for x in dn if x not in SKIPD]
    for f in fn:
        p=os.path.join(dp,f)
        try: v2sizes[os.path.getsize(p)].add(p)
        except OSError: pass
cache={}
def present(p):
    s=os.path.getsize(p); h=sha(p)
    for q in v2sizes.get(s,()):
        if q not in cache: cache[q]=sha(q)
        if cache[q]==h: return True
    return False
cls = collections.Counter(); absent = collections.defaultdict(list)
for dp, dn, fn in os.walk(C):
    dn[:] = [x for x in dn if x not in SKIPD and not (x=="tmp" and "_research" in dp)]
    for f in fn:
        p = os.path.join(dp, f)
        if os.path.islink(p) or not os.path.isfile(p): continue
        if present(p): continue
        rel = os.path.relpath(p, C)
        cand = [V2/rel, V2/rel.replace("_research/", "research/consolidation/",1), V2/rel.replace("_research/phase4/","research/phase4/",1)]
        if any(x.exists() for x in cand): cls["newer version in v2 (same path)"] += 1
        elif f in v2names: cls["same file name elsewhere in v2"] += 1
        else:
            cls["NOT in v2"] += 1; absent["/".join(rel.split("/")[:3])].append(rel)
print(dict(cls))
for k, v in sorted(absent.items(), key=lambda x: -len(x[1]))[:30]: print(f"  {len(v):4d}  {k}   e.g. {v[0]}")
json.dump({k: v for k, v in absent.items()}, open(V2/"_v2/results/phase9_consolidated_absent.json","w"), indent=1)
