#!/usr/bin/env python3
"""Apply fix #2 (G1 false success + the 13 group-A chat mismatches). Exact-anchor edits; aborts if any
anchor is missing or not unique. Idempotent guard: refuses to run twice."""
import pathlib, sys
R = pathlib.Path(__file__).resolve().parent.parent
api = R / "server/api_v2.py"; soc = R / "server/soc_run.py"
a = api.read_text(); s = soc.read_text()
if "FIX #2 (G1" in a:
    sys.exit("fix #2 already applied")

def rep(txt, old, new, name):
    assert txt.count(old) == 1, f"anchor not unique/missing: {name} ({txt.count(old)})"
    return txt.replace(old, new)

# ---------- 1) module-level review verdict helper ----------
helper = '''

def _review_verdict(review) -> str:
    """FIX #2 (G1, 2026-10-11): read the Project CTO review instead of ignoring it.
    'confirmed' ONLY when the review starts with 'Confirmed:' (markdown/emoji/quotes tolerated);
    'needs_fix' when it starts with 'Needs fix'; anything else (empty, error, hedged) is 'unclear',
    and unclear is NEVER a pass."""
    t = re.sub(r"^[\\s>*_`#\\"'\\u2705\\u26a0\\ufe0f\\u274c\\U0001F50E:-]+", "", str(review or "")).lower()
    if t.startswith("confirmed"):
        return "confirmed"
    if t.startswith("needs fix") or t.startswith("needs-fix") or t.startswith("needs a fix"):
        return "needs_fix"
    return "unclear"


def _vm_needs_root(cmd: str) -> bool:'''
a = rep(a, "\n\ndef _vm_needs_root(cmd: str) -> bool:", helper, "helper")

# ---------- 2) review prompt asks for evidence; injected values are not evidence (CH0-5) ----------
a = rep(a, '''"done correctly, otherwise start with 'Needs fix:' and say what. Be specific and brief.",''',
 '''"done correctly, otherwise start with 'Needs fix:' and say what. Be specific and brief. "
                "When you confirm, cite the evidence from the report (a file path, a command output or a test "
                "result). Values that were only injected into the brief or mandate (live connector facts, "
                "numbers you were given) are NOT evidence that the work was done; a claim with no evidence "
                "(e.g. 'only GET calls were made', 'rebooted', 'gap closed', 'captured live') is 'Needs fix:'.",''',
 "review prompt")

# ---------- 3) deliverable 'done' flag follows the same rule ----------
a = rep(a, "main_task.write_deliverable(pid, member, (reply or \"\").strip(), done=(step_clean))",
        "main_task.write_deliverable(pid, member, (reply or \"\").strip(), done=(step_clean and _review_verdict(review) == \"confirmed\"))",
        "write_deliverable")

# ---------- 4) failed_steps register ----------
a = rep(a, "        passed_members = []   # members whose part PASSED QA (for dependency waits)\n",
        "        passed_members = []   # members whose part PASSED QA (for dependency waits)\n"
        "        failed_steps = []     # FIX #2 (G1): every step NOT confirmed (review/audit/QA), reported in the verdict\n",
        "passed_members init")

# ---------- 5) step acceptance = review confirmed + audit clean + QA (when it ran) ----------
old5 = '''            if qa_ok and step_clean:
                passed_members.append(member)
            scopes.sync_up(mscope, f"{member} delivered; QA: {'passed' if qa_ok else 'failed'}; audit: {'clean' if step_clean else 'flagged'}")'''
new5 = '''            # FIX #2 (G1, 2026-10-11): a step passes ONLY when the CTO review CONFIRMS it, the audit eye found
            # real clean work (evidence), and QA passed when QA ran. The review was previously ignored.
            _qa_ran = bool(qa_enabled) and not _skip_qa_gate
            _rv = _review_verdict(review)
            ok_step = (_rv == "confirmed") and bool(step_clean) and bool(qa_ok)
            if ok_step:
                passed_members.append(member)
            else:
                failed_steps.append({"member": member, "review": _rv, "audit": bool(step_clean),
                                     "qa": (bool(qa_ok) if _qa_ran else None)})
            _qa_txt = ("passed" if qa_ok else "failed") if _qa_ran else "skipped"
            scopes.sync_up(mscope, f"{member} delivered; review: {_rv}; QA: {_qa_txt}; audit: {'clean' if step_clean else 'flagged'}")'''
a = rep(a, old5, new5, "acceptance")

# ---------- 6) honest step messages (CH4-5) ----------
old6 = '''            ok_step = qa_ok and step_clean
            scopes.add_message(pscope, run_chat["id"], "assistant",
                               f"[{member} → Project CTO] {'✅ passed (QA + audit clean)' if ok_step else '⚠️ flagged — QA/audit issues'}. {concl[:260]}")
            yield sse("status", {"icon": "✅" if ok_step else "⚠️", "text": f"{member}'s part {'passed (QA+audit)' if ok_step else 'still has issues'}"})
            yield sse("step_done", {"member": member, "step": idx + 1,
                                    "result": (("✅ QA passed. " if qa_ok else "⚠️ QA issues remain. ") + (review or ""))[:400]})'''
new6 = '''            _basis = "review confirmed + QA + audit clean" if _qa_ran else "review confirmed + audit clean; QA skipped"
            _why = ", ".join(x for x in (("review " + _rv.replace("_", " ")) if _rv != "confirmed" else "",
                                         "" if step_clean else "audit flagged",
                                         "QA failed" if (_qa_ran and not qa_ok) else "") if x)
            scopes.add_message(pscope, run_chat["id"], "assistant",
                               f"[{member} → Project CTO] {('✅ passed (' + _basis + ')') if ok_step else ('⚠️ NOT passed — ' + _why)}. {concl[:260]}")
            yield sse("status", {"icon": "✅" if ok_step else "⚠️", "text": f"{member}'s part {('passed (' + _basis + ')') if ok_step else ('still has issues — ' + _why)}"})
            _qa_lbl = ("✅ QA passed. " if qa_ok else "⚠️ QA issues remain. ") if _qa_ran else "QA skipped. "
            yield sse("step_done", {"member": member, "step": idx + 1,
                                    "result": (_qa_lbl + (review or ""))[:400]})'''
a = rep(a, old6, new6, "messages")

# ---------- 7) run result: required with QA off too ----------
a = rep(a, "        all_ok = len(passed_members) >= len([s for s in steps if s]) if qa_enabled else True\n",
        "        # FIX #2 (G1): every step must have passed (review + audit + QA when on) — ALSO when QA is off.\n"
        "        all_ok = (len(passed_members) >= len([s for s in steps if s])) and not failed_steps\n",
        "all_ok")

# ---------- 8) engine-failure guard: members' work only; add 401 markers (CH2-3, CH3-3) ----------
a = rep(a, '''        _engine_fail_markers = ("oauth access token has expired", "re-authenticate to continue", "hit your weekly limit")''',
        '''        _engine_fail_markers = ("oauth access token has expired", "re-authenticate to continue", "hit your weekly limit",
                                "api error: 401", "authentication_error")''', "markers")
a = rep(a, '''            _efblob = ("\\n".join(str(_d) for _d in (deliverables or {}).values()) + "\\n" + "\\n".join(str(_r.get("review") or "") for _r in (results or []))).lower()''',
        '''            # FIX #2: scan the members' OWN output only — a review that merely mentions an expired login
            # must not fail a confirmed run (CH3-3).
            _efblob = "\\n".join(str(_d) for _d in (deliverables or {}).values()).lower()''', "efblob")

# ---------- 9) a verified deploy no longer hides another member's open step ----------
a = rep(a, "        if _deploy_ok:\n            all_ok = True\n",
        "        _open_non_deploy = [f for f in failed_steps if not _is_devops(pid, f[\"member\"])]\n"
        "        if _deploy_ok and not _open_non_deploy:   # FIX #2: deploy evidence covers the deploy step only\n"
        "            all_ok = True\n", "deploy override")

# ---------- 10) final verdict lists what is not confirmed ----------
old10 = '''            verdict = "Everything builds and passed QA ✅" if (qa_enabled and all_ok) else \\
                      ("Some parts still have QA issues ⚠️" if qa_enabled else "All requirements addressed ✅")'''
new10 = '''            if all_ok:
                verdict = "Everything builds and passed QA ✅" if qa_enabled else "All requirements addressed ✅"
            else:   # FIX #2 (G1): never claim success; name every step that is not confirmed
                _ns = "; ".join(f"{f['member']} (" + ", ".join(x for x in (
                    ("review " + f["review"].replace("_", " ")) if f["review"] != "confirmed" else "",
                    "" if f["audit"] else "audit flagged",
                    "QA failed" if f["qa"] is False else "") if x) + ")" for f in failed_steps[:6])
                verdict = (f"⚠️ Not done — {len(failed_steps)} step(s) not confirmed: {_ns}" if failed_steps
                           else "⚠️ Not done — the run stopped before every step completed")'''
a = rep(a, old10, new10, "verdict")

# ---------- 11) SOC: auto-resolve only what was actually re-checked (CH4-4) ----------
s = rep(s, "def _reconcile(pid, issues_this_run):\n",
        "def _reconcile(pid, issues_this_run, checked_ids=None):\n", "reconcile sig")
s = rep(s, '''        if fid not in seen and it.get("owner_status") in ("open", None) and not it.get("resolved_ts"):''',
        '''        # FIX #2 (CH4-4): only a check that actually RAN and reported 'Checked …' this run can resolve its
        # finding. A finding whose check did not run (quick run, data unavailable) stays open.
        if (fid not in seen and it.get("owner_status") in ("open", None) and not it.get("resolved_ts")
                and checked_ids is not None and fid not in checked_ids):
            continue
        if fid not in seen and it.get("owner_status") in ("open", None) and not it.get("resolved_ts"):''',
        "auto-resolve")
s = rep(s, "    sections = _reconcile(pid, issues)\n",
        "    _checked = {f[\"id\"] for f in findings if str(f.get(\"data_source_state\", \"\")).startswith(\"Checked\")}\n"
        "    sections = _reconcile(pid, issues, checked_ids=_checked)\n", "reconcile call")

# ---------- 12) SOC-APP-001: no parsable counts is 'Data unavailable', never 'healthy' (CH4-1) ----------
old12 = '''    top = out.strip().splitlines()[0].split()
    cnt = int(top[0]) if top and top[0].isdigit() else 0'''
new12 = '''    # FIX #2 (CH4-1): a sudo prompt / error text is NOT "0 submissions". Only `uniq -c` lines count.
    _rows = [l.split() for l in out.strip().splitlines() if re.match(r"^\\s*\\d+\\s+\\S+", l)]
    if not _rows:
        return _finding("SOC-APP-001", "Newsletter/registration abuse", "medium", "low", "Needs Review",
                        "nginx access log", f"no parsable per-IP counts (output: {out[:100]})",
                        "cannot conclude healthy from unparsable data", "Data unavailable")
    top = _rows[0]
    cnt = int(top[0])'''
s = rep(s, old12, new12, "soc-app-001")

api.write_text(a); soc.write_text(s)
print("fix #2 applied: api_v2.py + soc_run.py")
