#!/usr/bin/env python3
"""G5 + F-36: a project's own delta is never flagged/promoted as a duplicate; duplicate cleanup keeps the OLDEST
registered copy under its ORIGINAL name, in the correct shared category; a shared-name clash is flagged, never overwritten."""
import pathlib, sys
R = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
def sub(path, old, new, count=1):
    p = R / path; s = p.read_text()
    assert s.count(old) == count, (path, old[:70], s.count(old)); p.write_text(s.replace(old, new))
MW, AU = "server/workspace_mw.py", "server/workspace_audit.py"
# ---------------- workspace_mw.py ----------------
sub(MW, '''def _promote_to_shared(src_path, category=None, extra_consumers=None) -> dict:''', '''class SharedNameConflict(ValueError):
    """F-36: shared/<category>/<name> already holds DIFFERENT content — never overwrite or drop a copy."""


_TEST_NAME = re.compile(r"(^test_|_test\\.|\\.test\\.|\\.spec\\.|(^|[_\\-.])e2e([_\\-.]|$)|^conftest\\.py$)", re.I)
_TEST_BODY = re.compile(r"^\\s*(import unittest|from unittest|import pytest|from pytest)|^\\s*def test_\\w+\\(|\\bdescribe\\(|\\bit\\(['\\"]", re.M)


def shared_category(p) -> str:
    """F-36: the CORRECT shared category for a file — decided by where it lives and what it is, never by a
    substring of its name ('latest_prices.py' or 'dup_test_r4.py' holding a helper is NOT a test)."""
    p = pathlib.Path(p)
    try:
        parts = p.resolve().relative_to(WS.resolve()).parts
    except Exception:
        parts = p.parts
    sub = parts[2] if len(parts) > 3 and parts[0] in ("projects", "agents") else ""
    try:
        body = p.read_text(errors="replace")[:20000]
    except Exception:
        body = ""
    if sub == "tests" or (_TEST_NAME.search(p.name) and (_TEST_BODY.search(body) or not body)) or _TEST_BODY.search(body):
        return "testing"
    if sub == "deploy" or re.search(r"(^|[_\\-.])deploy([_\\-.]|$)", p.name.lower()):
        return "infra"
    return "utils"


def oldest_registered(paths) -> str:
    """F-36: of several identical copies, the ORIGINAL = the oldest copy that odin_core has a row for (oldest
    file birth time; then the DB row's created_at; then path). If none is registered, the oldest on disk."""
    rows = {}
    conn = _db()
    if conn:
        try:
            cu = conn.cursor()
            cu.execute("SELECT path, created_at FROM files WHERE path = ANY(%s)", ([_relp(x) for x in paths],))
            rows = {a: b for a, b in cu.fetchall()}
        except Exception:
            rows = {}
        finally:
            conn.close()
    def key(x):
        q = ROOT / _relp(x)
        try:
            st = q.stat(); born = getattr(st, "st_birthtime", st.st_ctime)
        except Exception:
            born = float("inf")
        ca = rows.get(_relp(x))
        return (0 if _relp(x) in rows else 1, born, ca.timestamp() if ca else float("inf"), _relp(x))
    return sorted(paths, key=key)[0]


def _promote_to_shared(src_path, category=None, extra_consumers=None) -> dict:''')
sub(MW, '''    cat = category or ("infra" if "deploy" in low else
                       "testing" if ("test" in low or "e2e" in low or "spec" in low) else "utils")''',
        '''    cat = category or shared_category(p)          # F-36: by location + content, not a name substring''')
sub(MW, '''    created_shared = not dest.exists()
    _g8_cb = get_creator(p)[1]               # G8: keep the creator across the move''', '''    created_shared = not dest.exists()
    if dest.exists() and p.exists() and dest.read_bytes() != p.read_bytes():
        raise SharedNameConflict(f"{dest_rel} already exists with DIFFERENT content — not promoted; owner review")
    _g8_cb = get_creator(p)[1]               # G8: keep the creator across the move''')
# ---------------- workspace_audit.py ----------------
sub(AU, '''    # (a) IDENTICAL content across >=2 projects — catches the same function under DIFFERENT names
    by_hash, seen = {}, set()
    for p in _cap_files():''', '''    # G5: a project's OWN delta is not a duplicate — (1) a registered overlay in its dependency manifest,
    # (2) a file whose header declares "delta over shared capability: shared/…" (base exists), or (3) a
    # per-project input that a shared capability / core code reads from EVERY project at the same place
    # (e.g. deploy/deploy-config.json read by shared/infra/deploy_changes.py).
    _exempt = _delta_exemptions()
    by_hash, seen = {}, set()
    # (a) IDENTICAL content across >=2 projects — catches the same function under DIFFERENT names
    for p in _cap_files():
        if str(p.relative_to(ROOT)) in _exempt:
            continue''')
sub(AU, '''    by_name = {}
    for p in _cap_files():
        by_name.setdefault(p.name, []).append(p)''', '''    by_name = {}
    for p in _cap_files():
        if str(p.relative_to(ROOT)) in _exempt:
            continue
        by_name.setdefault(p.name, []).append(p)''')
sub(AU, '''def _external_writes() -> list:''', '''_CONV_STR = re.compile(r"projects/(?:<[^>/]+>|\\{[^}/]+\\}|\\$\\{?[A-Za-z_]+\\}?)/([A-Za-z0-9_\\-]+)/([A-Za-z0-9_\\-.]+\\.[A-Za-z0-9]+)")
_CONV_JOIN = re.compile(r"[\\"']([A-Za-z0-9_\\-]+)[\\"']\\s*/\\s*[\\"']([A-Za-z0-9_\\-.]+\\.[A-Za-z0-9]+)[\\"']")


def _per_project_inputs() -> set:
    """(subfolder, filename) pairs that shared capabilities or core code read PER PROJECT."""
    out = set()
    srcs = list((ROOT / "server").glob("*.py"))
    if (WS / "shared").exists():
        srcs += [p for p in (WS / "shared").rglob("*") if p.is_file() and p.suffix in (".py", ".sh", ".js", ".ts")
                 and ".bak" not in p.name]
    for s in srcs:
        try:
            t = s.read_text(errors="replace")
        except Exception:
            continue
        out.update(_CONV_STR.findall(t))
        out.update(_CONV_JOIN.findall(t))
    return out


def _delta_exemptions() -> dict:
    """{ROOT-relative path: reason} for every project file that is that project's own delta (G5)."""
    ex = {}
    conv = _per_project_inputs()
    for proj in (WS / "projects").glob("*") if (WS / "projects").exists() else []:
        if not proj.is_dir():
            continue
        man = proj / "dependencies" / "manifest.json"
        try:
            entries = json.loads(man.read_text()) if man.is_file() else []
        except Exception:
            entries = []
        for d in entries if isinstance(entries, list) else []:
            ov = d.get("overlay")
            if ov and str(d.get("source", "")).startswith("shared/"):
                for q in ((proj / ov), (proj / "code" / ov)):
                    if q.is_file():
                        ex[str(q.relative_to(ROOT))] = f"registered delta over {d['source']}"
                    elif q.is_dir():
                        for f in q.rglob("*"):
                            if f.is_file():
                                ex[str(f.relative_to(ROOT))] = f"registered delta over {d['source']}"
        for sub in ("code", "deploy"):
            for f in proj.glob(f"{sub}/**/*"):
                if not f.is_file():
                    continue
                rel = str(f.relative_to(ROOT))
                if rel in ex:
                    continue
                if (sub, f.name) in conv and f.parent == proj / sub:
                    ex[rel] = f"per-project input {sub}/{f.name} read by a shared capability"
                    continue
                try:
                    head = f.read_text(errors="replace")[:600]
                except Exception:
                    continue
                m = re.search(r"delta over shared capability:\\s*(shared/[\\w./-]+)", head)
                if m and (WS / m.group(1)).is_file():
                    ex[rel] = f"declared delta over {m.group(1)}"
    return ex


def _external_writes() -> list:''')
sub(AU, '''                others = iss["paths"][1:]
                res = mw.promote_to_shared(
                    str(ROOT / iss["paths"][0]),
                    extra_consumers=[("project", pathlib.Path(x).parts[2]) for x in others])''', '''                # F-36: keep the OLDEST registered copy, under its ORIGINAL name, in the correct category
                keep = mw.oldest_registered(iss["paths"])
                others = [x for x in iss["paths"] if x != keep]
                res = mw.promote_to_shared(
                    str(ROOT / keep),
                    extra_consumers=[("project", pathlib.Path(x).parts[2]) for x in others])''')
sub(AU, '''        except Exception as e:
            fix = f"error: {e}"
        finally:''', '''        except mw.SharedNameConflict as e:      # F-36: never overwrite / drop a different shared file
            fix = f"FLAGGED: {e}"
        except Exception as e:
            fix = f"error: {e}"
        finally:''')
print("G5 + F-36 applied")

# ---- G5 part 2: per-project inputs come only from SHARED capabilities, joins only when built from a project id (applied in-tree; see git diff g5-start..g5-done)
