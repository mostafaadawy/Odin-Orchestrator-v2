"""Odin-Isolated regression suite. Run after EVERY change; any metric worse than baseline = REGRESSION (revert).
usage: python regress.py <temp_root> [--save-baseline]
Measures behaviour only (no structure/design/DB changes). Writes results/regression_<ts>.json."""
import sys, os, json, re, time, pathlib, py_compile, urllib.request, threading, http.server, importlib
TR = pathlib.Path(sys.argv[1]).resolve()                     # throwaway root (from exp/mkroot.sh)
if "/_research/tmp/" not in str(pathlib.Path(sys.argv[1]).resolve()) or not (pathlib.Path(sys.argv[1]) / "server").is_dir():
    sys.exit("REFUSED: root must be a throwaway root under _research/tmp with server/ (safety guard)")
ISO = pathlib.Path("/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Isolated")
RES = ISO / "_research" / "results"; BASE = ISO / "_research" / "regression" / "baseline.json"
os.environ["ANCHOR_PG_DSN"] = "dbname=odin_anchor_iso"
os.environ["PGHOST"] = str(ISO / "_research/tmp/pg/sock"); os.environ["PGPORT"] = os.environ.get("EXP_PGPORT", "15433")
sys.path[:0] = [str(TR / "server"), str(TR / "orchestrator"), str(TR)]
os.chdir(TR)   # some modules write paths relative to the CWD — keep every write inside the throwaway root
M, F = {}, []          # metrics, failures
def chk(name, ok, detail=""):
    M[name] = bool(ok)
    if not ok: F.append(f"{name}: {detail}")

# R1 — isolation invariants (static, over the REAL isolated copy)
code_ext = (".py", ".sh", ".js", ".cjs", ".mjs", ".dart", ".jsx", ".ts")
bad_ref = re.compile(r"(?:/Users/mostafaadawy|~|\$HOME)/Desktop/(?:AiAgentWorkSpace/Odin-Orchestrator|Odin(?![A-Za-z0-9_\-])|OdinTesting|VolatileWorkSpace)")
n_bad = 0
for d in ("server", "orchestrator", "shells", "workspace/shared", "desktop/src", "desktop/electron", "odin_app/lib"):
    for p in (ISO / d).rglob("*"):
        if p.is_file() and p.suffix in code_ext and ".bak" not in p.name:
            try:
                if bad_ref.search(p.read_text(errors="ignore")): n_bad += 1
            except Exception: pass
chk("R1.no_real_path_in_code", n_bad == 0, f"{n_bad} files")
ck = json.loads((ISO / "workspace/shared/core-registry/connector_keys.json").read_text())
def leaves(o):
    if isinstance(o, dict):
        for v in o.values(): yield from leaves(v)
    elif isinstance(o, list):
        for v in o: yield from leaves(v)
    else: yield o
chk("R1.keys_blank", all(v in ("", 0, None, False, True) for v in leaves(ck)))
sched_on = sum(t.get("enabled", True) for f in ISO.glob("workspace/projects/*/data/jsons/schedules.json")
               for t in json.loads(f.read_text()).get("tasks", []))
chk("R1.schedules_disabled", sched_on == 0, f"{sched_on} enabled")
chk("R1.shims_present", all((ISO / "_isolation/shims" / b).exists() for b in ("az", "ssh", "rsync", "scp", "sshpass")))

# R2 — every python source compiles
nfail = 0; ntot = 0
for d in ("server", "orchestrator", "workspace/shared/testing"):
    for p in (ISO / d).glob("*.py"):
        ntot += 1
        try: compile(p.read_text(encoding="utf-8"), str(p), "exec")
        except Exception: nfail += 1
M["R2.py_compile_ok_ratio"] = (ntot - nfail) / ntot
chk("R2.py_compile_all", nfail == 0, f"{nfail}/{ntot}")

# R3 — live isolated server returns REAL results (not 500, not empty)
def get(path, base="http://127.0.0.1:18000"):
    try:
        with urllib.request.urlopen(base + path, timeout=30) as r: return r.status, r.read()
    except urllib.error.HTTPError as e: return e.code, b""
    except Exception as e: return 0, b""
eps = ["/health", "/projects", "/agents/all", "/project-types", "/models", "/schedules", "/activity",
       "/ui/projects", "/ui/agents", "/audit/status", "/anchor/v1/projects", "/notifications"]
ok = 0; seen = 0
for e in eps:
    s, b = get(e)
    if s == 404: continue
    seen += 1
    good = s == 200 and len(b) > 2
    ok += good
    M[f"R3.ep{e}"] = s
s, b = get("/projects")
try:
    _j = json.loads(b); npj = len(_j["projects"] if isinstance(_j, dict) else _j)
except Exception: npj = 0
M["R3.endpoint_ok_ratio"] = ok / max(seen, 1); M["R3.projects_listed"] = npj
chk("R3.endpoints_real", ok == seen and npj > 0, f"{ok}/{seen}, projects={npj}")

# R4 — middleware door (single creation door): placement + owner-scope guard
import workspace_mw as mw
mw.create_owner("project", "rg-a", {"name": "rg-a"}); mw.create_owner("project", "rg-b", {"name": "rg-b"})
r1 = mw.put_file("project", "rg-a", "wrongsub", "run_deploy.sh", "echo hi", actor=("project", "rg-a"))
r2 = mw.put_file("project", "rg-a", "code", "tool.py", "print(1)", actor=("project", "rg-a"))
r3 = mw.put_file("project", "rg-b", "code", "intrude.py", "print(2)", actor=("project", "rg-a"))
r4 = mw.put_file("project", "rg-a", "", "notes.md", "x", actor=("project", "rg-a"))
chk("R4.wrong_subfolder_redirected", r1["corrected"] and r1["final_subfolder"] == "deploy", r1)
chk("R4.valid_write_respected", not r2["corrected"] and r2["final_subfolder"] == "code", r2)
chk("R4.cross_owner_redirected", r3["scope_redirected"] and r3["owner_id"] == "rg-a" and not (TR / "workspace/projects/rg-b/code/intrude.py").exists(), r3)
chk("R4.root_stray_redirected", r4["corrected"] and r4["final_subfolder"] == "docs", r4)
v = [x for x in mw.scan_violations() if "rg-" in str(x[0])]
chk("R4.no_violations_after_door", not v, v)

# R5 — audit detects what bypassed the door (seeded), across types
import workspace_audit as au
pa = TR / "workspace/projects/rg-a"; pb = TR / "workspace/projects/rg-b"
(pa / "junkdir").mkdir(exist_ok=True); (pa / "junkdir/stray.py").write_text("print('stray')")
(pb / "code").mkdir(exist_ok=True); (pb / "code/dupfn.sh").write_text("echo same\n"); (pa / "code/dupfn.sh").write_text("echo same\n")
(pb / "code/user.py").write_text("open('workspace/projects/rg-a/code/tool.py').read()\n")
iss = [i for i in au.scan() if "rg-" in json.dumps(i)]
types = {i["type"] for i in iss}
for t in ("misplaced", "duplicate", "foreign-ref"):
    chk(f"R5.audit_detects_{t}", t in types, sorted(types))
M["R5.issue_types_detected"] = sorted(types)

# R6 — deterministic router: same input -> same agents (run twice) + agreement with Odin's own logged routing
from dispatcher import Dispatcher
rows = [json.loads(l) for l in open(ISO / "_research/rescued/testset/raw_requests_anon.jsonl")]
a1 = [Dispatcher.classify(r["text"]) for r in rows]; a2 = [Dispatcher.classify(r["text"]) for r in rows]
M["R6.router_determinism"] = sum(x == y for x, y in zip(a1, a2)) / len(rows)
def norm(s): return re.sub(r"[^a-z]", "", (s or "").lower().split("&")[0])
lab = [(r.get("route_lead") or "", a) for r, a in zip(rows, a1) if r.get("route_lead")]
M["R6.router_agrees_with_logged_lead"] = sum(norm(l) in [norm(x) for x in a] for l, a in lab) / max(len(lab), 1)
M["R6.n_labelled"] = len(lab)
chk("R6.router_deterministic", M["R6.router_determinism"] == 1.0)

# R7 — anchor queue contract: enqueue -> pull -> process -> result -> webhook ACK (local receiver)
import anchor_queue as aq
got = []
class H(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("content-length", 0)); got.append(json.loads(self.rfile.read(n)))
        self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
    def log_message(self, *a): pass
srv = http.server.HTTPServer(("127.0.0.1", 18199), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
K = 20; ids = [aq.enqueue("rg-a", {"prompt": f"q{i}"}, webhook_url="http://127.0.0.1:18199/cb")["id"] for i in range(K)]
done = 0
while True:
    batch = aq.next_pending(5)
    if not batch: break
    for r in batch:
        aq.mark_processing(r["id"]); res = aq.submit_result(r["id"], {"answer": r["payload"]["prompt"]})
        done += bool(res.get("acked"))
srv.shutdown()
fin = sum((aq.get(i) or {}).get("status") == "finished" for i in ids)
M["R7.callback_success_ratio"] = done / K; M["R7.finished_ratio"] = fin / K
chk("R7.queue_contract", done == K and fin == K and len(got) == K, f"acked={done} fin={fin} cb={len(got)}")

# R8 — live-sync ordering: per-scope sequence is contiguous (gap detection works)
import scopes
c = scopes.create_chat("project:rg-a", "rg")
for i in range(30): scopes.add_message("project:rg-a", c["id"], "user", f"m{i}")
seqs = [m.get("seq") for m in scopes.all_messages("project:rg-a") if m.get("seq") is not None]
M["R8.seq_contiguous"] = bool(seqs) and seqs == list(range(seqs[0], seqs[0] + len(seqs)))
chk("R8.sync_sequence", M["R8.seq_contiguous"], seqs[:5])

# R9 — P2 owner-scope hook (unit): allow own slot, redirect non-canonical, block cross-project / shared / root
import subprocess
def hook(path, tool="Write", mode="enforce"):
    if not (TR / "server" / "scope_hook.py").exists(): return None
    pa = TR / "workspace/projects/rg-a/code"; pa.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, ODIN_SCOPE_HOOK=mode, ODIN_ROOT=str(TR), ODIN_ACTOR_PID="rg-a", ODIN_ACTOR_WORKDIR=str(pa))
    inp = json.dumps({"tool_name": tool, "tool_input": {"file_path": path} if tool == "Write" else {"command": path}, "cwd": str(pa)})
    return subprocess.run([sys.executable, str(TR / "server/scope_hook.py")], input=inp, text=True, capture_output=True, env=env).returncode
if (TR / "server" / "scope_hook.py").exists():
    chk("R9.hook_allows_own_slot", hook("m.py") == 0)
    chk("R9.hook_redirects_noncanonical", hook(str(TR / "workspace/projects/rg-a/misc/n.md")) == 2)
    chk("R9.hook_blocks_cross_project", hook(str(TR / "workspace/projects/rg-b/code/x.py")) == 2)
    chk("R9.hook_blocks_shared_raw_write", hook(str(TR / "workspace/shared/utils/x.sh")) == 2)
    chk("R9.hook_blocks_repo_root", hook(str(TR / "code/x.py")) == 2)
    chk("R9.hook_blocks_bash_redirect_cross", hook("echo x > ../../rg-b/code/y.py", tool="Bash") == 2)
    chk("R9.hook_door_own_actor_allowed", hook("python3 server/door_cli.py promote code/m.py", tool="Bash") == 0)
    chk("R9.hook_door_spoofed_actor_blocked", hook("ODIN_ACTOR_PID=rg-b python3 server/door_cli.py promote x", tool="Bash") == 2)
    chk("R9.hook_door_chained_raw_write_blocked", hook(f"python3 server/door_cli.py promote m.py && cp m.py {TR}/workspace/shared/utils/m.py", tool="Bash") == 2)
    chk("R9.hook_quoted_gt_is_not_a_write", hook("sed -E 's/=.*/=<hidden>/' ../../../shared/oth/.cred", tool="Bash") == 0)
    chk("R9.hook_heredoc_body_is_not_a_write", hook("python3 - <<'PY' 2>&1\nif 1 > 0: print(1)\nPY", tool="Bash") == 0)
    chk("R9.hook_watch_never_blocks", hook(str(TR / "workspace/projects/rg-b/code/x.py"), mode="watch") == 0)
# R10 — delete leaves no registry rows (project scopes included)
import projects as _pj, scopes as _sc
def _cnt():
    c = mw._db()
    if not c: return None
    cu = c.cursor(); cu.execute("SELECT count(*) FROM files"); n = cu.fetchone()[0]; c.close(); return n
_b = _cnt()
if _b is not None:
    au.heal(force=True); _b = _cnt()
    _pj.create_project("RG Delete", "regression delete check", "", [{"name": "Reporter", "role": "Reporter"}], identifier="rg-del")
    _c = _sc.create_chat("project:rg-del", "Run"); _sc.add_message("project:rg-del", _c["id"], "assistant", "x")
    au.heal(force=True); mw.delete_owner("project", "rg-del"); au.heal(force=True)
    M["R10.delete_leftover_rows"] = _cnt() - _b
    chk("R10.delete_clean", M["R10.delete_leftover_rows"] == 0, M["R10.delete_leftover_rows"])
# R11 — every catalogued/registered operational role has a resources section (Revealer pre-flight)
_missing = [r for r in ("EasyPost", "Fulfillment", "Email", "QA", "DevOps", "Fullstack") if not _pj.resources_block(r).strip()]
chk("R11.roles_have_resources", not _missing, _missing)

# ---- compare with baseline ----
out = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "metrics": M, "failures": F}
regress = []
if BASE.exists() and "--save-baseline" not in sys.argv:
    b = json.loads(BASE.read_text())["metrics"]
    for k, bv in b.items():
        nv = M.get(k)
        if isinstance(bv, bool) and bv and nv is not True: regress.append(k)
        elif isinstance(bv, (int, float)) and not isinstance(bv, bool) and isinstance(nv, (int, float)) and nv < bv - 1e-9 and not k.startswith("R3.ep"):
            regress.append(k)
out["regressions_vs_baseline"] = regress
RES.mkdir(parents=True, exist_ok=True)
(RES / f"regression_{int(time.time())}.json").write_text(json.dumps(out, indent=1, default=str))
if "--save-baseline" in sys.argv: BASE.write_text(json.dumps(out, indent=1, default=str))
print(json.dumps({"pass": sum(1 for k, v in M.items() if v is True), "fail": F, "regressions": regress,
                  "router_agree": M.get("R6.router_agrees_with_logged_lead"), "endpoint_ok": M.get("R3.endpoint_ok_ratio")}, default=str))
