#!/usr/bin/env python3
"""Summary (names only): which real values are in git history, which are in the CURRENT tracked tree, and whether
anything was added since the cutover start or by 5722cca. KLAVIYO_API_REVISION is an API version date, not a secret."""
import pathlib, re, subprocess, collections
root = pathlib.Path(__file__).resolve().parents[2]; oth = root / "workspace/shared/oth"
NOT_SECRET = {"KLAVIYO_API_REVISION"}
vals = {}
for f in sorted(oth.glob(".cred*")):
    for line in f.read_text(errors="replace").splitlines():
        m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*(.+)", line)
        if m and m.group(1) not in NOT_SECRET:
            v = m.group(2).strip().strip('"').strip("'")
            if len(v) >= 10 and not v.startswith("http"): vals.setdefault(v.encode(), set()).add(m.group(1))
g = lambda *a: subprocess.run(["git", *a], cwd=root, capture_output=True).stdout
# current tracked tree
cur = collections.defaultdict(set)
for p in g("ls-files", "-z").split(b"\0"):
    if not p: continue
    f = root / p.decode(errors="replace")
    try:
        b = f.read_bytes() if f.is_file() and f.stat().st_size < 30_000_000 else b""
    except Exception: b = b""
    for v, ks in vals.items():
        if v in b: cur[p.decode()].update(ks)
print("CURRENT tracked files holding a real value:")
for p, ks in sorted(cur.items()): print("  ", p, sorted(ks))
# history: per key, number of commits whose diff adds it, and whether any is after the cutover start
def commits_adding(v):
    return g("log", "--all", "--format=%h", "-S", v.decode()).decode().split()
since = set(g("rev-list", "a5818c6^..HEAD").decode().split())
since_short = {s[:7] for s in since}
for v, ks in vals.items():
    cs = commits_adding(v)
    if cs:
        recent = [c for c in cs if c[:7] in since_short]
        print(f"HISTORY {sorted(ks)}: changed in {len(cs)} commits; oldest {cs[-1]}; since cutover start: {recent or 'none'}")
print("5722cca touches a value:", any(v in g("show", "5722cca") for v in vals))
print("remotes:", g("remote", "-v").decode().split("\n")[:2])
