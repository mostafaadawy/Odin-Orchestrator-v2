"""Reproduce 'delete leaves 1-2 registry rows': create a project like the prompt journey does, simulate a run
(scope messages), let the audit heal (indexes files), delete via workspace_mw.delete_owner, diff registry counts."""
import sys, os, json, pathlib
root = pathlib.Path(sys.argv[1]).resolve()
if "/_research/tmp/" not in str(root): sys.exit("REFUSED")
sys.path.insert(0, str(root / "server")); os.chdir(root)
import workspace_mw as mw, workspace_audit as au, projects, scopes
def counts():
    c = mw._db(); cu = c.cursor(); out = {}
    for t in ("projects", "agents", "files", "folders", "dependencies", "project_agents", "project_chats"):
        cu.execute(f"SELECT count(*) FROM {t}"); out[t] = cu.fetchone()[0]
    cu.execute("SELECT path, owner_type, owner_id FROM files"); rows = set(cu.fetchall()); c.close(); return out, rows
au.heal(force=True)
b, brows = counts()
p = projects.create_project("Repro Delete", "Track shipments and produce a report", "", [{"name": "Fulfillment", "role": "Fulfillment"}, {"name": "Reporter", "role": "Reporter"}], identifier="repro-delete")
pid = p.get("id") or "repro-delete"
c = scopes.create_chat(f"project:{pid}", "Run")
for i in range(3): scopes.add_message(f"project:{pid}", c["id"], "assistant", f"m{i}")
au.heal(force=True)
mw.delete_owner("project", pid)
au.heal(force=True)
e, erows = counts()
print(json.dumps({"pid": pid, "delta": {k: e[k] - b[k] for k in b}, "leftover_rows": sorted(map(list, erows - brows))[:10]}, default=str))
