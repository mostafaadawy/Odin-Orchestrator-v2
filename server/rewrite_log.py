#!/usr/bin/env python3
"""rewrite_log.py — the log of every AUTOMATIC change the middleware/audit made (G6b, owner condition).

  python server/rewrite_log.py list [--batch ID] [--last N]   show changes: time, batch, reason, file, old -> new
  python server/rewrite_log.py revert <batch-id> [--no-hold]  undo ONE action exactly (one command)
  python server/rewrite_log.py release <batch-id>             lift the hold: the audit may fix those paths again

One action (a promotion or one audit heal) = one batch. Revert restores every rewritten file's previous
content (only if nobody edited it since), moves the file back from shared, recreates removed copies, drops
the dependency rows that action created, and puts a HOLD so the audit flags those paths instead of redoing it."""
import sys, os, json, pathlib
ROOT = pathlib.Path(os.environ.get("ODIN_ROOT") or pathlib.Path(__file__).resolve().parent.parent)
sys.path.insert(0, str(ROOT / "server"))
import workspace_mw as mw


def _list(a):
    batch = a[a.index("--batch") + 1] if "--batch" in a else None
    last = int(a[a.index("--last") + 1]) if "--last" in a else None
    rows = mw.change_log(batch)
    rows = rows[-last:] if last else rows
    for d in rows:
        k = d.get("kind")
        if k == "ref-rewrite":
            what = f"{d['file']}: {d['old']} -> {d['new']}"
        elif k == "move":
            what = f"MOVED {d['from']} -> {d['to']}"
        elif k == "copy-removed":
            what = f"REMOVED identical copy {d['path']} (kept {d['kept']})"
        elif k == "revert":
            what = f"REVERTED batch {d['reverts']}: {len(d['done'])} done, {len(d['skipped'])} skipped"
        elif k == "release":
            what = "HOLD RELEASED by the owner"
        else:
            what = f"HOLD on {len(d.get('paths') or [])} path(s)"
        print(f"{d.get('ts','')[:19]}  {d.get('batch') or d.get('reverts')}  {k:12}  {what}  | reason: {d.get('reason','')}")
    print(f"-- {len(rows)} change(s)")
    return 0


def main(a):
    if not a or a[0] not in ("list", "revert", "release"):
        print(__doc__); return 2
    if a[0] == "list":
        return _list(a[1:])
    if len(a) < 2:
        print(__doc__); return 2
    r = mw.release_hold(a[1]) if a[0] == "release" else mw.revert_batch(a[1], hold="--no-hold" not in a)
    print(json.dumps(r, indent=2, ensure_ascii=False))
    return 0 if r.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
