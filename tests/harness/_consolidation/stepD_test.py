#!/usr/bin/env python3
"""Step D test (no LLM): F-22. N5 — two PROCESSES share the JSON anchor queue (no Postgres): no request is lost and no
request is handed out twice. N6 — phase_ctl registers a localhost webhook only for the local anchor. N7 — the desktop
login-code poll honours the editable production anchor. python stepD_test.py <root> <iso_root>"""
import sys, os, pathlib, subprocess, json, collections
root = pathlib.Path(sys.argv[1]).resolve(); iso = pathlib.Path(sys.argv[2]); os.chdir(root)
fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:300]}]" if info and not c else ""))
    if not c: fails.append(n)
CHILD = r'''
import sys, os, json, time
os.environ.pop("ANCHOR_PG_DSN", None)
sys.path.insert(0, "server")
import anchor_queue as q
tag, n = sys.argv[1], int(sys.argv[2]); got = []
for i in range(n):
    q.enqueue("t", {"i": i, "w": tag}, sender=tag)
    got += [r["id"] for r in q.next_pending(3)]
for _ in range(30):
    got += [r["id"] for r in q.next_pending(10)]
open(f"_got_{tag}.json", "w").write(json.dumps(got))
'''
env = {k: v for k, v in os.environ.items() if k != "ANCHOR_PG_DSN"}
qf = root / "workspace" / "anchor-layer" / "anchor_queue.json"
for p in [qf] + list(root.glob("data/anchor_queue.json")):
    if p.exists(): p.unlink()
sys.path.insert(0, str(root / "server")); os.environ.pop("ANCHOR_PG_DSN", None)
import anchor_queue as q0
check("N5-0: the test runs on the JSON queue (no Postgres)", q0.backend() != "postgres", q0.backend())
q0.clear_all()
N = 120
ps = [subprocess.Popen([sys.executable, "-c", CHILD, t, str(N)], cwd=root, env=env) for t in ("A", "B")]
for p in ps: p.wait(timeout=170)
rows = q0._row_all()
check(f"N5-1: no request is lost ({2*N} enqueued by two processes at once)", len(rows) == 2 * N, len(rows))
got = json.loads((root / "_got_A.json").read_text()) + json.loads((root / "_got_B.json").read_text())
dup = [k for k, v in collections.Counter(got).items() if v > 1]
check("N5-2: no request is handed out twice", not dup, f"{len(dup)} duplicates")
sh = (root / "shells/phase_ctl.sh").read_text() if (root / "shells/phase_ctl.sh").exists() else (iso / "shells/phase_ctl.sh").read_text()
seg = sh[sh.index("do_send(){"):sh.index("do_send(){") + 1400]
check("N6: phase_ctl registers a localhost webhook ONLY for the local anchor", 'if [ -n "$VM_IP" ]; then' in seg and seg.count("webhook_url") == 1, seg[:200])
app = (root / "desktop/src/App.jsx").read_text() if (root / "desktop/src/App.jsx").exists() else ""
i = app.find("pending-code")
check("N7: the desktop login-code poll honours the editable production anchor", 'localStorage.getItem("odin.prod.anchor")' in app[max(0, i - 900):i])
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
