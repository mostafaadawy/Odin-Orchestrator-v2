#!/usr/bin/env python3
"""Scrub the isolated test clone: replace every REAL credential value (from the owner's local .cred and its rotation
backups) found anywhere in _v2/iso_root (chat transcripts, logs, seeds, research copies) with a placeholder.
Prints counts and key names only."""
import pathlib, re
root = pathlib.Path(__file__).resolve().parents[2]; oth = root / "workspace/shared/oth"; iso = root / "_v2/iso_root"
NOT_SECRET = {"KLAVIYO_API_REVISION"}          # an API version date, not a secret
vals = {}
for f in sorted(oth.glob(".cred*")):
    for line in f.read_text(errors="replace").splitlines():
        m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*(.+)", line)
        if m and m.group(1) not in NOT_SECRET:
            v = m.group(2).strip().strip('"').strip("'")
            if len(v) >= 10 and not v.startswith("http"): vals[v.encode()] = m.group(1)
files = names = 0; left = set()
for f in iso.rglob("*") if iso.exists() else []:
    try:
        if not f.is_file() or f.is_symlink() or f.stat().st_size > 50_000_000: continue
        b = f.read_bytes(); nb = b
        for v, k in vals.items():
            if v in nb: nb = nb.replace(v, b"SCRUBBED_" + k.encode()); left.add(k)
        if nb != b: f.write_bytes(nb); files += 1
    except Exception: pass
print(f"  iso scrub: {files} files cleaned; key names found: {sorted(left) or 'none'}")
