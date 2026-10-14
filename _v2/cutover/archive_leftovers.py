#!/usr/bin/env python3
"""Before Phase 9: copy into v2/_archive/ (git-ignored) everything from the intermediate folders that is NOT
already in v2 by content, plus a git bundle of each intermediate repo's full history. Nothing is deleted here."""
import json, os, pathlib, shutil, subprocess, hashlib
WS = pathlib.Path.home()/"Desktop/AiAgentWorkSpace"; V2 = WS/"Odin-Orchestrator-v2"; A = V2/"_archive"
A.mkdir(exist_ok=True)
absent = json.load(open(V2/"_v2/results/phase9_consolidated_absent.json"))
n = b = 0
for _, rels in absent.items():
    for rel in rels:
        src = WS/"Odin-Consolidated"/rel; dst = A/"Odin-Consolidated"/rel
        dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, dst); n += 1; b += src.stat().st_size
for rel in ("_phase1_bundles/B5b_build_heads.txt", "_phase1_bundles/B1_core_docs.txt"):
    src = WS/"odin-v2-staging"/rel; dst = A/"odin-v2-staging"/rel
    if src.exists(): dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, dst); n += 1; b += src.stat().st_size
print(f"copied {n} not-in-v2 files ({b/1e6:.1f} MB) into _archive/")
for repo in ("Odin-Consolidated", "Odin-Isolated", "odin-v2-staging"):
    r = WS/repo
    if (r/".git").exists():
        out = A/f"{repo}.git.bundle"
        res = subprocess.run(["git", "bundle", "create", str(out), "--all"], cwd=r, capture_output=True, text=True)
        ok = res.returncode == 0 and subprocess.run(["git", "bundle", "verify", str(out)], cwd=r, capture_output=True).returncode == 0
        print(f"{repo}: full git history bundle {'✓ verified' if ok else '✗ ' + res.stderr[-200:]}  ({out.stat().st_size/1e6:.1f} MB)" if out.exists() else f"{repo}: bundle failed")
    else:
        print(f"{repo}: not a git repo (files only)")
