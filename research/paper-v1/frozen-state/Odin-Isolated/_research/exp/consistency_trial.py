"""ONE trial of the consistency-at-scale experiment, run against Odin's REAL middleware + audit code in a throwaway root.
usage: consistency_trial.py <root> <N projects> <door|bypass> <seed>
N projects x 3 agents write concurrently. The write mix follows the error classes seen in Odin's own history
(misplaced, root-stray, cross-owner, duplicate utility, foreign reference). Prints one JSON line."""
import sys, os, json, time, random, threading, pathlib
root, N, cond, seed = pathlib.Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3], int(sys.argv[4])
if "/_research/tmp/" not in str(pathlib.Path(sys.argv[1]).resolve()) or not (pathlib.Path(sys.argv[1]) / "server").is_dir():
    sys.exit("REFUSED: root must be a throwaway root under _research/tmp with server/ (safety guard)")
sys.path[:0] = [str(root / "server"), str(pathlib.Path(__file__).parent)]
from common import PidMeter
import workspace_mw as mw, workspace_audit as au
WS = root / "workspace"; rnd = random.Random(seed)
PIDS = [f"cx{seed}-n{N}-p{i}" for i in range(N)]
for p in PIDS: mw.create_owner("project", p, {"name": p})
AGENTS = ["dev", "qa", "ops"]; W = 12
MIX = [("valid", .60), ("wrong_sub", .15), ("root_file", .05), ("cross_owner", .10), ("dup_util", .05), ("foreign_ref", .05)]
def pick():
    x = rnd.random(); a = 0
    for k, w in MIX:
        a += w
        if x < a: return k
    return "valid"
plan = []   # (actor_pid, agent, kind, target_pid, subfolder, name, content)
for p in PIDS:
    for ag in AGENTS:
        for j in range(W):
            k = pick(); tgt = p; sub = rnd.choice(["code", "docs", "data/jsons", "tests"]); name = f"{p.split('-')[-1]}_{ag}_{j}.py"
            body = f"# author: {p}/{ag}\nprint('{p}-{ag}-{j}')\n"
            if k == "wrong_sub": sub = rnd.choice(["misc", "tmp", "stuff", "out"])
            elif k == "root_file": sub = ""; name = f"{p.split('-')[-1]}_{ag}_{j}_notes.md"
            elif k == "cross_owner" and N > 1: tgt = rnd.choice([q for q in PIDS if q != p]); sub = "code"
            elif k == "cross_owner": k = "valid"
            elif k == "dup_util": sub = "code"; name = f"util_{ag}_{j}.sh"; body = "# shared helper\nretry(){ for i in 1 2 3; do \"$@\" && return 0; sleep 1; done; return 1; }\n"
            elif k == "foreign_ref" and N > 1:
                o = rnd.choice([q for q in PIDS if q != p]); sub = "code"
                body = f"# author: {p}/{ag}\nexec(open('workspace/projects/{o}/code/base_{o}.py').read())\n"
            elif k == "foreign_ref": k = "valid"
            plan.append((p, ag, k, tgt, sub, name, body))
for o in PIDS:   # each project owns one base file other projects may (wrongly) reference
    if cond == "door": mw.put_file("project", o, "code", f"base_{o}.py", "X=1\n", actor=("project", o))
    else: (WS / "projects" / o / "code").mkdir(parents=True, exist_ok=True); (WS / "projects" / o / "code" / f"base_{o}.py").write_text("X=1\n")
lat = []; lock = threading.Lock()
def work(items):
    for (p, ag, k, tgt, sub, name, body) in items:
        t0 = time.perf_counter()
        if cond == "door":
            mw.put_file("project", tgt, sub, name, body, actor=("project", p))
        else:   # BYPASS: an agent writing straight to the path it asked for (no middleware)
            d = WS / "projects" / tgt / sub if sub else WS / "projects" / tgt
            d.mkdir(parents=True, exist_ok=True); (d / name).write_text(body)
        with lock: lat.append(time.perf_counter() - t0)
groups = {}
for it in plan: groups.setdefault((it[0], it[1]), []).append(it)
with PidMeter() as pm:
    th = [threading.Thread(target=work, args=(v,)) for v in groups.values()]
    [t.start() for t in th]; [t.join() for t in th]
def mine(i): return any(p in json.dumps(i) for p in PIDS)
def landed():
    wrong = sum(1 for path, _ in mw.scan_violations() if any(p in str(path) for p in PIDS))
    cross = 0; lost = 0
    for p in PIDS:
        for f in (WS / "projects" / p).rglob("*"):
            if f.is_file() and f.suffix in (".py", ".md"):
                head = f.read_text(errors="ignore")[:200]
                if "# author: " in head and not head.split("# author: ")[1].startswith(p + "/"): cross += 1
    return wrong, cross
def lockstep():
    try:
        c = mw._db(); cu = c.cursor(); cu.execute("SELECT path FROM files"); rows = {r[0] for r in cu.fetchall()}; c.close()
        disk = [str(f.relative_to(root)) for p in PIDS for f in (WS / "projects" / p).rglob("*") if f.is_file() and au._interesting(f)]
        return sum(d in rows for d in disk) / max(len(disk), 1)
    except Exception:
        return None
lock_before = lockstep()
w0, c0 = landed()
iss0 = [i for i in au.scan() if mine(i)]
types0 = {}
for i in iss0: types0[i["type"]] = types0.get(i["type"], 0) + 1
with PidMeter() as ph:
    h = au.heal(force=True)
w1, c1 = landed()
iss1 = [i for i in au.scan() if mine(i)]
types1 = {}
for i in iss1: types1[i["type"]] = types1.get(i["type"], 0) + 1
# DB lockstep: files on disk under these projects vs rows in odin_core_iso.files
lock_ratio = None
try:
    c = mw._db(); cu = c.cursor(); cu.execute("SELECT path FROM files"); rows = {r[0] for r in cu.fetchall()}; c.close()
    disk = [str(f.relative_to(root)) for p in PIDS for f in (WS / "projects" / p).rglob("*") if f.is_file() and au._interesting(f)]
    lock_ratio = sum(d in rows for d in disk) / max(len(disk), 1)
except Exception as e:
    lock_ratio = None
nw = len(plan); kinds = {}
for it in plan: kinds[it[2]] = kinds.get(it[2], 0) + 1
lat.sort()
print(json.dumps({"N": N, "cond": cond, "seed": seed, "writes": nw, "agents": N * len(AGENTS), "kinds": kinds,
  "wrong_folder_landed": w0, "cross_project_landed": c0, "audit_issues": len(iss0), "audit_types": types0,
  "after_heal": {"wrong_folder": w1, "cross_project": c1, "audit_issues": len(iss1), "types": types1},
  "violation_rate": (w0 + c0) / nw, "residual_rate_after_heal": (w1 + c1) / nw,
  "db_lockstep_before_heal": lock_before, "db_lockstep_after_heal": lockstep(), "lat_p50_ms": lat[len(lat)//2]*1000, "lat_p95_ms": lat[int(len(lat)*.95)]*1000,
  "work": pm.result(), "heal": ph.result()}))
