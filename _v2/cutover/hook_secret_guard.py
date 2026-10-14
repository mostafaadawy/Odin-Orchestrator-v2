#!/usr/bin/env python3
"""git hook guard. pre-commit: block if any STAGED file (or file inside a staged archive) holds a known credential
value. pre-push: block if anything reachable from the pushed commits holds one. Names/paths only."""
import subprocess, sys, pathlib
R = pathlib.Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip())
sys.path.insert(0, str(R / "_v2/cutover")); import secretlib as S
vals = S.load_values(); bad = []
def check(label, data):
    items = [(label, data)] + (list(S.members(label, data)) if S.ARCH.search(label) else [])
    for ip, b in items:
        k = S.scan_bytes(b, vals)[0]
        if k: bad.append((ip, sorted(k)))
mode = sys.argv[1]
if mode == "pre-commit":
    for p in subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"], capture_output=True).stdout.decode().split("\0"):
        if p: check(p, subprocess.run(["git", "show", f":{p}"], capture_output=True).stdout)
else:
    for line in sys.stdin.read().splitlines():
        parts = line.split()
        if len(parts) == 4 and set(parts[1]) != {"0"}:
            for l in subprocess.run(["git", "rev-list", "--objects", parts[1]], capture_output=True, text=True).stdout.splitlines():
                if " " in l:
                    sha, p = l.split(" ", 1)
                    if subprocess.run(["git", "cat-file", "-t", sha], capture_output=True, text=True).stdout.strip() == "blob":
                        check(p, subprocess.run(["git", "cat-file", "blob", sha], capture_output=True).stdout)
if bad:
    print(f"✋ BLOCKED ({mode}): credential values found (names only):")
    for p, k in bad[:50]: print("   ", p, k)
    sys.exit(1)
print(f"✓ secret guard ({mode}): 0 credential values")
