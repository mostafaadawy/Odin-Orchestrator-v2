#!/usr/bin/env python3
"""Make Odin-Consolidated independent of Odin-Isolated: repath + own DB names + own ports. Logs every file changed."""
import json, pathlib, re, subprocess
R = pathlib.Path(__file__).resolve().parent.parent
assert R.name == "Odin-Consolidated", R
SKIP_DIRS = {".git", "node_modules"}
KEEP_AS_RECORD = ("_research/results/", "_research/deliverables/", "_research/rescued/")
def text_files():
    for p in R.rglob("*"):
        if p.is_symlink() or not p.is_file(): continue
        rel = p.relative_to(R).as_posix()
        if set(p.relative_to(R).parts) & SKIP_DIRS: continue
        if rel.startswith(KEEP_AS_RECORD) or re.match(r"_research/[^/]+\.md$", rel): continue
        if rel.startswith("_consolidation/"): continue
        try: b = p.read_bytes()
        except Exception: continue
        if b"\0" in b[:4096]: continue
        yield p, rel, b
log = {"repath": [], "db": [], "ports": []}
remap_list = set(json.loads((R / "_isolation/db_port_remap_files.json").read_text()).keys())
PORTS = [("18000", "28000"), ("19100", "29100"), ("19104", "29104"), ("19300", "29300"), ("18080", "28080"),
         ("15432", "25432"), ("15433", "25433")]
for p, rel, b in text_files():
    s = b.decode("utf-8", errors="surrogateescape"); o = s
    if "Odin-Isolated" in s:
        s = s.replace("Odin-Isolated", "Odin-Consolidated"); log["repath"].append(rel)
    if "odin_core_iso" in s or "odin_anchor_iso" in s:
        s = s.replace("odin_core_iso", "odin_core_con").replace("odin_anchor_iso", "odin_anchor_con"); log["db"].append(rel)
    if rel in remap_list or rel.startswith("_isolation/") or rel.startswith("_research/exp/") or rel.startswith("_research/regression/"):
        s2 = s
        for a, c in PORTS:
            s2 = re.sub(r"(?<!\d)" + a + r"(?!\d)", c, s2)
        if s2 != s: log["ports"].append(rel); s = s2
    if s != o:
        p.write_bytes(s.encode("utf-8", errors="surrogateescape"))
(R / "_consolidation/remap_log.json").write_text(json.dumps({k: sorted(set(v)) for k, v in log.items()}, indent=1))
print({k: len(set(v)) for k, v in log.items()})
