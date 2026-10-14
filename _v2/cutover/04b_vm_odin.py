#!/usr/bin/env python3
"""VM Odin contents + credential copies (owner conditions 1-5). NEVER prints a value; key NAMES only.
   python 04b_vm_odin.py inspect   READ-ONLY: what is under the Odin folders; every .cred* copy outside RBO with its key names
   python 04b_vm_odin.py cleanup   after the deploy wrote the minimal .cred: delete every OTHER Odin .cred* copy on the VM
RBO (~/bendcore, ~/organics) is never searched for deletion and never written."""
import sys, pathlib
V2 = pathlib.Path(__file__).resolve().parents[2]; sys.path.insert(0, str(V2 / "server"))
import deploy_ssh as d
FIND = r"""import os, sys
SKIP = ("/home/mostafa/bendcore", "/home/mostafa/organics")
def names(f):
    out = []
    for raw in open(f, encoding="utf-8", errors="replace").read().splitlines():
        s = raw.strip()
        if not s or s.startswith("#"): continue
        k = s.split("=", 1)[0] if ("=" in s and ":" not in s.split("=", 1)[0]) else (s.split(":", 1)[0] if ":" in s else "(unnamed)")
        out.append(k.strip())
    return out
hits = []
for root, dirs, files in os.walk("/home/mostafa"):
    if root.startswith(SKIP) or root.count("/") > 8: dirs[:] = []; continue
    dirs[:] = [x for x in dirs if x not in ("node_modules", ".venv", ".git", ".cache")]
    hits += [os.path.join(root, f) for f in files if f.startswith(".cred")]
MODE = sys.argv[1]; KEEP = "/home/mostafa/anchor-online/.cred"
ODIN = ("/home/mostafa/anchor-online/", "/home/mostafa/odin-web/", "/home/mostafa/odin_backups/", "/home/mostafa/workspace/")
for f in hits:
    if MODE == "inspect":
        print("   %s  [%d bytes]  keys: %s" % (f, os.path.getsize(f), ", ".join(names(f))))
    elif f != KEEP and f.startswith(ODIN):
        os.remove(f); print("   deleted", f)
    elif f != KEEP:
        print("   NOT an Odin path, left alone:", f)
if MODE == "cleanup" and os.path.exists(KEEP): print("   kept", KEEP, "keys:", ", ".join(names(KEEP)))
"""
INSPECT = r"""
set +e
cd /home/mostafa
echo "== folders in /home/mostafa that look like Odin:"; ls -d */ 2>/dev/null | grep -iE 'odin|anchor|workspace'
for d in anchor-online odin-web; do
  [ -d $d ] || { echo "$d: missing"; continue; }
  echo "== $d: $(find $d -path '*/.venv' -prune -o -type f -print | wc -l) files (without .venv), $(du -sh --exclude=.venv $d | cut -f1)"
  find $d -maxdepth 2 -path '*/.venv' -prune -o -print | sed 's#^#   #' | head -60
done
[ -d /home/mostafa/workspace ] && echo "!! /home/mostafa/workspace EXISTS: $(find /home/mostafa/workspace -type f | wc -l) files" || echo "no /home/mostafa/workspace"
echo "== .cred copies outside bendcore/organics (key NAMES only):"
python3 - inspect <<'PY'
""" + "__FIND__" + r"""
PY
"""
CLEAN = r"""
python3 - cleanup <<'PY'
""" + "__FIND__" + r"""
PY
"""
INSPECT = INSPECT.replace("__FIND__", FIND); CLEAN = CLEAN.replace("__FIND__", FIND)
mode = sys.argv[1] if len(sys.argv) > 1 else "inspect"
d.refresh_firewall()
r = d.ssh_exec(INSPECT if mode == "inspect" else CLEAN, timeout=300)
print(r.get("out", "") or r.get("error", ""))
sys.exit(0 if r.get("ok", False) else 1)
