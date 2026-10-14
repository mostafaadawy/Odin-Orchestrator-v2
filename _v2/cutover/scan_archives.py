#!/usr/bin/env python3
"""Scan INSIDE every compressed file (.tgz/.tar.gz/.zip/.gz) tracked in github-main for real credential values. Names only."""
import io, re, pathlib, subprocess, tarfile, zipfile, gzip
root = pathlib.Path(__file__).resolve().parents[2]; oth = root/"workspace/shared/oth"
vals = {}
for f in sorted(oth.glob(".cred*")):
    for line in f.read_text(errors="replace").splitlines():
        m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*(.+)", line)
        if m and m.group(1) != "KLAVIYO_API_REVISION":
            v = m.group(2).strip().strip('"').strip("'")
            if len(v) >= 10 and not v.startswith("http"): vals[v.encode()] = m.group(1)
g = lambda *a: subprocess.run(["git", *a], cwd=root, capture_output=True).stdout
hits = {}
import sys
REF = sys.argv[1] if len(sys.argv) > 1 else "github-main"
for line in g("ls-tree", "-r", REF).decode().splitlines():
    meta, path = line.split("\t", 1); sha = meta.split()[2]
    if not re.search(r"\.(tgz|tar\.gz|zip|gz|tar)$", path): continue
    data = g("cat-file", "blob", sha); members = []
    try:
        if path.endswith(".zip"):
            z = zipfile.ZipFile(io.BytesIO(data)); members = [(n, z.read(n)) for n in z.namelist() if not n.endswith("/")]
        elif re.search(r"\.(tgz|tar\.gz|tar)$", path):
            t = tarfile.open(fileobj=io.BytesIO(data)); members = [(m.name, t.extractfile(m).read()) for m in t.getmembers() if m.isfile()]
        else:
            members = [(path, gzip.decompress(data))]
    except Exception as e:
        print("could not open", path, type(e).__name__); continue
    for n, b in members:
        ks = sorted({k for v, k in vals.items() if v in b})
        if ks: hits.setdefault(path, []).append((n, ks))
print("archives with real values:", {p: [(n[:80], k) for n, k in v[:5]] for p, v in hits.items()} or "none")
