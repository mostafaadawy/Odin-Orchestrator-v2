#!/usr/bin/env python3
"""Make branch `main` ONE clean commit (no parent) for the new GitHub repo. Names/paths only, never values.
 1. every known credential value (current, rotation backups, v1) found in a TRACKED text file is replaced on
    disk by <REDACTED:KEY_NAME> (only dead values are in plain files; live connector keys are only in archives)
 2. archives that hold any value are untracked (kept on disk) + ignored; .bak_* backups ignored
 3. git add -A, then main := single parentless commit of that tree (old commit dropped locally)
 usage: make_clean_main.py [--apply]"""
import subprocess, sys, pathlib, re
sys.path.insert(0, str(pathlib.Path(__file__).parent)); import secretlib as S
APPLY = "--apply" in sys.argv; R = S.V2
def git(*a, **k): return subprocess.run(["git", *a], cwd=R, capture_output=True, check=True, **k).stdout
vals = S.load_values()
ign = (R / ".gitignore").read_text()
add_ign = [p for p in ("*.bak_*", "docs/program/_phase1_bundles/*.tgz") if p not in ign]
if APPLY and add_ign:
    (R / ".gitignore").write_text(ign.rstrip("\n") + "\n# never publish: rotation/edit backups + raw v1 bundles (hold credential values)\n" + "\n".join(add_ign) + "\n")
git("add", "-A") if APPLY else None
tracked = [p for p in git("ls-files", "-z").decode().split("\0") if p]
red, untrack = {}, []
for p in tracked:
    f = R / p
    if not f.is_file(): continue
    d = f.read_bytes()
    if S.ARCH.search(p):
        hits = set()
        for ip, b in S.members(p, d): hits |= S.scan_bytes(b, vals)[0]
        if hits: untrack.append((p, sorted(hits)))
        continue
    n = d
    for v, k in vals.items():
        if v in n: n = n.replace(v, f"<REDACTED:{k}>".encode()); red.setdefault(p, set()).add(k)
    if APPLY and n != d: f.write_bytes(n)
print("files redacted on disk (dead values only):")
for p, ks in sorted(red.items()): print("  ", p, sorted(ks))
print("archives untracked (kept on disk, ignored):")
for p, ks in untrack: print("  ", p, ks)
if not APPLY: sys.exit("dry run — re-run with --apply")
for p, _ in untrack:
    git("rm", "--cached", "-q", p)
    with open(R / ".gitignore", "a") as g: g.write(p + "\n")
git("add", "-A")
tree = git("write-tree").decode().strip()
msg = (b"Odin Orchestrator v2 - initial import (clean single commit; credential values removed)\n\n"
       b"Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01Eo7cH6GLnFTNPsW8AjYoQ2\n")
c = git("commit-tree", tree, input=msg).decode().strip()
git("update-ref", "refs/heads/main", c)
print("main =", c[:10], "parents=0 files=", len([x for x in git("ls-tree", "-r", "--name-only", c).decode().split("\n") if x]))
