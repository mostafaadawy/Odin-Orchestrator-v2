#!/usr/bin/env python3
"""For a ref: which leaked values are CURRENT (live) vs OLD (already replaced). Names only. Also shows the
variable NAME + value LENGTH for every secret-shape (method 2) hit outside archives, so false positives can be judged."""
import subprocess, sys, pathlib, re
sys.path.insert(0, str(pathlib.Path(__file__).parent)); import secretlib as S
ref = sys.argv[1]
cur = {}
for line in (S.V2 / "workspace/shared/oth/.cred").read_text(errors="replace").splitlines():
    m = re.match(r"\s*([A-Za-z_]\w*)\s*[:=]\s*(.+)", line)
    if m: cur[m.group(1)] = m.group(2).strip().strip('"').strip("'").encode()
allv = S.load_values()
tree = subprocess.run(["git", "ls-tree", "-r", ref], cwd=S.V2, capture_output=True, text=True).stdout.splitlines()
found = {}
for l in tree:
    meta, p = l.split("\t", 1); sha = meta.split()[2]
    d = subprocess.run(["git", "cat-file", "blob", sha], cwd=S.V2, capture_output=True).stdout
    items = [(p, d)] + (list(S.members(p, d)) if S.ARCH.search(p) else [])
    for ip, b in items:
        for v, k in allv.items():
            if v in b: found.setdefault(k, set()).add("CURRENT(live)" if cur.get(k) == v else "OLD(replaced)")
        if "!" not in ip:
            for m in S.PATTERNS["assigned-secret"].finditer(b):
                s = m.group(0); name = re.match(rb"(?i)\s*([A-Z0-9_]+)", s).group(1).decode()
                val = re.split(rb"[:=]\s*[\"']?", s, 1)[1]
                print(f"  shape-hit {ip} :: var={name} value_len={len(val)} looks_like={'hex' if re.fullmatch(rb'[0-9a-f]+', val) else 'mixed'}")
print("leaked key status:")
for k, st in sorted(found.items()): print(f"  {k}: {sorted(st)}")
