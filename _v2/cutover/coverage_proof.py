#!/usr/bin/env python3
"""Phase 9 proof: for each candidate folder, is every file's CONTENT present in v2 (sha256 match anywhere in v2)?
Skips rebuildable/derived content (.git internals, node_modules, venvs, caches, build outputs, test-run tmp).
Writes _v2/results/phase9_coverage.json + prints a summary. Names/paths only."""
import hashlib, json, os, pathlib, sys, collections, time
WS = pathlib.Path.home() / "Desktop/AiAgentWorkSpace"; V2 = WS / "Odin-Orchestrator-v2"
CANDS = sys.argv[1:] or ["Odin-Consolidated", "Odin-Isolated", "odin-v2-staging"]
SKIPD = {".git", "node_modules", ".venv", "venv", "__pycache__", ".dart_tool", "build", "release", "dist", ".pytest_cache",
         "iso_root", "Pods", ".gradle", ".idea", "DerivedData"}
def walk(root):
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIPD and not (d == "tmp" and "_research" in dp)]
        for f in fn:
            p = pathlib.Path(dp) / f
            try:
                if p.is_symlink() or not p.is_file(): continue
                yield p, p.stat().st_size
            except OSError: pass
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
t0 = time.time()
v2_by_size = collections.defaultdict(list)
for p, s in walk(V2): v2_by_size[s].append(p)
v2_hash = {}
def v2_has(h, s):
    for p in v2_by_size.get(s, []):
        if p not in v2_hash: v2_hash[p] = sha(p)
        if v2_hash[p] == h: return True
    return False
out = {}
for c in CANDS:
    root = WS / c; tot = cov = 0; size_tot = size_cov = 0; missing = collections.Counter(); miss_list = []
    for p, s in walk(root):
        tot += 1; size_tot += s
        if v2_has(sha(p), s): cov += 1; size_cov += s
        else:
            rel = str(p.relative_to(root)); top = "/".join(rel.split("/")[:2])
            missing[top] += 1; miss_list.append(rel)
    out[c] = {"files": tot, "covered": cov, "bytes": size_tot, "bytes_covered": size_cov,
              "missing_by_folder": missing.most_common(40), "missing_sample": miss_list[:300]}
    print(f"{c}: {cov}/{tot} files present in v2 ({100*cov/max(tot,1):.1f}%), {size_cov/1e6:.0f}/{size_tot/1e6:.0f} MB")
    for k, n in missing.most_common(15): print(f"     not in v2: {n:5d}  {k}")
(V2 / "_v2/results").mkdir(exist_ok=True)
(V2 / "_v2/results/phase9_coverage.json").write_text(json.dumps(out, indent=1))
print(f"done in {time.time()-t0:.0f}s")
