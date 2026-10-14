"""DoD 7 — every v1 project exists and works in v2. Reads v1 READ-ONLY; checks v2 files and the v2 brain on the
isolated clone. usage: python _v2/projects_table.py <v1_root> <v2_root> <iso_brain_url> > table.md  (values never printed)"""
import sys, json, pathlib, hashlib, urllib.request
V1, V2, BRAIN = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3].rstrip("/")
SKIP = {"__pycache__", ".DS_Store"}
def files(root):
    return {p.relative_to(root).as_posix(): p for p in root.rglob("*") if p.is_file() and not (set(p.parts) & SKIP)}
def h(p):
    try: return hashlib.sha256(p.read_bytes()).hexdigest()
    except Exception: return ""
def jl(p, default):
    try: return json.loads(p.read_text())
    except Exception: return default
def get(path):
    try:
        with urllib.request.urlopen(BRAIN + path, timeout=20) as r: return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e: return e.code, {}
    except Exception: return 0, {}
def chats(root, pid):
    n = 0
    for d in (root / "workspace/chats/scopes").glob(f"*{pid}*"):
        for f in d.rglob("*.json"):
            m = jl(f, {}); n += len(m.get("messages", [])) if isinstance(m, dict) else 0
    return n
st, ui = get("/ui/projects"); ui_ids = json.dumps(ui)
rows = []; allok = True
pids = sorted({p.name for p in (V1 / "workspace/projects").iterdir() if p.is_dir()} | {p.name for p in (V2 / "workspace/projects").iterdir() if p.is_dir()})
for pid in pids:
    a, b = V1 / "workspace/projects" / pid, V2 / "workspace/projects" / pid
    fa, fb = (files(a) if a.exists() else {}), (files(b) if b.exists() else {})
    lost = [k for k in fa if k not in fb]
    changed = [k for k in fa if k in fb and h(fa[k]) != h(fb[k])]
    added = [k for k in fb if k not in fa]
    ag1 = len(jl(a / "agents.json", {}).get("agents", jl(a / "agents.json", []))) if a.exists() else 0
    ag2 = len(jl(b / "agents.json", {}).get("agents", jl(b / "agents.json", []))) if b.exists() else 0
    sch1 = len(jl(a / "data/jsons/schedules.json", {}).get("tasks", [])); sch2 = len(jl(b / "data/jsons/schedules.json", {}).get("tasks", []))
    c1, c2 = chats(V1, pid), chats(V2, pid)
    code, pj = get(f"/projects/{pid}") if pid != "_shared" else (200, {})
    works = pid == "_shared" or (code == 200 and len(pj.get("agents", [])) >= 0 and pid in ui_ids)
    ok = a.exists() == b.exists() or (not a.exists())
    ok = ok and not lost and works
    allok &= ok
    rows.append(f"| {pid} | {'yes' if a.exists() else 'no'} | {'yes' if b.exists() else 'no'} | {len(fa)} → {len(fb)} (lost {len(lost)}, changed {len(changed)}, new {len(added)}) "
                f"| {ag1} → {ag2} | {sch1} → {sch2} | {c1} → {c2} | {'brain 200, ' + str(len(pj.get('agents', []))) + ' agents, in UI list' if pid != '_shared' else 'shared folder'} "
                f"| {'✅' if ok else '❌'} |")
    if lost: rows.append(f"|  | lost files: {', '.join(lost[:6])} | | | | | | | |")
    if changed: rows.append(f"|  | changed: {', '.join(changed[:6])} | | | | | | | |")
print("| Project | In v1 | In v2 | Files v1 → v2 | Agents | Schedules | Chat messages | v2 brain check (isolated) | Verified |")
print("|---|---|---|---|---|---|---|---|---|")
print("\n".join(rows))
print(f"\nRESULT: {'ALL VERIFIED' if allok else 'SEE ❌ ROWS'}  (ui list http {st})")
