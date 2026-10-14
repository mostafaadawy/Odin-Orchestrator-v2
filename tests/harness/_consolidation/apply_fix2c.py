#!/usr/bin/env python3
"""Fix #2c (owner review 2026-10-11): pass/fail from a FIXED verdict field, accepted only when evidence agrees.
  review → VERDICT: {"verdict": PASSED|NOT_DONE|WAITING_FOR_APPROVAL, "evidence_files": [...], "reason": "..."}
  PASSED accepted only if: expected files exist (+ changed during the step) and are registered in odin_core
  (workspace files) or lie in the project's own folder; audit clean; QA passed when it ran.
  WAITING_FOR_APPROVAL accepted only if this project has an approval created during the step that is pending.
  The old text check stays as a safety net ("Needs fix" anywhere → NOT_DONE).
Exact-anchor edits on top of fix #2/#2b; aborts on any missing anchor."""
import pathlib, sys
R = pathlib.Path(__file__).resolve().parent.parent
api = R / "server/api_v2.py"; a = api.read_text()
if "FIX #2c" in a:
    sys.exit("fix #2c already applied")
def rep(old, new, name):
    global a
    assert a.count(old) == 1, f"anchor {name}: {a.count(old)}"
    a = a.replace(old, new)

# 1) helpers after _review_verdict
rep('''    return "unclear"


def _vm_needs_root(cmd: str) -> bool:''', '''    return "unclear"


_BUILDISH = re.compile(r"\\b(build|implement|creat\\w*|develop|scaffold|write|add|fix|updat\\w*|generat\\w*|refactor)\\b", re.I)


def _parse_verdict(review) -> dict:
    """FIX #2c: read the FIXED verdict field the review must end with. Missing/invalid → NOT_DONE."""
    txt = str(review or "")
    for m in reversed(list(re.finditer(r"VERDICT\\s*:\\s*(\\{.*?\\})\\s*(?:$|\\n)", txt, re.S))):
        try:
            d = json.loads(m.group(1))
        except Exception:
            continue
        v = str(d.get("verdict", "")).strip().upper()
        if v in ("PASSED", "NOT_DONE", "WAITING_FOR_APPROVAL"):
            ev = d.get("evidence_files") or []
            return {"verdict": v, "evidence_files": [str(x) for x in ev if str(x).strip()][:20],
                    "reason": str(d.get("reason", ""))[:300], "parsed": True}
    return {"verdict": "NOT_DONE", "evidence_files": [], "reason": "no valid VERDICT field in the review",
            "parsed": False}


def _step_outcome(pid: str, task: str, review, step_clean: bool, qa_ok: bool, qa_ran: bool,
                  step_t0: float, folder: str = "") -> tuple:
    """FIX #2c (G1): the step outcome is the review's FIXED verdict, accepted only when the evidence agrees.
    Returns (outcome, detail). outcome ∈ PASSED | NOT_DONE | WAITING_FOR_APPROVAL."""
    pv = _parse_verdict(review)
    det = {"claimed": pv["verdict"], "parsed": pv["parsed"], "reason": pv["reason"], "checks": []}
    def no(why):
        det["checks"].append(why); return "NOT_DONE", det
    # safety net (text): a review that says "Needs fix" anywhere is never a pass
    if _review_verdict(review) == "needs_fix" and pv["verdict"] != "NOT_DONE":
        return no("text says 'Needs fix' — contradicts the verdict field")
    if pv["verdict"] == "NOT_DONE":
        return no("review verdict NOT_DONE" + ("" if pv["parsed"] else " (no valid verdict field)"))
    if not step_clean:
        return no("audit eye flagged this step")
    if pv["verdict"] == "WAITING_FOR_APPROVAL":
        try:
            import approvals as _ap
            mine = [x for x in _ap.list_pending(pid) if float(x.get("created") or 0) >= step_t0 - 5]
        except Exception:
            mine = []
        if not mine:
            return no("claims WAITING_FOR_APPROVAL but no approval was created for this project in this step")
        det["approvals"] = [x.get("id") for x in mine]
        return "WAITING_FOR_APPROVAL", det
    # PASSED
    if qa_ran and not qa_ok:
        return no("QA ran and failed")
    proj = (ROOT / "workspace" / "projects" / pid).resolve()
    own = pathlib.Path(os.path.expanduser(folder)).resolve() if folder else None
    ok_files, changed = [], 0
    conn = None
    try:
        import workspace_mw as _mw
        conn = _mw._db()
    except Exception:
        _mw = None
    for raw in pv["evidence_files"]:
        cands = [pathlib.Path(os.path.expanduser(raw))]
        if not cands[0].is_absolute():
            cands = [ROOT / raw, proj / raw] + ([own / raw] if own else [])
        p = next((c.resolve() for c in cands if c.is_file()), None)
        if p is None:
            return no(f"expected file missing: {raw}")
        if p.stat().st_mtime >= step_t0 - 5:
            changed += 1
        ws = (ROOT / "workspace").resolve()
        if ws in p.parents:
            reg = False
            try:
                if _mw:
                    _mw.sync_row(p)          # register through the single door (true owner inferred)
                if conn:
                    cu = conn.cursor(); cu.execute("SELECT 1 FROM files WHERE path=%s", (str(p.relative_to(ROOT)),))
                    reg = cu.fetchone() is not None
            except Exception:
                reg = False
            if not reg:
                return no(f"file not registered in odin_core: {raw}")
        elif not (own and (p == own or own in p.parents)):
            return no(f"file outside the workspace and outside this project's folder: {raw}")
        ok_files.append(str(p))
    try:
        if conn: conn.close()
    except Exception:
        pass
    det["evidence_ok"] = ok_files
    if _BUILDISH.search(task or "") and (not ok_files or changed == 0):
        return no("build/write task but no evidence file was created or changed during this step")
    return "PASSED", det


def _vm_needs_root(cmd: str) -> bool:''', "helpers")

# 2) review prompt: demand the fixed verdict field
rep('''"(e.g. 'only GET calls were made', 'rebooted', 'gap closed', 'captured live') is 'Needs fix:'.",''',
'''"(e.g. 'only GET calls were made', 'rebooted', 'gap closed', 'captured live') is 'Needs fix:'.\\n"
                "Then END with exactly ONE line: VERDICT: {\\"verdict\\": \\"PASSED\\" | \\"NOT_DONE\\" | "
                "\\"WAITING_FOR_APPROVAL\\", \\"evidence_files\\": [paths of the files this work created or "
                "changed], \\"reason\\": \\"one sentence\\"}. PASSED only if the work is really done and on disk; "
                "WAITING_FOR_APPROVAL only if the work is a proposal that now waits for the owner's approval; "
                "otherwise NOT_DONE.",''', "prompt")

# 3) record step start time
rep('''            deps = step.get("depends_on") or []\n''',
    '''            deps = step.get("depends_on") or []\n            _step_t0 = time.time()   # FIX #2c: evidence must come from THIS step\n''', "t0")

# 4) the first deliverable write is provisional; the final one follows the outcome
rep('''done=(step_clean and _review_verdict(review) == "confirmed"))''', '''done=False)   # FIX #2c: final flag set after the outcome''', "deliv")

# 5) acceptance
rep('''            _qa_ran = bool(qa_enabled) and not _skip_qa_gate
            _rv = _review_verdict(review)
            ok_step = (_rv == "confirmed") and bool(step_clean) and bool(qa_ok)
            if ok_step:
                passed_members.append(member)
            else:
                failed_steps.append({"member": member, "review": _rv, "audit": bool(step_clean),
                                     "qa": (bool(qa_ok) if _qa_ran else None)})
            _qa_txt = ("passed" if qa_ok else "failed") if _qa_ran else "skipped"
            scopes.sync_up(mscope, f"{member} delivered; review: {_rv}; QA: {_qa_txt}; audit: {'clean' if step_clean else 'flagged'}")''',
'''            _qa_ran = bool(qa_enabled) and not _skip_qa_gate
            # FIX #2c: outcome = the review's FIXED verdict field, accepted only when the evidence agrees
            _outc, _odet = _step_outcome(pid, task, review, bool(step_clean), bool(qa_ok), _qa_ran,
                                         _step_t0, folder)
            ok_step = (_outc == "PASSED")
            _rv = _outc
            if ok_step:
                passed_members.append(member)
            elif _outc == "WAITING_FOR_APPROVAL":
                waiting_steps.append({"member": member, "approvals": _odet.get("approvals", [])})
            else:
                failed_steps.append({"member": member, "review": "not done", "audit": bool(step_clean),
                                     "qa": (bool(qa_ok) if _qa_ran else None),
                                     "why": "; ".join(_odet.get("checks", []))[:200]})
            try:
                import main_task as _mtf
                _mtf.write_deliverable(pid, member, (reply or "").strip(), done=ok_step)
                _mtf.append(pid, "Outcome check", f"{member}: {_outc} — {json.dumps(_odet, ensure_ascii=False)[:600]}")
            except Exception:
                pass
            _qa_txt = ("passed" if qa_ok else "failed") if _qa_ran else "skipped"
            scopes.sync_up(mscope, f"{member} delivered; outcome: {_outc}; QA: {_qa_txt}; audit: {'clean' if step_clean else 'flagged'}")''', "accept")

# 6) messages
rep('''            _basis = "review confirmed + QA + audit clean" if _qa_ran else "review confirmed + audit clean; QA skipped"
            _why = ", ".join(x for x in (("review " + _rv.replace("_", " ")) if _rv != "confirmed" else "",
                                         "" if step_clean else "audit flagged",
                                         "QA failed" if (_qa_ran and not qa_ok) else "") if x)''',
'''            _basis = ("verdict PASSED + files verified + QA + audit clean" if _qa_ran
                      else "verdict PASSED + files verified + audit clean; QA skipped")
            _why = ("waiting for your approval" if _outc == "WAITING_FOR_APPROVAL"
                    else ("; ".join(_odet.get("checks", [])) or "not done"))''', "msgs")
rep('''{('✅ passed (' + _basis + ')') if ok_step else ('⚠️ NOT passed — ' + _why)}. {concl[:260]}")''',
    '''{('✅ passed (' + _basis + ')') if ok_step else (('⏳ ' if _outc == 'WAITING_FOR_APPROVAL' else '⚠️ NOT passed — ') + _why)}. {concl[:260]}")''', "msg1")
rep('''yield sse("status", {"icon": "✅" if ok_step else "⚠️", "text": f"{member}'s part {('passed (' + _basis + ')') if ok_step else ('still has issues — ' + _why)}"})''',
    '''yield sse("status", {"icon": "✅" if ok_step else ("⏳" if _outc == "WAITING_FOR_APPROVAL" else "⚠️"), "text": f"{member}'s part {('passed (' + _basis + ')') if ok_step else (('is ' + _why) if _outc == 'WAITING_FOR_APPROVAL' else ('still has issues — ' + _why))}"})''', "msg2")
rep('''                                    "result": (_qa_lbl + (review or ""))[:400]})''',
    '''                                    "result": (_qa_lbl + (review or ""))[:400], "outcome": _outc})''', "msg3")

# 7) waiting register + run result
rep('''        failed_steps = []     # FIX #2 (G1): every step NOT confirmed (review/audit/QA), reported in the verdict\n''',
    '''        failed_steps = []     # FIX #2 (G1): every step NOT confirmed (review/audit/QA), reported in the verdict\n        waiting_steps = []    # FIX #2c: steps whose work is a proposal waiting for the owner's approval\n''', "waitinit")
rep('''        all_ok = (len(passed_members) >= len([s for s in steps if s])) and not failed_steps\n''',
    '''        all_ok = (len(passed_members) >= len([s for s in steps if s])) and not failed_steps and not waiting_steps\n        _run_outcome = "PASSED" if all_ok else ("WAITING_FOR_APPROVAL" if (waiting_steps and not failed_steps) else "NOT_DONE")\n''', "allok")
rep('''        elif _engine_failed:
            all_ok = False''', '''        elif _engine_failed:
            all_ok = False; _run_outcome = "NOT_DONE"''', "engine")
rep('''        elif open_reqs and not (bool(steps) and all((s.get("member") in passed_members) for s in steps if s)):''',
    '''        elif _run_outcome == "WAITING_FOR_APPROVAL":   # FIX #2c: honest "waiting", never "Not done"/"✅"
            verdict = ("⏳ Waiting for your approval — " + "; ".join(
                f"{w['member']} ({', '.join(w['approvals'][:3])})" for w in waiting_steps[:6]))
        elif open_reqs and not (bool(steps) and all((s.get("member") in passed_members) for s in steps if s)):''', "waitverdict")
rep('''            all_ok = False
            miss = "; ".join(r["text"][:70] for r in open_reqs[:6])''', '''            all_ok = False; _run_outcome = "NOT_DONE"
            miss = "; ".join(r["text"][:70] for r in open_reqs[:6])''', "openreq")
rep('''                _ns = "; ".join(f"{f['member']} (" + ", ".join(x for x in (
                    ("review " + f["review"].replace("_", " ")) if f["review"] != "confirmed" else "",
                    "" if f["audit"] else "audit flagged",
                    "QA failed" if f["qa"] is False else "") if x) + ")" for f in failed_steps[:6])''',
'''                _ns = "; ".join(f"{f['member']} ({f.get('why') or 'not done'})" for f in failed_steps[:6])''', "ns")
rep('''            all_ok = True
            verdict = "✅ Deploy verified successful''', '''            all_ok = True; _run_outcome = "PASSED"
            verdict = "✅ Deploy verified successful''', "deployok")
rep('''            _fin = "\\u2705 RUN FINISHED" if bool(all_ok) else "\\u23f9\\ufe0f RUN FINISHED (open items remain)"''',
    '''            _fin = ("\\u2705 RUN FINISHED" if bool(all_ok) else
                    ("\\u23f3 RUN FINISHED \\u2014 Waiting for your approval" if _run_outcome == "WAITING_FOR_APPROVAL"
                     else "\\u23f9\\ufe0f RUN FINISHED (open items remain)"))''', "fin")
rep('''        yield sse("done", {"pid": pid, "steps": total, "ok": bool(all_ok), "timing": _timing})''',
    '''        yield sse("done", {"pid": pid, "steps": total, "ok": bool(all_ok), "outcome": _run_outcome, "timing": _timing})''', "done")
api.write_text(a)
print("fix #2c applied")
