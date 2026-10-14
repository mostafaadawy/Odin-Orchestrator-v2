#!/usr/bin/env python3
"""
Deployment change-detection — the FIRST step the DevOps agent runs before any organics deploy.

Keeps TWO saved lists (front-end + back-end) built from the owner's LOCAL source folders:
  - VolatileWorkSpace/RBO-Staging/f (staging frontend)
  - VolatileWorkSpace/RBO-Staging/b (staging backend)
Each list records every deployable file + its **modification date** (mtime), EXCLUDING the things we
never deploy: node_modules, .env / .env.* / .backup-env, build folders (.next front / dist back),
package.json + the lockfile, and public/uploads/logs.

On each deploy the agent:
  1) `scan`   → compares current mtimes to the saved list → prints added / modified / removed.
              If a baseline exists and NOTHING changed → deployment is NOT required (skip).
  2) deploys ONLY the changed files (over SSH as mostafa; az only for firewall/IP; never root).
  3) after a VERIFIED-successful deploy → `update` → saves the current **real** mtimes as the new baseline.

Special one-time bootstrap (`seed-old`): when there is no reliable prior state, write the baseline with
every file's date set to 2 years ago, so the very next `scan` reports EVERYTHING as changed → a full,
clean overwrite happens through the NORMAL script flow (no hardcoded exception). After that deploy
succeeds, `update` records the real dates so future runs detect real changes only.

    python infra/deploy_changes.py scan       # front+back diff vs saved lists
    python infra/deploy_changes.py seed-old    # one-time: baseline dated 2 years ago (=> all changed)
    python infra/deploy_changes.py update      # after a good deploy: save REAL mtimes as the new baseline
    python infra/deploy_changes.py changed backend   # print just the changed file paths (for rsync --files-from)
"""
from __future__ import annotations
import sys, os, json, time, pathlib, fnmatch

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPO = pathlib.Path(__file__).resolve().parents[3]
HOME = pathlib.Path.home()

# ---------------------------------------------------------------------------------------------
# GENERIC ENGINE: this script knows NOTHING about any specific project. It is told WHICH project
# to measure (--project / ODIN_DEPLOY_PROJECT) and reads that project's OWN delta:
#     workspace/projects/<pid>/deploy/deploy-config.json
# so the same engine serves the real production, a sandbox, or any future project. Each project's
# personal paths (local source folders, VM target) live in ITS delta — never in here.
# ---------------------------------------------------------------------------------------------
PROJECT = os.environ.get("ODIN_DEPLOY_PROJECT", "organics-prod-deploy")
for _i, _a in enumerate(sys.argv):
    if _a == "--project" and _i + 1 < len(sys.argv):
        PROJECT = sys.argv[_i + 1]

# per-project baseline lists (legacy flat files stay valid for the original production project)
_LEGACY = pathlib.Path(__file__).resolve().parent / "deploy-lists"
LISTS = _LEGACY if (PROJECT == "organics-prod-deploy" and (_LEGACY / "backend.json").exists()) \
    else _LEGACY / PROJECT
LISTS.mkdir(parents=True, exist_ok=True)

_DEF_EXC_DIRS = {"node_modules", "dist", ".next", "logs", ".git", "migrations"}
_DEF_EXC_GLOB = [".env", ".env.*", "*.env", ".env.example", ".backup-env", "*.env.bak",
                 "package-lock.json", "yarn.lock", "pnpm-lock.yaml", ".DS_Store",
                 "next-env.d.ts", "tsconfig.tsbuildinfo", "*.tsbuildinfo"]


def _targets_from_project(pid: str):
    """Build the measure-set from THIS project's delta. Returns {} if the project has no deploy config."""
    cfg_p = REPO / "workspace" / "projects" / pid / "deploy" / "deploy-config.json"
    try:
        cfg = json.loads(cfg_p.read_text())
    except Exception:
        return {}
    out = {}
    for t in cfg.get("targets", []):
        name = t.get("name")
        local = t.get("local")
        if not name or not local:
            continue
        exc = set(t.get("excludes") or [])
        out[name] = {
            "src": pathlib.Path(os.path.expanduser(local)),
            "exclude_dirs": {e.rstrip("/**").rstrip("/") for e in exc if "*" not in e} | _DEF_EXC_DIRS,
            "exclude_glob": [e for e in exc if "*" in e] or _DEF_EXC_GLOB,
        }
    return out


_LEGACY_TARGETS = {
    # Excludes per the owner's spec: env files, the package LOCK (NOT package.json), node_modules, and the
    # BUILD folders (dist = NestJS backend, .next = Next.js frontend). Everything else is INCLUDED.
    # (.git is never source; public/logs/uploads stay excluded per the deploy rules — they are static/runtime.)
    # Owner's exclusion spec = ONLY: env*, the package LOCK (NOT package.json), node_modules, dist (backend
    # build), .next (frontend build). Everything else is INCLUDED — INCLUDING public/ (site assets like the
    # captcha icons + photos). We also drop pure MACHINE-GENERATED noise that the owner never hand-edits and
    # that must not count as a source change: prisma migrations (regenerated on the VM by `migrate dev`),
    # next-env.d.ts, *.tsbuildinfo, logs, .git.
    "backend": {
        "src": pathlib.Path("/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Isolated/_external/VolatileWorkSpace") / "RBO-Staging/b",
        "exclude_dirs": {"node_modules", "dist", "logs", ".git", "migrations"},
        "exclude_glob": [".env", ".env.*", "*.env", ".env.example", ".backup-env", "*.env.bak",
                         "package-lock.json", "yarn.lock", "pnpm-lock.yaml", ".DS_Store",
                         "*.tsbuildinfo"],
    },
    "frontend": {
        "src": pathlib.Path("/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Isolated/_external/VolatileWorkSpace") / "RBO-Staging/f",
        "exclude_dirs": {"node_modules", ".next", "logs", ".git"},   # public INCLUDED (photos/icons deploy)
        "exclude_glob": [".env", ".env.*", "*.env", ".env.example", ".backup-env", "*.env.bak",
                         "package-lock.json", "yarn.lock", "pnpm-lock.yaml", ".DS_Store",
                         "next-env.d.ts", "tsconfig.tsbuildinfo", "*.tsbuildinfo"],
    },
}

# The project's OWN delta wins. The legacy block above is only the fallback for the original
# production project so its long-standing behaviour is byte-for-byte unchanged.
TARGETS = (_LEGACY_TARGETS if PROJECT == "organics-prod-deploy" else _targets_from_project(PROJECT))
if not TARGETS:
    print(f"[deploy_changes] no deploy targets for project '{PROJECT}' "
          f"(expected workspace/projects/{PROJECT}/deploy/deploy-config.json with .targets[])")

TWO_YEARS_AGO = int(time.time()) - 2 * 365 * 24 * 3600   # ~2024


def _excluded(rel: str, cfg: dict) -> bool:
    parts = pathlib.PurePosixPath(rel).parts
    if any(p in cfg["exclude_dirs"] for p in parts):
        return True
    base = parts[-1] if parts else rel
    return any(fnmatch.fnmatch(base, g) for g in cfg["exclude_glob"])


def _scan_tree(cfg: dict) -> dict:
    """{relpath: mtime_int} of every deployable file under src."""
    src = pathlib.Path(cfg["src"]); out = {}
    if not src.exists():
        return out
    for dp, dns, fns in os.walk(src):
        dns[:] = [d for d in dns if d not in cfg["exclude_dirs"]]
        for fn in fns:
            full = pathlib.Path(dp) / fn
            rel = str(full.relative_to(src))
            if _excluded(rel, cfg):
                continue
            try:
                out[rel] = int(full.stat().st_mtime)
            except Exception:
                pass
    return out


def _list_path(name): return LISTS / f"{name}.json"
def _load(name) -> dict:
    try: return json.loads(_list_path(name).read_text()).get("files", {})
    except Exception: return {}
def _save(name, files):
    _list_path(name).write_text(json.dumps(
        {"saved_at": time.strftime("%Y-%m-%d %H:%M:%S"), "count": len(files), "files": files}, indent=2))


def diff(name) -> dict:
    cur = _scan_tree(TARGETS[name]); old = _load(name)
    added = sorted(f for f in cur if f not in old)
    removed = sorted(f for f in old if f not in cur)
    modified = sorted(f for f in cur if f in old and cur[f] != old[f])
    return {"target": name, "src": str(TARGETS[name]["src"]), "total": len(cur),
            "baseline_exists": bool(old), "added": added, "modified": modified, "removed": removed,
            "changed": sorted(set(added) | set(modified))}


def scan_all():
    return {n: diff(n) for n in TARGETS}


# --- DB-sensitivity: is a changed file part of the SCHEMA or the SEED? ------------------------------
# If yes, a plain code deploy is NOT enough — the DB likely needs a rebase/reseed. The deploy flow must
# then RECOMMEND (serious, but required) a DB deployment and ASK the owner to approve/deny.
SCHEMA_HINTS = ("prisma/schema.prisma", "prisma/migrations", ".prisma")
SEED_HINTS   = ("src/seed/", "prisma/seed", "seed-data", "rbac.seed", "seed-reference", "seed.")


def classify_db(changed) -> dict:
    norm = [f.replace("\\", "/") for f in changed]
    schema = sorted({f for f in norm if any(h in f for h in SCHEMA_HINTS)})
    seed   = sorted({f for f in norm if any(h in f for h in SEED_HINTS)})
    return {"schema": schema, "seed": seed, "sensitive": bool(schema or seed)}


def db_scan_all() -> dict:
    allchanged = []
    for n in TARGETS:
        allchanged += diff(n)["changed"]
    return classify_db(allchanged)


def seed_old():
    """One-time bootstrap: baseline dated 2 years ago → next scan marks EVERYTHING changed."""
    res = {}
    for n, cfg in TARGETS.items():
        files = {rel: TWO_YEARS_AGO for rel in _scan_tree(cfg)}
        _save(n, files); res[n] = len(files)
    return res


def update_real():
    """After a verified-successful deploy: save each file's REAL current mtime as the new baseline."""
    res = {}
    for n, cfg in TARGETS.items():
        files = _scan_tree(cfg)   # real mtimes
        _save(n, files); res[n] = len(files)
    return res


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "scan"
    if cmd == "seed-old":
        print(json.dumps({"seeded_2yr_ago": seed_old()}, indent=2))
    elif cmd == "update":
        print(json.dumps({"baseline_updated_real_mtimes": update_real()}, indent=2))
    elif cmd == "changed":
        name = sys.argv[2] if len(sys.argv) > 2 else "backend"
        for f in diff(name)["changed"]:
            print(f)
    elif cmd == "dbscan":
        # machine-readable DB-sensitivity check for the deploy flow
        c = db_scan_all()
        print(json.dumps(c, indent=2))
        print("DB_SENSITIVE:", "YES" if c["sensitive"] else "NO")
    else:
        d = scan_all(); need = False
        for n, r in d.items():
            print(f"\n=== {n} — {r['total']} files · baseline={'yes' if r['baseline_exists'] else 'NONE'} ===")
            print(f"  added:{len(r['added'])}  modified:{len(r['modified'])}  removed:{len(r['removed'])}")
            if r["changed"] or r["removed"]:
                need = True
                for f in r["changed"][:10]: print(f"    ~ {f}")
        print("\nDEPLOY_REQUIRED:" , "YES" if need else "NO (no changes → skip)")
        # SMART DB-change recommendation: flag schema/seed changes so the flow asks to rebase/reseed.
        c = db_scan_all()
        if c["sensitive"]:
            print("DB_SENSITIVE: YES  ⚠  RECOMMENDATION (serious, but required): schema/seed files changed"
                  " → a DATABASE rebase/reseed is recommended. The deploy will ASK you to approve or deny.")
            for f in (c["schema"] + c["seed"])[:12]:
                tag = "schema" if any(h in f for h in SCHEMA_HINTS) else "seed"
                print(f"    ⚠ [{tag}] {f}")
        else:
            print("DB_SENSITIVE: NO  (no schema/seed files changed → normal non-destructive deploy)")
