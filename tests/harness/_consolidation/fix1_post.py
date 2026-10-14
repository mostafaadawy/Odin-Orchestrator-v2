import sys, os, json, pathlib
R = pathlib.Path(__file__).resolve().parent.parent; sys.path[:0] = [str(R / "server")]
os.environ.setdefault("PGHOST", "/tmp/odc_pg"); os.environ.setdefault("PGPORT", "25432")
import workspace_mw as mw, workspace_audit as au, psycopg2
out = {}
c = psycopg2.connect(dbname="odin_core_con"); cu = c.cursor()
for rep in (4, 5, 6):
    f = R / f"_consolidation/results/S2_r{rep}.json"
    if not f.exists(): continue
    pid = json.load(open(f))["pid"]
    P = R / "workspace/projects" / pid
    cu.execute("SELECT path, owner_type, owner_id FROM files WHERE path LIKE %s", (f"workspace/projects/{pid}/deploy/%",))
    rows = cu.fetchall()
    cu.execute("SELECT owner_type, owner_id, name, source_path, mode FROM dependencies WHERE owner_id=%s", (pid,))
    deps = cu.fetchall()
    cu.execute("SELECT owner_id, path FROM files WHERE path LIKE %s AND owner_id<>%s", (f"workspace/projects/{pid}/%", pid))
    wrong = cu.fetchall()
    man = P / "dependencies/manifest.json"
    out[f"r{rep}"] = {"pid": pid, "deploy_files": sorted(p.name for p in (P / "deploy").glob("*") if p.name != ".gitkeep"),
                      "files_rows": rows, "wrong_owner_rows": wrong, "dependencies_rows": deps,
                      "manifest": json.loads(man.read_text()) if man.exists() else None,
                      "resolve": {k: v for k, v in mw.resolve_capability("project", pid, "deploy_changes.py").items() if k in ("resolved", "overlay", "base")},
                      "audit_issues": [(i["type"], i.get("path") or i.get("paths")) for i in au.scan() if pid in json.dumps(i)]}
c.close()
out["revealer"] = {n: mw.resolve_capability("project", "revealer-6978", n).get("resolved") for n in ("deploy_changes.py", "testing")}
out["delta_duplicate_flags"] = [i.get("paths") for i in au.scan() if i.get("type") == "duplicate" and any("/deploy/" in p for p in (i.get("paths") or []))]
print(json.dumps(out, indent=1, default=str))
(R / "_consolidation/results/fix1_post.json").write_text(json.dumps(out, indent=1, default=str))
