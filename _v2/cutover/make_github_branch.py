#!/usr/bin/env python3
"""Build a CLEAN, history-free branch `github-main` from the current HEAD tree, for a NEW GitHub repo.
- One commit, no parent: none of the inherited v1 history (which holds old key values) is included.
- Every real credential value (from the local .cred and its backups) found in a tracked file is replaced by
  <REDACTED:KEY_NAME> in that commit only. The working folder and the existing history are NOT changed.
- Afterwards every blob of the new commit is re-scanned; it fails loudly if any value remains.
Prints key NAMES and file paths only, never a value."""
import os, pathlib, re, subprocess, sys, tempfile
root = pathlib.Path(__file__).resolve().parents[2]; oth = root / "workspace/shared/oth"
NOT_SECRET = {"KLAVIYO_API_REVISION"}
vals = {}
for f in sorted(oth.glob(".cred*")):
    for line in f.read_text(errors="replace").splitlines():
        m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*(.+)", line)
        if m and m.group(1) not in NOT_SECRET:
            v = m.group(2).strip().strip('"').strip("'")
            if len(v) >= 10 and not v.startswith("http"): vals[v.encode()] = m.group(1)
def git(*a, inp=None, env=None):
    r = subprocess.run(["git", *a], cwd=root, input=inp, capture_output=True, env=env)
    if r.returncode: sys.exit(f"git {' '.join(a[:2])} failed: {r.stderr.decode()[:300]}")
    return r.stdout
tmp_index = tempfile.mktemp(prefix="odin_idx_")
env = {**os.environ, "GIT_INDEX_FILE": tmp_index}
git("read-tree", "HEAD", env=env)
changed = {}
for line in git("ls-files", "-s", "-z", env=env).split(b"\0"):
    if not line: continue
    meta, path = line.split(b"\t", 1); mode, sha, _ = meta.split()
    if re.search(r"\.(tgz|tar\.gz|tar|zip)$", path.decode()) and path.decode().startswith("docs/program/_phase1_bundles/"):
        # phase-1 raw bundles of v1 (source/chats) hold old credential values INSIDE the archive and are
        # redundant (v1 itself is kept) — left out of the GitHub tree
        git("update-index", "--force-remove", path.decode(), env=env); changed.setdefault(path.decode(), set()).add("(left out — archive with old values)"); continue
    data = git("cat-file", "blob", sha.decode())
    new = data
    for v, k in vals.items():
        if v in new: new = new.replace(v, f"<REDACTED:{k}>".encode()); changed.setdefault(path.decode(), set()).add(k)
    if new != data:
        nsha = git("hash-object", "-w", "--stdin", inp=new).decode().strip()
        git("update-index", "--cacheinfo", f"{mode.decode()},{nsha},{path.decode()}", env=env)
tree = git("write-tree", env=env).decode().strip()
msg = b"Odin Orchestrator v2 - initial import (clean history; credential values redacted)\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01Eo7cH6GLnFTNPsW8AjYoQ2\n"
commit = git("commit-tree", tree, inp=msg).decode().strip()
git("update-ref", "refs/heads/github-main", commit)
os.unlink(tmp_index)
print("redacted in the clean commit (names only):")
for p, ks in sorted(changed.items()): print("  ", p, sorted(ks))
# verify: no value in any blob of the new tree
leaks = 0
for line in git("ls-tree", "-r", "-z", commit).split(b"\0"):
    if not line: continue
    sha = line.split()[2].decode()
    data = git("cat-file", "blob", sha)
    leaks += sum(1 for v in vals if v in data)
files = len([l for l in git("ls-tree", "-r", "--name-only", commit).split(b"\n") if l])
print(f"github-main = {commit[:10]}  files={files}  parents=0  remaining credential values={leaks}")
sys.exit(1 if leaks else 0)
