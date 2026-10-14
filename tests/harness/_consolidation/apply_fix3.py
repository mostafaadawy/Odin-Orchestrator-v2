#!/usr/bin/env python3
"""Fix #3 (F-23, approval bypass). Owner rules (2026-10-11):
 (1) "approve" applies ONLY to the proposal it refers to: by ID, or the one being replied to (reply_to);
 (2) only the OWNER's messages can approve — never Odin's own messages, follow-ups or agents;
 (3) older pending proposals stay pending until approved or rejected individually;
 (4) a test reproduces the 34-second case and proves it can no longer happen.
Root cause: _scoped_gen() approved ALL pending approvals whenever ANY text contained "approve(d)". The
post-apply auto-continue posts "[system] The gate you proposed was APPROVED and applied…" into the project chat
through _scoped_gen() → every other pending proposal was approved and applied (S2 r5: dc13fbd7, 34 s later)."""
import pathlib, sys
R = pathlib.Path(__file__).resolve().parent.parent
api = R / "server/api_v2.py"; a = api.read_text()
if "FIX #3 (F-23" in a: sys.exit("already applied")
def rep(old, new, name):
    global a
    assert a.count(old) == 1, f"anchor {name}: {a.count(old)}"
    a = a.replace(old, new)
rep('''    def scope_stream(scope: str, text: str, lang: str = "en", cid: str = ""):
        return StreamingResponse(_scoped_gen(scope, text, lang, cid),''',
    '''    def scope_stream(scope: str, text: str, lang: str = "en", cid: str = "", reply_to: str = ""):
        # FIX #3 (F-23): this endpoint is the OWNER's chat; internal callers never set from_owner.
        return StreamingResponse(_scoped_gen(scope, text, lang, cid, from_owner=True, reply_to=reply_to),''', "endpoint")
rep("def _scoped_gen(scope: str, text: str, lang: str, cid: str):",
    "def _scoped_gen(scope: str, text: str, lang: str, cid: str, from_owner: bool = False, reply_to: str = \"\"):", "sig")
rep('''        # Saying "approve" in the chat = the same as clicking Approve on the popup. It approves ALL
        # pending changes for this project AND re-fires any approved-but-not-applied ones, so it
        # ALWAYS takes effect — you never have to ask 7-8 times.
        if scope.startswith("project:"):
            import re as _re2
            if _re2.search(r"\\b(i\\s+)?(approve|approved|accept|accepted|approve all|run it|go ahead and run)\\b", text, _re2.I):
                _pid = scope.split(":", 1)[1]
                fired = 0
                for ap in approvals.list_pending(_pid):
                    approvals.decide(ap["id"], True)
                for ap in approvals.list_for(_pid):
                    if ap.get("status") == "approved" and not ap.get("applied"):
                        threading.Thread(target=_apply_approval_bg, args=(ap["id"],), daemon=True).start()
                        fired += 1
                msg = (f"✅ Approved — running {fired} change(s) now; results appear in the member chats."
                       if fired else "Nothing is pending approval right now.")''',
'''        # FIX #3 (F-23, 2026-10-11): saying "approve" in the chat approves ONLY the proposal it names (its id)
        # or the one being replied to (reply_to) — never "all pending". Only the OWNER's own chat message can
        # approve (from_owner, set only by the /scope/stream endpoint); Odin's own follow-ups ("[system] … APPROVED
        # and applied …"), agents and internal callers never can. Other pending proposals stay pending.
        _txt0 = str(text or "").lstrip()
        if scope.startswith("project:") and from_owner and not _txt0.startswith("["):
            import re as _re2
            if _re2.search(r"\\b(i\\s+)?(approve|approved|accept|accepted|approve all|run it|go ahead and run)\\b", text, _re2.I):
                _pid = scope.split(":", 1)[1]
                _pend = approvals.list_pending(_pid)
                _ids = set(_re2.findall(r"\\b[0-9a-f]{12}\\b", (text or "").lower()))
                if reply_to:
                    _ids.add(str(reply_to).strip().lower())
                _targets = [ap for ap in _pend if ap["id"] in _ids]
                _refire = [ap for ap in approvals.list_for(_pid, limit=500)
                           if ap["id"] in _ids and ap.get("status") == "approved" and not ap.get("applied")]
                fired = 0
                for ap in _targets:
                    approvals.decide(ap["id"], True, "owner chat approval (by id)")
                for ap in _targets + _refire:
                    threading.Thread(target=_apply_approval_bg, args=(ap["id"],), daemon=True).start()
                    fired += 1
                if fired:
                    msg = (f"✅ Approved {', '.join(ap['id'] for ap in _targets + _refire)} — running now. "
                           + (f"{len(_pend) - len(_targets)} other proposal(s) stay pending." if len(_pend) > len(_targets) else ""))
                elif _pend:
                    msg = ("Which proposal? An approval applies to ONE proposal. Reply \\"approve <id>\\" "
                           "(or use Approve on its popup):\\n" + "\\n".join(
                               f"• {ap['id']} — {ap.get('member', '')}: {str(ap.get('title', ''))[:70]}" for ap in _pend[:12]))
                else:
                    msg = "Nothing is pending approval right now."''', "block")
api.write_text(a); print("fix #3 applied")
