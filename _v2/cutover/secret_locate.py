#!/usr/bin/env python3
"""Which git blobs (path + first commit + reachable?) hold a real credential value. Names only."""
import pathlib, re, subprocess
root = pathlib.Path(__file__).resolve().parents[2]; oth = root / "workspace/shared/oth"
vals = {}
for f in sorted(oth.glob(".cred*")):
    for line in f.read_text(errors="replace").splitlines():
        m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*(.+)", line)
        if m:
            v = m.group(2).strip().strip('"').strip("'")
            if len(v) >= 10 and not v.startswith("http"): vals.setdefault(v.encode(), set()).add(m.group(1))
g = lambda *a: subprocess.run(["git", *a], cwd=root, capture_output=True).stdout
ids = [l.split()[0] for l in g("cat-file", "--batch-all-objects", "--batch-check").decode().splitlines() if l.split()[1] == "blob"]
proc = subprocess.Popen(["git", "cat-file", "--batch"], cwd=root, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
hits = {}
for sha in ids:
    proc.stdin.write((sha + "\n").encode()); proc.stdin.flush()
    hdr = proc.stdout.readline().split(); n = int(hdr[2]); data = proc.stdout.read(n); proc.stdout.read(1)
    names = sorted({k for v, ks in vals.items() if v in data for k in ks})
    if names: hits[sha] = names
proc.stdin.close()
reach = {}
for line in g("rev-list", "--all", "--objects").decode(errors="replace").splitlines():
    p = line.split(" ", 1)
    if p[0] in hits: reach[p[0]] = p[1] if len(p) > 1 else ""
for sha, names in hits.items():
    path = reach.get(sha)
    first = g("log", "--all", "--format=%h %ad", "--date=short", "--diff-filter=A", "--find-object=" + sha).decode().split("\n")[-2:] if path is not None else []
    print(f"blob {sha[:10]} {'REACHABLE path=' + path if path is not None else 'UNREACHABLE (not in any commit)'} keys={names} added_in={[x for x in first if x]}")
print("total blobs with a real value:", len(hits))
