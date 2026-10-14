"""Build the ISOLATED test clone of v2 (P5-2/P5-3 baselines, Phase 7 re-proof) — v2 itself stays production-true.
Clone: _v2/iso_root (gitignored). It mirrors how Odin-Consolidated was isolated (see tests/harness/_isolation/ISOLATION.md)
but uses its OWN ports, Postgres and DB names so it never collides with the Consolidated copy or the owner's real stack:
  paths  : AiAgentWorkSpace/Odin-Orchestrator-v2 -> .../Odin-Orchestrator-v2/_v2/iso_root ; ~/Desktop/{Odin,OdinTesting,
           VolatileWorkSpace} -> iso_root/_external/... (empty sandboxes)
  DBs    : odin_core -> odin_core_v2i, odin_anchor -> odin_anchor_v2i (private cluster, sockets /tmp/odv2_pg, ports 26432/26433)
  ports  : 8000->38000, 9100->39100, 9104->39104, 9300->39300, 8080->38080 (only in files that carry the service ports)
  secrets: .cred/.auth -> one comment line; connector_keys.json values blank; .env removed (.env.example kept); backup.key blank
  sched  : the 5 real scheduled tasks disabled (SOC agents never run twice); remote tools blocked by shims on PATH
Harness = tests/harness (Consolidated dialect) rewritten to the same names. usage: python3 _v2/iso/build_iso.py"""
import os, re, json, shutil, subprocess, pathlib, stat
V2 = pathlib.Path(__file__).resolve().parents[2]; ISO = V2 / "_v2" / "iso_root"; H = V2 / "tests" / "harness"
CONS = "/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Consolidated"; HOME = "/Users/mostafaadawy"
# v2 Phase 9: Odin-Consolidated was retired. Its full git history lives in v2 as a verified bundle, mirrored at
# _archive/Odin-Consolidated.git (all 85 tags), and the two seed dumps in _archive/iso_seed. CONS stays only as the
# text that harness files are rewritten FROM; nothing is read from that folder any more.
CONS_GIT = "/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2/_archive/Odin-Consolidated.git"
SEED = "/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2/_archive/iso_seed"
assert V2.name == "Odin-Orchestrator-v2", V2
EXCL = {".git", ".venv", "node_modules", "__pycache__", "_v2", "tests", "research", "docs"}
EXCL_REL = {"desktop/release", "odin_app/build", "odin_app/.dart_tool", "odin_app/ios/Pods", "workspace/logs/agent_term", "desktop/dist"}
def rm_tree(p):
    if p.exists():
        for dp, dns, fns in os.walk(p):
            for n in dns + fns:
                try: os.chmod(os.path.join(dp, n), 0o755)
                except Exception: pass
        shutil.rmtree(p)
rm_tree(ISO); ISO.mkdir(parents=True)
def copy_tree(src, dst, rel=""):
    for e in os.scandir(src):
        r = (rel + "/" + e.name).lstrip("/")
        if e.name in EXCL and rel == "" or e.name in {"__pycache__", "node_modules", ".venv"} or r in EXCL_REL: continue
        if e.is_symlink(): continue
        d = dst / e.name
        if e.is_dir(): d.mkdir(exist_ok=True); copy_tree(e.path, d, r)
        else: shutil.copy2(e.path, d)
copy_tree(V2, ISO)
os.symlink(V2 / ".venv", ISO / ".venv"); os.symlink(V2 / "research", ISO / "research")   # read-only use (models, paper); never rewritten
shutil.copytree(H, ISO, dirs_exist_ok=True)          # _consolidation, _isolation, _research/{exp,regression,testlibs}
for d in ("_external/Odin", "_external/OdinTesting", "_external/VolatileWorkSpace", "_external/LaunchAgents",
          "_research/tmp/pg", "_research/runs", "_consolidation/results", "workspace/logs/agent_term", "data"):
    (ISO / d).mkdir(parents=True, exist_ok=True)
# harness data the regression needs (rescued anonymised request set)
if (V2 / "research/consolidation/rescued").exists():
    shutil.copytree(V2 / "research/consolidation/rescued", ISO / "_research/rescued", dirs_exist_ok=True)
# the throwaway Postgres restore dumps (same seed data the Consolidated runs used)
for f in ("odin_core.sql", "odin_anchor_schema.sql"):
    src = pathlib.Path(SEED) / f
    if src.exists(): shutil.copy2(src, ISO / "_research/tmp/pg" / f)
ISOS = str(ISO)
PORTS = [("8000", "38000"), ("9100", "39100"), ("9104", "39104"), ("9300", "39300"), ("8080", "38080")]
port_files = set(json.loads((H / "_isolation/db_port_remap_files.json").read_text()))
pf2 = V2 / "_v2" / "port_files.json"
if pf2.exists(): port_files |= set(json.loads(pf2.read_text()))
HARNESS = ("_consolidation/", "_isolation/", "_research/")
log = {"paths": 0, "db": 0, "ports": [], "secrets": [], "harness": 0}
def tx_product(rel, s):
    o = s
    s = re.sub(r"AiAgentWorkSpace/Odin-Orchestrator-v2(?!/_v2/iso_root)", "AiAgentWorkSpace/Odin-Orchestrator-v2/_v2/iso_root", s)
    for name in ("OdinTesting", "VolatileWorkSpace", "Odin"):
        s = re.sub(r"(" + re.escape(HOME) + r"|~)/Desktop/" + name + r"(?=[/\"'`\s,;:)\]}]|$)", ISOS + "/_external/" + name, s, flags=re.M)
    s = re.sub(r"([\"']AiAgentWorkSpace[\"'],\s*)([\"'])Odin-Orchestrator-v2([\"'])(?!,\s*[\"']_v2)", r"\1\2Odin-Orchestrator-v2\3, \2_v2\3, \2iso_root\3", s)
    s = re.sub(r"(pkill[^\n]*?)Odin-Orchestrator-v2/desktop", r"\1Odin-Orchestrator-v2/_v2/iso_root/desktop", s)
    if s != o: log["paths"] += 1
    s2 = re.sub(r"\bodin_core\b(?!_)", "odin_core_v2i", s); s2 = re.sub(r"\bodin_anchor\b(?!_)", "odin_anchor_v2i", s2)
    if s2 != s: log["db"] += 1; s = s2
    if rel in port_files:
        s3 = s
        for a, b in PORTS: s3 = re.sub(r"(?<![\d.])" + a + r"(?!\d)", b, s3)
        if s3 != s: log["ports"].append(rel); s = s3
    return s
def tx_harness(s):
    s = s.replace(CONS, ISOS)
    s = s.replace("/tmp/odc_pg", "/tmp/odv2_pg").replace("odin_core_con", "odin_core_v2i").replace("odin_anchor_con", "odin_anchor_v2i")
    s = re.sub(r"(?<!\d)25432(?!\d)", "26432", s); s = re.sub(r"(?<!\d)25433(?!\d)", "26433", s)
    for a, b in (("28000", "38000"), ("29100", "39100"), ("29104", "39104"), ("29300", "39300"), ("28080", "38080")):
        s = re.sub(r"(?<!\d)" + a + r"(?!\d)", b, s)
    # PRE-FIX trees = the exact Consolidated evidence trees (4945000 = clean pre-fix workspace matching the DB dump,
    # f43-start = pre-F-43 server), rebuilt in iso dialect as cons-* commits (see below). Same semantics as Consolidated.
    s = re.sub(r"git archive 4945000\b", "git archive cons-4945000", s)
    s = s.replace("git archive f43-start server", "git archive cons-f43-start server")
    # fix2_unit read v1's recorded CTO reviews READ-ONLY (../Odin-Orchestrator/workspace from Consolidated); in v2 the
    # same records live in the clone's own workspace (copied from v2 = v1 records + later ones)
    s = s.replace("fix2_unit.py server ../Odin-Orchestrator/workspace", "fix2_unit.py server workspace")
    # stepE check 0 reads the PRE-F-14 key values (never printed) from the Consolidated tag, read-only
    s = s.replace("'stepE-start:desktop/src/App.jsx'], cwd=iso,", "'stepE-start:desktop/src/App.jsx'], cwd=" + repr(CONS_GIT) + ",")
    s = s.replace("AiAgentWorkSpace/Odin-Orchestrator|", "AiAgentWorkSpace/Odin-Orchestrator(?!-v2/_v2/iso_root)|")   # v2: the iso clone lives under Odin-Orchestrator-v2 -> still flags v1 and real-v2 paths
    s = re.sub(r"\$\{([A-Z0-9_]+)_VERS:-before after\}", r"${\1_VERS:-after}", s)     # v2: AFTER runs only (before = Consolidated evidence)
    return s
for dp, dns, fns in os.walk(ISO):
    dns[:] = [d for d in dns if d not in {".venv", ".git"}]
    for fn in fns:
        p = pathlib.Path(dp) / fn; rel = p.relative_to(ISO).as_posix()
        if p.is_symlink(): continue
        # secrets -> placeholders
        if fn in (".cred", ".auth") or fn.endswith((".cred", ".auth")) or fn.startswith((".cred.", ".auth.")):
            p.write_text("# placeholder (v2 isolated test clone: no credentials)\n"); log["secrets"].append(rel); continue
        if fn == "backup.key": p.write_text(""); log["secrets"].append(rel); continue
        if (fn == ".env" or fn.startswith(".env.")) and not fn.endswith((".example", ".sample", ".template")):
            p.unlink(); log["secrets"].append(rel); continue
        if fn == "connector_keys.json":
            def blank(x): return {k: blank(v) for k, v in x.items()} if isinstance(x, dict) else [blank(v) for v in x] if isinstance(x, list) else ("" if isinstance(x, str) else x)
            try: p.write_text(json.dumps(blank(json.loads(p.read_text())), indent=1)); log["secrets"].append(rel)
            except Exception: p.write_text("{}")
            continue
        try: b = p.read_bytes()
        except Exception: continue
        if b"\0" in b[:4096] or len(b) > 30_000_000: continue
        s = b.decode("utf-8", errors="surrogateescape")
        t = tx_harness(s) if rel.startswith(HARNESS) else tx_product(rel, s)
        if rel.startswith(HARNESS) and t != s: log["harness"] += 1
        if t != s: p.write_bytes(t.encode("utf-8", errors="surrogateescape"))
# Consolidated result files the harness READS as inputs (recorded live runs, reference data) -> iso results dir
for f in ("S1_r4.json", "F07_live.json", "claude_calls.json", "f43_live.json", "fix1_post.json", "stepC_data.json",
          "v1_lost_custom_rules.json", "secret_hist_log.json"):
    src = V2 / "research/consolidation/_consolidation/results" / f
    if src.exists(): (ISO / "_consolidation/results" / f).write_text(tx_harness(src.read_text(errors="surrogateescape")), errors="surrogateescape")
# disable the real scheduled tasks
sched = json.loads((H / "_isolation/schedules_original_enabled.json").read_text())
for key in sched:
    f, tid = key.split("#"); p = ISO / f
    if p.exists():
        d = json.loads(p.read_text()); items = d if isinstance(d, list) else d.get("schedules") or d.get("tasks") or []
        for it in items:
            if isinstance(it, dict) and str(it.get("id")) == tid: it["enabled"] = False
        p.write_text(json.dumps(d, indent=2))
for sh in (ISO / "_isolation/shims").iterdir(): sh.chmod(0o755)
for f in list((ISO / "_consolidation").glob("*.sh")) + list((ISO / "_isolation").glob("*.sh")) + list((ISO / "_research/exp").glob("*.sh")): f.chmod(0o755)
# a private git so the harness can 'git archive' pristine trees; every tag the harness names points at this base
env = dict(os.environ, GIT_AUTHOR_NAME="iso", GIT_AUTHOR_EMAIL="iso@local", GIT_COMMITTER_NAME="iso", GIT_COMMITTER_EMAIL="iso@local")
run = lambda *a: subprocess.run(a, cwd=ISO, env=env, check=True, capture_output=True, text=True)
(ISO / ".gitignore").write_text(".venv\n_research/tmp/\n_research/runs/\n_consolidation/results/\n__pycache__/\n"
                                 "# F-14 (same as v2): generated at run time, carry the anchor key\n/anchor_prod.js\n/anchor_seed.js\nworkspace/anchor-layer/anchor_seed.js\n")
run("git", "init", "-q"); run("git", "add", "-A"); run("git", "commit", "-q", "-m", "iso-base: isolated clone of v2")
tags = set(re.findall(r"git archive (?:\$\{[A-Z0-9_]+:-)?([A-Za-z0-9_.-]+-(?:start|done))", "\n".join(p.read_text(errors="ignore") for p in (ISO / "_consolidation").glob("*.sh"))))
for t in sorted(tags | {"iso-base", "phase3-start", "post3-done"}): run("git", "tag", "-f", t)
# cons-* : Consolidated PRE-FIX evidence trees, read with `git archive` (read-only) and rewritten to the iso dialect
import tempfile, tarfile, io
SECRET_LIT = re.compile(r"od_anchor_[A-Za-z0-9_-]{20,}")
def cons_commit(tag, ref, paths):
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="cons_", dir=ISO / "_research/tmp"))
    ar = subprocess.run(["git", "--no-optional-locks", "archive", ref] + paths, cwd=CONS_GIT, capture_output=True, check=True).stdout
    tarfile.open(fileobj=io.BytesIO(ar)).extractall(tmp)
    for dp, dns, fns in os.walk(tmp):
        for fn in fns:
            q = pathlib.Path(dp) / fn
            if fn in (".cred", ".auth") or fn.endswith((".cred", ".auth")) or fn.startswith((".cred.", ".auth.")): q.write_text("# placeholder (v2 isolated test clone: no credentials)\n"); continue
            if fn == "backup.key": q.write_text(""); continue
            if (fn == ".env" or fn.startswith(".env.")) and not fn.endswith((".example", ".sample", ".template")): q.unlink(); continue
            b = q.read_bytes()
            if b"\0" in b[:4096]: continue
            t = b.decode("utf-8", errors="surrogateescape")
            t2 = SECRET_LIT.sub("od_anchor_REDACTED", tx_harness(t))
            if t2 != t: q.write_bytes(t2.encode("utf-8", errors="surrogateescape"))
    ienv = dict(env, GIT_INDEX_FILE=str(tmp) + ".idx", GIT_WORK_TREE=str(tmp))
    subprocess.run(["git", "add", "-A", "-f", "."], cwd=tmp, env=ienv | {"GIT_DIR": str(ISO / ".git")}, check=True, capture_output=True)
    tree = subprocess.run(["git", "write-tree"], cwd=tmp, env=ienv | {"GIT_DIR": str(ISO / ".git")}, check=True, capture_output=True, text=True).stdout.strip()
    c = subprocess.run(["git", "commit-tree", tree, "-m", f"{tag}: Consolidated {ref} {paths} (iso dialect)"], cwd=ISO, env=env, check=True, capture_output=True, text=True).stdout.strip()
    run("git", "tag", "-f", tag, c); rm_tree(tmp); pathlib.Path(str(tmp) + ".idx").unlink(missing_ok=True)
cons_commit("cons-4945000", "4945000", ["workspace"])
cons_commit("cons-f43-start", "f43-start", ["server"])
log["ports"] = sorted(log["ports"]); log["secrets"] = sorted(log["secrets"])
(V2 / "_v2" / "iso" / "last_build.json").write_text(json.dumps({k: (v if isinstance(v, int) else len(v)) for k, v in log.items()} | {"port_files": log["ports"], "secret_files": log["secrets"]}, indent=1))
print("ISO built:", ISO, {k: (v if isinstance(v, int) else len(v)) for k, v in log.items()})
