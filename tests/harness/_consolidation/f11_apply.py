"""F-11 (owner's 50% rule) — idempotent edits. Run from the copy root."""
import pathlib
def edit(p, old, new, marker):
    s = pathlib.Path(p).read_text()
    if marker in s: print('skip', p, marker); return
    assert s.count(old) == 1, (p, old[:70], s.count(old))
    pathlib.Path(p).write_text(s.replace(old, new)); print('ok', p, marker)

MW = 'server/workspace_mw.py'
edit(MW, '''class SharedNameConflict(ValueError):
    """F-36: shared/<category>/<name> already holds DIFFERENT content — never overwrite or drop a copy."""
''', '''class SharedNameConflict(ValueError):
    """F-36: shared/<category>/<name> already holds DIFFERENT content — never overwrite or drop a copy."""


# ── F-11 (owner's design, 2026-10-12): the 50% rule for SHARED vs SEPARATE ──
#   more than 50% common    -> one SHARED base + a per-project DELTA
#   more than 50% different -> SEPARATE scripts (not a duplicate; nothing is merged)
#   exactly 50%             -> owner review (never guessed)
# "Common" = matching meaningful lines (blank and comment-only lines ignored), Dice-style over both files.
SHARE_THRESHOLD = 0.5
_F11_COMMENT = re.compile(r"^\\s*(#|//|--|;|/\\*|\\*/|\\*\\s)")


def _f11_lines(text) -> list:
    return [l.strip() for l in (text or "").splitlines() if l.strip() and not _F11_COMMENT.match(l)]


def common_ratio(a: str, b: str) -> float:
    import difflib
    la, lb = _f11_lines(a), _f11_lines(b)
    if not la and not lb:
        return 1.0
    sm = difflib.SequenceMatcher(None, la, lb, autojunk=False)
    m = sum(bl.size for bl in sm.get_matching_blocks())
    return 2.0 * m / (len(la) + len(lb))


def share_decision(a: str, b: str) -> dict:
    r = round(common_ratio(a, b), 4)
    d = "shared+delta" if r > SHARE_THRESHOLD else ("separate" if r < SHARE_THRESHOLD else "review")
    return {"common": r, "decision": d}
''', 'SHARE_THRESHOLD = 0.5')

edit(MW, '''def customize_shared(owner_type, owner_id, name, overlay_name, overlay_content, mode="override") -> dict:''',
'''def customize_shared(owner_type, owner_id, name, overlay_name, overlay_content, mode="override",
                     full_version: str = None) -> dict:''', 'full_version: str = None')
edit(MW, '''    if not src:
        return {"ok": False, "reason": f"shared base for '{name}' not found"}
    res = put_file(owner_type, owner_id, "code", overlay_name, overlay_content)  # overlay in the owner's own code/''',
'''    if not src:
        return {"ok": False, "reason": f"shared base for '{name}' not found"}
    if full_version is not None:   # F-11: the owner's whole version decides delta vs separate script
        dec = share_decision((WS / src).read_text(errors="replace"), full_version)
        if dec["decision"] == "review":
            return {"ok": False, **dec, "reason": "exactly 50% common — owner review (F-11)"}
        if dec["decision"] == "separate":
            res = put_file(owner_type, owner_id, "code", overlay_name, full_version)   # its own script, no base
            return {"ok": True, **dec, "base": None, "separate": res["path"]}
        overlay_content = full_version
        mode = "override"
    res = put_file(owner_type, owner_id, "code", overlay_name, overlay_content)  # overlay in the owner's own code/''',
'if full_version is not None:')
edit(MW, '''    return {"ok": True, "base": src, "overlay": overlay_name, "mode": mode, "overlay_path": res["path"]}''',
'''    out = {"ok": True, "base": src, "overlay": overlay_name, "mode": mode, "overlay_path": res["path"]}
    if full_version is not None:
        out.update(dec)
    return out''', 'out.update(dec)')

AU = 'server/workspace_audit.py'
edit(AU, '''    for name, paths in by_name.items():
        if len({_proj(x) for x in paths}) >= 2:
            key = tuple(sorted(str(x.relative_to(ROOT)) for x in paths))
            if key not in seen:
                issues.append({"type": "duplicate", "name": name, "paths": list(key), "identical": False,
                               "reason": "same filename, different content in >=2 projects — promote shared base + custom deltas"})''',
'''    for name, paths in by_name.items():
        if len({_proj(x) for x in paths}) >= 2:
            key = tuple(sorted(str(x.relative_to(ROOT)) for x in paths))
            if key not in seen:
                # F-11 (owner's 50% rule): compare every copy with the ORIGINAL (oldest registered) copy
                try:
                    base = mw.oldest_registered(list(key))
                    bt = (ROOT / base).read_text(errors="replace")
                    plan = {x: mw.share_decision(bt, (ROOT / x).read_text(errors="replace")) for x in key if x != base}
                except Exception:
                    base, plan = None, {}
                if plan and all(v["decision"] == "separate" for v in plan.values()):
                    continue   # >50% different everywhere: separate scripts by design — not a duplicate
                issues.append({"type": "duplicate", "name": name, "paths": list(key), "identical": False,
                               "base": base, "plan": plan,
                               "reason": "same filename, different content in >=2 projects — F-11: " + (", ".join(
                                   f"{x.split('/')[2]} {int(v['common'] * 100)}% common -> {v['decision']}"
                                   for x, v in plan.items()) or "promote shared base + custom deltas")})''',
'F-11 (owner\'s 50% rule): compare every copy')
edit(AU, '''            elif t == "duplicate":
                fix = "FLAGGED: duplicate differs across projects — promote shared base + custom deltas (review)"''',
'''            elif t == "duplicate" and iss.get("base") and iss.get("plan") and \\
                    not any(v["decision"] == "review" for v in iss["plan"].values()):
                # F-11: >50% common -> the ORIGINAL copy becomes the shared base; every >50%-common copy stays
                # in its project, registered as that project's DELTA over the base; <50% copies stay separate.
                deltas = [x for x, v in iss["plan"].items() if v["decision"] == "shared+delta"]
                sep = [x for x, v in iss["plan"].items() if v["decision"] == "separate"]
                res = mw.promote_to_shared(str(ROOT / iss["base"]))
                for x in deltas:
                    pp = pathlib.Path(x).parts
                    mw.add_dependency("project", pp[2], pp[-1], res["promoted"], kind="code", mode="override",
                                      overlay=str(pathlib.Path(*pp[3:])))
                fix = (f"F-11 shared base {res['promoted']} + deltas {deltas}"
                       + (f"; kept separate (>50% different): {sep}" if sep else ""))
            elif t == "duplicate":
                fix = ("FLAGGED: duplicate differs across projects — exactly 50% common, owner review (F-11)"
                       if iss.get("plan") else
                       "FLAGGED: duplicate differs across projects — promote shared base + custom deltas (review)")''',
'F-11 shared base')
