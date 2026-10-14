#!/usr/bin/env python3
"""Independent proof scan of EVERYTHING reachable from a git ref (every commit, every blob, and every file
inside every archive, recursively). Method 1: exact match against every known credential value (current
.cred, all rotation backups, v1 .cred files). Method 2: generic secret-shape regexes.
Prints key NAMES, pattern names and paths only — never a value.  usage: scan_commit.py <ref> [report.txt]"""
import subprocess, sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).parent)); import secretlib as S
ref = sys.argv[1]; out = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else None
vals = S.load_values()
objs = subprocess.run(["git", "rev-list", "--objects", ref], cwd=S.V2, capture_output=True, text=True, check=True).stdout.split("\n")
paths = {}
for l in objs:
    if " " in l: sha, p = l.split(" ", 1); paths.setdefault(sha, p)
commits = subprocess.run(["git", "rev-list", ref], cwd=S.V2, capture_output=True, text=True).stdout.split()
batch = subprocess.Popen(["git", "cat-file", "--batch"], cwd=S.V2, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
vhits, phits, nblob, narch, nmem, unread = collections.defaultdict(set), collections.defaultdict(set), 0, 0, 0, []
def blob(sha):
    batch.stdin.write((sha + "\n").encode()); batch.stdin.flush()
    hdr = batch.stdout.readline().split()
    if len(hdr) < 3 or hdr[1] != b"blob":
        if len(hdr) >= 3: batch.stdout.read(int(hdr[2]) + 1)
        return None
    d = batch.stdout.read(int(hdr[2])); batch.stdout.read(1); return d
for sha, p in paths.items():
    d = blob(sha)
    if d is None: continue
    nblob += 1
    k, pt = S.scan_bytes(d, vals)
    for x in k: vhits[x].add(p)
    for x in pt: phits[x].add(p)
    if S.ARCH.search(p):
        narch += 1
        for ip, b in S.members(p, d):
            nmem += 1
            if "<UNREADABLE" in ip: unread.append(ip); continue
            k, pt = S.scan_bytes(b, vals)
            for x in k: vhits[x].add(ip)
            for x in pt: phits[x].add(ip)
lines = [f"ref={ref} commits={len(commits)} blobs={nblob} archives={narch} files-inside-archives={nmem} "
         f"known-values-checked={len(vals)} (from {sum(1 for f in S.CRED_FILES if f.exists())} .cred files) patterns={len(S.PATTERNS)}",
         f"METHOD 1 exact credential values found: {sum(len(v) for v in vhits.values())} locations"]
for k in sorted(vhits): lines += [f"  {k}: {len(vhits[k])}"] + [f"     {x}" for x in sorted(vhits[k])[:400]]
lines.append(f"METHOD 2 secret-shape matches: {sum(len(v) for v in phits.values())} locations")
for k in sorted(phits): lines += [f"  {k}: {len(phits[k])}"] + [f"     {x}" for x in sorted(phits[k])[:400]]
lines.append(f"unreadable archives: {len(unread)} {unread[:20]}")
txt = "\n".join(lines); (out.write_text(txt) if out else None)
print("\n".join(l for l in lines if not l.startswith("     ")))
