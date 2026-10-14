#!/usr/bin/env python3
"""Copy EVERY file of the intermediate folders whose exact content is not already somewhere in v2 (older versions
included) into v2/_archive/<folder>/<same path>. Then the coverage proof reaches 100%. Nothing is deleted."""
import hashlib, os, pathlib, shutil, collections, sys
WS = pathlib.Path.home()/"Desktop/AiAgentWorkSpace"; V2 = WS/"Odin-Orchestrator-v2"; A = V2/"_archive"
SKIPD = {".git","node_modules",".venv","venv","__pycache__",".dart_tool","build","release","dist",".pytest_cache","iso_root","Pods",".gradle",".idea","DerivedData"}
def files(root):
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIPD and not (d == "tmp" and "_research" in dp)]
        for f in fn:
            p = os.path.join(dp, f)
            if not os.path.islink(p) and os.path.isfile(p): yield p
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
by_size = collections.defaultdict(list)
for p in files(V2): by_size[os.path.getsize(p)].append(p)
cache = {}
def present(p):
    h = sha(p)
    for q in by_size.get(os.path.getsize(p), ()):
        if q not in cache: cache[q] = sha(q)
        if cache[q] == h: return True
    return False
for c in sys.argv[1:] or ["Odin-Consolidated"]:
    n = 0
    for p in files(WS/c):
        if present(p): continue
        rel = os.path.relpath(p, WS/c); dst = A/c/rel
        if dst.exists(): dst = dst.with_name(dst.name + ".older")
        dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p, dst); n += 1
    print(f"{c}: archived {n} more files")
