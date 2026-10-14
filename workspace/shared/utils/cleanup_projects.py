"""
cleanup_projects.py — remove STALE test-project SIGNATURES from the app, SAFELY.

Keeps only what the owner wants: Test 2 (fulfillment-vq-status-read-only), Test 3 (email-klaviyo-
workflows-read-only*), the NEWEST Test 4 ('revealer-*') and the NEWEST Test 5 (deploy/overwrite) project.
Deletes Test 1 (organics-vm-deploy-*) and every OLD revealer-*/deploy run.

HARD SAFETY:
  • NEVER runs while a test is active (STATUS=RUNNING) — the app stores every run's data in shared files,
    so deleting other projects mid-run could corrupt the live run. It skips instead.
  • Only removes APP PROJECT RECORDS via projects.delete_project — it CANNOT and does NOT touch real code
    folders on disk, the VolatileWorkSpace organic-frontend/organic-backend deploy folders, or anything
    outside the app's own data store.
  • Deletes ONLY ids that clearly belong to the test set (organics-vm-deploy*, revealer*, *overwrite*,
    *sandbox-deploy*); anything unrecognized is left untouched.

Usage:  python3 testing/cleanup_projects.py        (dry-run shows the plan)
        python3 testing/cleanup_projects.py --apply (actually delete)
"""
from __future__ import annotations
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "server"))


def main() -> int:
    apply = "--apply" in sys.argv[1:]
    status = HERE / "results" / "STATUS"
    if status.exists() and status.read_text(errors="ignore").startswith("RUNNING"):
        print("⏸ A test run is ACTIVE (STATUS=RUNNING) — skipping cleanup to protect the live run's data.")
        return 0
    try:
        import projects
    except Exception as e:
        print(f"cannot import projects: {e}")
        return 1
    pf = ROOT / "data" / "projects.json"
    if not pf.exists():
        print("no data/projects.json")
        return 0
    d = json.load(open(pf))
    ps = d.get("projects", d) if isinstance(d, dict) else d
    if isinstance(ps, dict):
        ps = list(ps.values())
    ids = [(str(p.get("id")), p.get("created", 0)) for p in ps if p.get("id")]

    def _is(pat, i):
        return pat in i.lower()

    # Explicit allow-list of PASSED project ids the owner wants to keep (the driver appends a Test 4/Test 5
    # pid here the moment it PASSES). We never keep a revealer/deploy just for being newest — a newest one is
    # usually a FAILED leftover. Only T2, T3, and ids recorded as passed survive.
    keepf = HERE / "results" / "KEEP_PROJECTS.txt"
    passed_ids = set()
    if keepf.exists():
        passed_ids = {ln.strip() for ln in keepf.read_text(errors="ignore").splitlines() if ln.strip()}

    keep = set()
    # Test 2 — always keep its single seeded project (safety: never delete it).
    for i, _ in ids:
        if "fulfillment-vq-status-read-only" in i.lower():
            keep.add(i)
    # Explicit keep-list = the chosen ONE Test 3 + any passed Test 4 / Test 5 the driver recorded.
    keep |= {i for i, _ in ids if i in passed_ids}
    # ONE-PER-TEST safety net for Test 3: if the keep-list named no email-klaviyo, keep only the NEWEST one
    # (and delete the older duplicate). With 72df in the keep-list this leaves exactly one Test 3.
    eks = sorted([i for i in ids if "email-klaviyo-workflows-read-only" in i[0].lower()], key=lambda x: -x[1])
    if eks and not any("email-klaviyo-workflows-read-only" in k.lower() for k in keep):
        keep.add(eks[0][0])
    # TRANSIENT PROTECTION: never delete the NEWEST revealer or the NEWEST overwrite/deploy — that is the
    # live (or just-finished, decision-pending) run. A FAILED run stops being newest once the next run
    # starts, so it gets cleaned then; a PASSED run is recorded in the keep-list and kept permanently. This
    # guarantees the live run is never deleted even if cleanup is invoked at an awkward moment.
    revs = sorted([i for i in ids if _is("revealer", i[0])], key=lambda x: -x[1])
    deploys = sorted([i for i in ids if _is("overwrite", i[0]) or _is("sandbox-deploy", i[0])], key=lambda x: -x[1])
    if revs:
        keep.add(revs[0][0])
    if deploys:
        keep.add(deploys[0][0])

    # Delete candidates = ANY known TEST project not in `keep`. This includes duplicate Test 3
    # (email-klaviyo) and Test 2 (fulfillment-vq) instances — the ones we keep are already in `keep`, so
    # only the extra/old duplicates get removed. One-per-test is thus enforced for every test.
    _TESTPAT = ("organics-vm-deploy", "revealer", "overwrite", "sandbox-deploy",
                "email-klaviyo-workflows-read-only", "fulfillment-vq-status-read-only")
    todel = []
    for i, _ in ids:
        il = i.lower()
        if i in keep:
            continue
        if any(pat in il for pat in _TESTPAT):
            todel.append(i)

    print("KEEP  :", sorted(keep))
    print("DELETE:", todel)
    if not apply:
        print("\n(dry-run — re-run with --apply to delete the above. Real code folders are never touched.)")
        return 0
    for i in todel:
        try:
            projects.delete_project(i)
            print("  ✓ deleted", i)
        except Exception as e:
            print("  ✗ failed", i, e)
    print(f"done — kept {len(keep)}, deleted {len(todel)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
