#!/usr/bin/env python3
"""v1 RESTORE PATCH (prepared 2026-10-11; for the OWNER to run — nothing here runs by itself).
Merges back into live v1 what the 2026-07-19 G10 rewrite removed from shared agent files: the 20 custom rules and
the 'Integrated foundational charter' / '[archived] merged from duplicate agent' sections, taken from v1's own
git commit 06a6ddb (2026-07-18). MERGE ONLY: no existing line is changed or deleted (a lone '- (none yet)'
placeholder is dropped where a rule is added). Touches ONLY workspace/agents/*/capability.md. No git commit.

  python3 v1_restore.py            DRY RUN (default): per-agent summary + full diff in dry_run_diff.txt; writes nothing in v1
  python3 v1_restore.py --apply    backs up every file it will change (backups/<time>/), then writes; prints the undo id
  python3 v1_restore.py --undo     restores the files from the LAST apply's backup — only files not edited since

Optional: --v1 <path to Odin-Orchestrator>  (default: ~/Desktop/AiAgentWorkSpace/Odin-Orchestrator)"""
import sys, os, json, pathlib, subprocess, hashlib, difflib, datetime, shutil
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import f42_merge
SRC = "06a6ddb"
args = sys.argv[1:]
V1 = pathlib.Path(args[args.index("--v1") + 1]).expanduser() if "--v1" in args else pathlib.Path("~/Desktop/AiAgentWorkSpace/Odin-Orchestrator").expanduser()
sha = lambda s: hashlib.sha256(s.encode()).hexdigest()

def plan():
    out = {}
    for p in sorted((V1 / "workspace/agents").glob("*/capability.md")):
        r = subprocess.run(["git", "--no-optional-locks", "-C", str(V1), "show", f"{SRC}:workspace/agents/{p.parent.name}/capability.md"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            continue
        cur = p.read_text(encoding="utf-8")
        new, rep = f42_merge.merge(r.stdout, cur)
        if new != cur:
            out[p.parent.name] = (p, cur, new, rep)
    return out

def summary(pl):
    for a, (p, cur, new, rep) in pl.items():
        secs = ", ".join(f"{s['section']} ({s['lines']} lines)" for s in rep["sections_added"]) or "-"
        print(f"{a}: +{len(rep['rules_added'])} rule(s); sections added: {secs}")
        for r in rep["rules_added"]:
            print(f"    rule: {r}")
    print(f"\n{len(pl)} file(s) would change; total rules {sum(len(v[3]['rules_added']) for v in pl.values())} in Custom rules "
          f"(+ rules inside restored sections).")

if "--undo" in args:
    runs = sorted((HERE / "backups").glob("*/manifest.json"))
    if not runs:
        sys.exit("nothing to undo (no apply found)")
    man = json.loads(runs[-1].read_text())
    if man.get("undone"):
        sys.exit(f"the last apply ({runs[-1].parent.name}) was already undone")
    done, skipped = [], []
    for f in man["files"]:
        p = pathlib.Path(f["path"])
        if not p.exists() or sha(p.read_text(encoding="utf-8")) != f["sha_after"]:
            skipped.append(f"{f['agent']}: edited after the apply — left as is"); continue
        p.write_text((runs[-1].parent / f"{f['agent']}.md").read_text(encoding="utf-8"), encoding="utf-8")
        done.append(f["agent"])
    man["undone"] = datetime.datetime.now().isoformat(); runs[-1].write_text(json.dumps(man, indent=1))
    print(f"UNDO of {runs[-1].parent.name}: restored {len(done)} file(s): {', '.join(done) or '-'}")
    for s in skipped: print("  skipped:", s)
    sys.exit(0)

pl = plan()
if "--apply" not in args:
    summary(pl)
    diff = []
    for a, (p, cur, new, rep) in pl.items():
        diff += difflib.unified_diff(cur.splitlines(True), new.splitlines(True), f"a/{a}/capability.md", f"b/{a}/capability.md")
    (HERE / "dry_run_diff.txt").write_text("".join(diff), encoding="utf-8")
    print(f"\nDRY RUN — nothing written in v1. Full diff: {HERE / 'dry_run_diff.txt'}")
    sys.exit(0)

run = HERE / "backups" / datetime.datetime.now().strftime("%Y%m%dT%H%M%S"); run.mkdir(parents=True)
files = []
for a, (p, cur, new, rep) in pl.items():
    (run / f"{a}.md").write_text(cur, encoding="utf-8")
    p.write_text(new, encoding="utf-8")
    files.append({"agent": a, "path": str(p), "sha_before": sha(cur), "sha_after": sha(new), "report": rep})
(run / "manifest.json").write_text(json.dumps({"applied": datetime.datetime.now().isoformat(), "source": SRC, "v1": str(V1), "files": files}, indent=1, ensure_ascii=False))
summary(pl)
print(f"\nAPPLIED to {len(files)} file(s). Backup + manifest: {run}\nUndo with:  python3 {pathlib.Path(__file__).name} --undo")
