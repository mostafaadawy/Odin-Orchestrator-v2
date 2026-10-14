#!/usr/bin/env python3
"""Fix #2e (found by S8 r2): the text safety net guards against a false PASS only. A proposal waiting for approval
is not 'Confirmed', so the reviewer wrote 'Needs fix:' while its verdict field correctly said WAITING_FOR_APPROVAL
(and the approval existed). The review prompt now offers 'Waiting:' as an opener, and the text net applies to
PASSED claims only."""
import pathlib, sys
R = pathlib.Path(__file__).resolve().parent.parent
api = R / "server/api_v2.py"; a = api.read_text()
if "FIX #2e" in a: sys.exit("already applied")
def rep(old, new, name):
    global a
    assert a.count(old) == 1, f"anchor {name}: {a.count(old)}"
    a = a.replace(old, new)
rep('''    if _review_verdict(review) == "needs_fix" and pv["verdict"] != "NOT_DONE":''',
    '''    if _review_verdict(review) == "needs_fix" and pv["verdict"] == "PASSED":   # FIX #2e: guards a false PASS only''', "net")
rep('''                "done correctly, otherwise start with 'Needs fix:' and say what. Be specific and brief. "''',
    '''                "done correctly, with 'Waiting:' if it is a correct proposal that now waits for the owner's "
                "approval, otherwise start with 'Needs fix:' and say what. Be specific and brief. "''', "prompt")
api.write_text(a); print("fix #2e applied")
