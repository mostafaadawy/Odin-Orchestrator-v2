#!/usr/bin/env python3
"""Fix #2d (found by S8 r1): work that is a PROPOSAL waiting for the owner's approval was rejected by the audit
eye's artifact gate as "zero files", re-proposed on every retry (3 duplicate approvals), halted as BUILD FAILED
and reported "Incomplete". Now: a pending approval created in this step clears ONLY the zero-files check, stops
the retries (no duplicates), skips the build halt, and tells the reviewer; the outcome can be WAITING_FOR_APPROVAL."""
import pathlib, sys
R = pathlib.Path(__file__).resolve().parent.parent
api = R / "server/api_v2.py"; a = api.read_text()
if "FIX #2d" in a: sys.exit("already applied")
def rep(old, new, name):
    global a
    assert a.count(old) == 1, f"anchor {name}: {a.count(old)}"
    a = a.replace(old, new)
rep("            _step_t0 = time.time()   # FIX #2c: evidence must come from THIS step\n",
    "            _step_t0 = time.time()   # FIX #2c: evidence must come from THIS step\n"
    "            _step_waiting, _wait_ids = False, []   # FIX #2d\n", "init")
rep("                    if _probs:\n                        step_clean = False\n",
    "                    # FIX #2d: a proposal now WAITING for the owner's approval is not 'zero files'.\n"
    "                    try:\n"
    "                        import approvals as _ap2\n"
    "                        _wn = [x for x in _ap2.list_pending(pid) if float(x.get('created') or 0) >= _step_t0 - 5]\n"
    "                    except Exception:\n"
    "                        _wn = []\n"
    "                    if _wn:\n"
    "                        _step_waiting, _wait_ids = True, [x.get('id') for x in _wn]\n"
    "                        _probs = [p for p in _probs if not p.startswith('you wrote ZERO real files')]\n"
    "                    if _probs:\n                        step_clean = False\n", "audit")
rep("                if step_clean:\n                    if _try > 1:",
    "                if _step_waiting:\n"
    "                    break   # FIX #2d: the work waits for the owner's approval — never re-propose (no duplicates)\n"
    "                if step_clean:\n                    if _try > 1:", "break")
rep("            if _is_build_step and not step_clean:", "            if _is_build_step and not step_clean and not _step_waiting:", "buildgate")
rep('''                f"Their report:\\n{(reply or '')[:1500]}\\nIn 1-3 sentences, REVIEW it: start with 'Confirmed:' if it's "''',
    '''                f"Their report:\\n{(reply or '')[:1500]}\\n"
                + (f"NOTE (system): this step created proposal(s) now WAITING for the owner's approval: "
                   f"{', '.join(_wait_ids)}. Nothing is applied until the owner approves.\\n" if _step_waiting else "")
                + f"In 1-3 sentences, REVIEW it: start with 'Confirmed:' if it's "''', "prompt")
rep("            _skip_qa_gate = _is_operational(pid, member) or (_is_devops(pid, member) and deploy_ctx)\n",
    "            _skip_qa_gate = _is_operational(pid, member) or (_is_devops(pid, member) and deploy_ctx) \\\n"
    "                or _step_waiting   # FIX #2d: nothing to test until the owner approves the proposal\n", "qa")
api.write_text(a); print("fix #2d applied")
