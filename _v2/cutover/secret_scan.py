#!/usr/bin/env python3
"""Scan EVERY git object (all commits, all branches/tags, unreachable too) and the isolated test clone for any real
credential value from the local .cred and its rotation backups. Prints KEY NAMES and counts only — never a value."""
import pathlib, re, subprocess, sys
root = pathlib.Path(__file__).resolve().parents[2]; oth = root / "workspace/shared/oth"
vals = {}
for f in sorted(oth.glob(".cred*")):
    for line in f.read_text(errors="replace").splitlines():
        m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*(.+)", line)
        if m:
            v = m.group(2).strip().strip('"').strip("'")
            if len(v) >= 10 and not v.startswith("http"): vals.setdefault(v, set()).add(m.group(1))
print("files scanned for values:", [f.name[:18] + "…" for f in sorted(oth.glob(".cred*"))], "values:", len(vals))
# 1) every git object
p = subprocess.run(["git", "cat-file", "--batch-all-objects", "--batch"], cwd=root, capture_output=True)
blob = p.stdout
hit_git = sorted({n for v, ns in vals.items() if v.encode() in blob for n in ns})
print("git objects size MB:", round(len(blob) / 1e6, 1), "| key names whose value is in ANY git object:", hit_git or "none")
# 2) isolated test clone
iso = root / "_v2/iso_root"; hit_iso = {}
if iso.exists():
    for f in iso.rglob("*"):
        try:
            if f.is_file() and f.stat().st_size < 20_000_000 and ".git/" not in str(f):
                b = f.read_bytes()
                for v, ns in vals.items():
                    if v.encode() in b: hit_iso.setdefault(str(f.relative_to(iso))[:90], set()).update(ns)
        except Exception: pass
print("test clone files holding a real value:", {k: sorted(v) for k, v in hit_iso.items()} or "none")
