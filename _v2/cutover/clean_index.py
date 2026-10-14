#!/usr/bin/env python3
"""After `git add -A`: any STAGED file holding a known credential value is committed in redacted form
(<REDACTED:KEY>) while the file on disk stays untouched (skip-worktree). Staged archives holding a value are
unstaged. Names/paths only, never values."""
import subprocess, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent)); import secretlib as S
R = S.V2; vals = S.load_values()
def git(*a, **k): return subprocess.run(["git", *a], cwd=R, capture_output=True, check=True, **k).stdout
staged = [l for l in git("ls-files", "-s", "-z").decode().split("\0") if l]
red, unstaged = [], []
for l in staged:
    meta, p = l.split("\t", 1); mode, sha, _ = meta.split()
    d = git("cat-file", "blob", sha)
    if S.ARCH.search(p):
        if any(S.scan_bytes(b, vals)[0] for _, b in S.members(p, d)):
            git("rm", "--cached", "-q", p); unstaged.append(p)
        continue
    n = d; ks = set()
    for v, k in vals.items():
        if v in n: n = n.replace(v, f"<REDACTED:{k}>".encode()); ks.add(k)
    if ks:
        nsha = git("hash-object", "-w", "--stdin", input=n).decode().strip()
        git("update-index", "--cacheinfo", f"{mode},{nsha},{p}")
        git("update-index", "--skip-worktree", p); red.append((p, sorted(ks)))
print(f"staged files: {len(staged)}")
print("committed redacted (disk copy untouched, skip-worktree):"); [print("  ", p, k) for p, k in red]
print("archives left out:"); [print("  ", p) for p in unstaged]
