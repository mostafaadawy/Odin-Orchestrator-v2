"""P5-3: replay the APPROVED product changes made in Odin-Consolidated onto v2, one Consolidated commit at a time.
Each changed product file is merged 3-way:  ours = v2 file, base = R(file at commit^), theirs = R(file at commit),
where R reverses the isolation dialect (Isolated/Consolidated paths, *_iso/*_con DB names, 18xxx/28xxx/29xxx ports,
_external sandboxes) back to the production names. Only lines the commit really changed reach v2; v2's own content
(v1's newer data) is kept. Conflicts are NOT forced: the file is left as v2 had it and listed for review.
Harness/test/research files are not product code and are not replayed (tests live in tests/harness).
usage: port_from_consolidated.py <first_commit> <last_commit> [--commit]   (git commit per replayed commit with --commit)"""
import os, re, sys, json, subprocess, pathlib, tempfile
V2 = pathlib.Path(__file__).resolve().parents[1]
CONS = pathlib.Path("/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Consolidated")
H = "/Users/mostafaadawy/Desktop"; W = H + "/AiAgentWorkSpace"
INCLUDE = ("server/", "orchestrator/", "desktop/", "odin_app/", "shells/", "dashboard/", "voice/", "workspace/agents/",
           "workspace/shared/", "workspace/docs/", "workspace/anchor-layer/", "workspace/projects/", ".gitignore", "CLAUDE.md", "README.md")
SKIP = (re.compile(r"^workspace/shared/testing/(dup_test_r\d+|project_test)\.py$"), re.compile(r"^desktop/dist/"),
        re.compile(r"\.bak"), re.compile(r"/__pycache__/"))
def g(*a, cwd=CONS, check=True):
    return subprocess.run(["git", "--no-optional-locks", *a], cwd=cwd, capture_output=True, text=True, check=check)
def show(c, path):
    r = subprocess.run(["git", "--no-optional-locks", "show", f"{c}:{path}"], cwd=CONS, capture_output=True)
    return r.stdout.decode("utf-8", errors="surrogateescape") if r.returncode == 0 else None
PORTS = [("18000|28000", "8000"), ("19100|29100", "9100"), ("19104|29104", "9104"), ("19300|29300", "9300"), ("18080|28080", "8080")]
def R(s):
    if s is None: return None
    for name, real in (("OdinTesting", H + "/OdinTesting"), ("VolatileWorkSpace", H + "/VolatileWorkSpace"),
                       ("RedBerry-Continuous-SOC", W + "/RedBerry-Continuous-SOC"), ("LaunchAgents", "/Users/mostafaadawy/Library/LaunchAgents"),
                       ("Odin", H + "/Odin")):
        s = re.sub(re.escape(W) + r"/Odin-(?:Isolated|Consolidated)/_external/" + name + r"(?=[/\"'`\s,;:)\]}]|$)", real, s, flags=re.M)
    s = re.sub(r"AiAgentWorkSpace/Odin-(?:Isolated|Consolidated)(?=[/\"'`\s,;:)\]}]|$)", "AiAgentWorkSpace/Odin-Orchestrator-v2", s, flags=re.M)
    s = re.sub(r"([\"']AiAgentWorkSpace[\"'],\s*[\"'])Odin-(?:Isolated|Consolidated)([\"'])", r"\1Odin-Orchestrator-v2\2", s)
    s = re.sub(r"(pkill[^\n]*?)Odin-(?:Isolated|Consolidated)/desktop", r"\1Odin-Orchestrator-v2/desktop", s)
    s = re.sub(r"\bodin_core_(?:iso|con)\b", "odin_core", s); s = re.sub(r"\bodin_anchor_(?:iso|con)\b", "odin_anchor", s)
    for a, b in PORTS: s = re.sub(r"(?<![\d.])(?:" + a + r")(?!\d)", b, s)
    return s
def product(path):
    return path.startswith(INCLUDE) and not any(rx.search(path) for rx in SKIP)
first, last = sys.argv[1], sys.argv[2]; COMMIT = "--commit" in sys.argv
SKIP_COMMITS = {"a4de1ec"}   # scenario-verification run: workspace side effects of test runs, not product changes
commits = [c for c in g("rev-list", "--reverse", f"{first}^..{last}").stdout.split() if c[:7] not in SKIP_COMMITS]
pf = V2 / "_v2" / "port_files.json"; port_files = set(json.loads(pf.read_text())) if pf.exists() else set()
report = {"commits": []}
for c in commits:
    subj = g("log", "-1", "--format=%s", c).stdout.strip(); parent = f"{c}^"
    rows = [l.split("\t") for l in g("diff", "--name-status", "-M100%", parent, c).stdout.splitlines() if l.strip()]
    rec = {"commit": c, "subject": subj, "applied": [], "deleted_from_git": [], "conflicts": [], "skipped_nonproduct": 0, "skipped_test_project": []}
    for row in rows:
        st, paths = row[0], row[1:]
        if st.startswith("R"):
            old, new = paths; rows.append(["D", old]); rows.append(["A", new]); continue
        path = paths[0]
        if not product(path): rec["skipped_nonproduct"] += 1; continue
        ours_p = V2 / path
        if st == "A" and path.startswith("workspace/projects/"):
            rec["skipped_test_project"].append(path); continue            # files/projects created by Consolidated TEST runs
        base, theirs = R(show(parent, path)), R(show(c, path))
        if st == "D":
            if path in ("anchor_prod.js", "anchor_seed.js", "workspace/anchor-layer/anchor_seed.js") or ours_p.exists():
                rec["deleted_from_git"].append(path)                      # untracked (gitignored) like in Consolidated; file kept on disk
            continue
        if theirs is None: continue
        if base is None or not ours_p.exists():
            ours_p.parent.mkdir(parents=True, exist_ok=True); ours_p.write_text(theirs, errors="surrogateescape")
            rec["applied"].append(path)
        else:
            ours = ours_p.read_text(errors="surrogateescape")
            if ours == theirs: continue
            with tempfile.TemporaryDirectory() as td:
                pb, pt = pathlib.Path(td, "b"), pathlib.Path(td, "t"); pb.write_text(base, errors="surrogateescape"); pt.write_text(theirs, errors="surrogateescape")
                po = pathlib.Path(td, "o"); po.write_text(ours, errors="surrogateescape")
                r = subprocess.run(["git", "merge-file", "-p", str(po), str(pb), str(pt)], capture_output=True)
                if r.returncode == 0:
                    ours_p.write_bytes(r.stdout); rec["applied"].append(path)
                else:
                    rec["conflicts"].append({"path": path, "n": r.returncode})
        orig_theirs = show(c, path) or ""
        if any(re.search(r"(?<![\d.])(?:" + a + r")(?!\d)", orig_theirs) for a, _ in PORTS): port_files.add(path)
    if rec["deleted_from_git"] and COMMIT:
        subprocess.run(["git", "rm", "-q", "--cached", "--ignore-unmatch", *rec["deleted_from_git"]], cwd=V2)
    report["commits"].append(rec)
    if COMMIT and (rec["applied"] or rec["deleted_from_git"]):
        subprocess.run(["git", "add", "-A", "--", *[p for p in rec["applied"]]], cwd=V2, check=True)
        msg = (f"port {c[:7]} from Odin-Consolidated: {subj}\n\nApplied {len(rec['applied'])} product file(s) 3-way (isolation dialect reversed). "
               f"Conflicts left for review: {len(rec['conflicts'])}.\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
               "Claude-Session: https://claude.ai/code/session_01Eo7cH6GLnFTNPsW8AjYoQ2")
        subprocess.run(["git", "-c", "user.name=Odin v2", "commit", "-q", "-m", msg], cwd=V2)
    print(f"{c[:7]} applied={len(rec['applied'])} conflicts={len(rec['conflicts'])} untracked={len(rec['deleted_from_git'])} test_projects_skipped={len(rec['skipped_test_project'])}  {subj[:70]}", flush=True)
pf.write_text(json.dumps(sorted(port_files), indent=1))
out = V2 / "_v2" / f"port_report_{first[:7]}_{last[:7]}.json"; out.write_text(json.dumps(report, indent=1))
print("REPORT", out, "conflicts total:", sum(len(r["conflicts"]) for r in report["commits"]))
