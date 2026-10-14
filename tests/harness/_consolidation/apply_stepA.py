"""Step A (F-27, F-28, F-29, F-30, F-31) code changes. F-25 is a data change (stepA_f25.py)."""
import pathlib
def patch(path, a, b, n=1):
    p = pathlib.Path(path); s = p.read_text(); assert s.count(a) == n, (path, s.count(a), a[:70]); p.write_text(s.replace(a, b))
A = "server/api_v2.py"
# ---- F-27: a scheduled / ▶ Run project-level run is ALWAYS a team run
patch(A, """        _RUNS[pid] = {"running": True, "cancel": False, "goal": goal, "started": time.time()}
    _bg_orchestrate(pid, goal)   # drains synchronously; clears running in its finally""",
"""        # F-27: a scheduled / ▶ Run project-level run (no single assignee) is ALWAYS a TEAM run
        _RUNS[pid] = {"running": True, "cancel": False, "goal": goal, "started": time.time(), "force_team": True}
    _bg_orchestrate(pid, goal)   # drains synchronously; clears running in its finally""")
patch(A, """        _cls = _intent.classify_request(goal, engine=getattr(projects, "_engine", None))
        _forbid = set(_cls.get("forbid") or [])""",
"""        _cls = _intent.classify_request(goal, engine=getattr(projects, "_engine", None))
        if _cls.get("mode") == "direct" and (_RUNS.get(pid) or {}).get("force_team"):
            # F-27: a recurring/scheduled project run is a TEAM run, never one member doing everything.
            # The owner's exclusions (forbid, e.g. 'do not deploy') still apply.
            _cls = {**_cls, "mode": "orchestrate", "reason": "scheduled/recurring project run = team run"}
        _forbid = set(_cls.get("forbid") or [])""")
# ---- F-28: never re-add what the owner excluded or what is not in the owner's request
patch(A, """            try:
                _missing = projects.check_plan_coverage(_req_src, steps)
            except Exception:
                _missing = []""",
"""            try:
                _missing = projects.check_plan_coverage(_req_src, steps)
            except Exception:
                _missing = []
            _missing, _skipped = _filter_missing(_req_src, _missing, _forbid)   # F-28
            if _skipped:
                scopes.add_message(pscope, run_chat["id"], "assistant",
                                   "[Project CTO] Not re-adding (you excluded it, or it is not in your request): "
                                   + "; ".join(_skipped[:6]))""")
patch(A, """def _direct_member(pid: str, goal: str) -> str:""",
'''_EXCL_WORDS = {"deploy": ("deploy", "rsync", "reboot", "restart the server", "migrat", "production", "the vm", "on the vm", "to the vm", "azure"),
               "db_rebase": ("rebase", "reseed", "re-seed", "seed the", "drop the database", "reset the database")}


def _filter_missing(request: str, missing: list, forbid) -> tuple:
    """F-28: the coverage gate may only re-add parts of the OWNER'S REQUEST that the plan missed — never an
    action the owner excluded (forbid, e.g. 'do not deploy') and never something that is not in the request
    (e.g. taken from the project brief). Returns (keep, skipped)."""
    import re as _re
    req = (request or "").lower()
    req_words = set(_re.findall(r"[a-z0-9]{4,}", req))
    keep, skipped = [], []
    for m in missing or []:
        ml = str(m).lower()
        if any(w in ml for f in (forbid or ()) for w in _EXCL_WORDS.get(str(f).lower(), (str(f).lower(),))):
            skipped.append(f"{m} (you excluded it)"); continue
        words = set(_re.findall(r"[a-z0-9]{4,}", ml))
        if words and len(words & req_words) / len(words) < 0.5:
            skipped.append(f"{m} (not in your request)"); continue
        keep.append(m)
    return keep, skipped


_STATUS_OTHER = ("shipping", "shipment", "order", "tracking", "payment", "delivery", "parcel", "invoice",
                 "customer", "account", "subscription", "email", "campaign", "profile", "stock", "inventory")
_COMPLAINT = ("not ", "n't", "never", "violation", "voilation", "wrong", "stop", "why ", "complain", "i will not",
              "didnt", "dont", "you said")


def _is_run_status_question(text: str) -> bool:
    """F-29: only a plain question about THIS project's run/deploy gets the deterministic status answer —
    never a complaint, a negation, or a question about some other status (shipping, order, tracking …)."""
    import re as _re
    t = (text or "").strip().lower()
    if not t or len(t) >= 90:
        return False
    if not _re.search(r"(^\\s*\\?+\\s*$)|\\b(status|result|results|is it (done|finished|complete|over|online)|"
                      r"did it (finish|work|run|deploy)|what'?s?\\s+(the\\s+)?status|where (are we|is it))\\b", t):
        return False
    if any(c in t for c in _COMPLAINT):
        return False
    if any(_re.search(r"\\b" + w + r"\\w*\\s+status\\b", t) or _re.search(r"\\bstatus of (the |my |our )?" + w, t)
           for w in _STATUS_OTHER):
        return False
    return True


_INFLIGHT = {}
_INFLIGHT_TTL = 600


def _inflight_claim(scope: str, text: str) -> float:
    """F-30: the SAME owner message in the SAME chat while the first is still being handled is not started
    twice. Returns 0 if claimed (go ahead), else the start time of the turn already handling it."""
    import re as _re
    key = (scope, _re.sub(r"\\s+", " ", (text or "").strip().lower()))
    now = time.time()
    for k in [k for k, t0 in _INFLIGHT.items() if now - t0 > _INFLIGHT_TTL]:
        _INFLIGHT.pop(k, None)
    if key in _INFLIGHT:
        return _INFLIGHT[key]
    _INFLIGHT[key] = now
    return 0.0


def _inflight_release(scope: str, text: str) -> None:
    import re as _re
    _INFLIGHT.pop((scope, _re.sub(r"\\s+", " ", (text or "").strip().lower())), None)


def _direct_member(pid: str, goal: str) -> str:''')
# F-29: use the stricter check
patch(A, """        if scope.startswith("project:") and len(text or "") < 90:
            import re as _re3
            if _re3.search(""", """        if scope.startswith("project:") and _is_run_status_question(text):   # F-29
            import re as _re3
            if _re3.search(""")
# F-30: guard before the heavy path; release when the reply is stored
patch(A, """        # PROJECT CTO chat: a build/change/test request runs the FULL team pipeline""",
"""        # F-30: the same owner message already being handled in this chat is not started a second time
        if not str(text or "").lstrip().startswith("["):
            _t_in = _inflight_claim(scope, text)
            if _t_in:
                msg = (f"⏳ I'm already working on this exact message (started {int(time.time() - _t_in)} s ago) — "
                       "not starting it twice. You'll see the answer here when it's done.")
                scopes.add_message(scope, cid, "assistant", msg)
                yield sse("token", {"t": msg})
                yield sse("done", {"scope": scope, "cid": cid, "member": None,
                                   "approval": {"required": False, "categories": []}, "lang": lang})
                return

        # PROJECT CTO chat: a build/change/test request runs the FULL team pipeline""")
patch(A, """        scopes.add_message(scope, cid, "assistant", reply or "")
        # If the agent PROPOSED changes in this chat""", """        scopes.add_message(scope, cid, "assistant", reply or "")
        _inflight_release(scope, text)   # F-30
        # If the agent PROPOSED changes in this chat""")
# ---- F-31: never an empty reason; a gated scheduled run says honestly that it did NOT run
patch("orchestrator/dispatcher.py", """        if d["approval"]["required"]:
            cats = ", ".join(d["approval"]["categories"])""", """        if d["approval"]["required"]:
            # F-31: never an empty reason
            cats = (", ".join(d["approval"]["categories"]) or str(d["approval"].get("why") or "").strip()
                    or "it would change files or state")""")
patch("server/scheduler.py", """        reply = "(engine unavailable)"
        try:
            from dispatcher import default_dispatcher as d  # type: ignore
            reply = d.respond(prompt, lang="en")
        except Exception as e:
            reply = f"(scheduler engine error: {e})"
        scopes.add_message(scope_id, cid, "assistant", reply)""", """        reply = "(engine unavailable)"
        _gated = None
        try:
            from dispatcher import default_dispatcher as d  # type: ignore
            _dec = d.route(prompt, lang="en")
            if (_dec.get("approval") or {}).get("required"):
                # F-31: a gated scheduled run is NOT silently "waiting" — say plainly that it did NOT run, why,
                # and how to run it; nothing is prepared behind the owner's back.
                _why = (", ".join(_dec["approval"].get("categories") or []) or str(_dec["approval"].get("why") or "").strip()
                        or "it would change files or state")
                _gated = _why
                reply = (f"⏸ This scheduled run did NOT execute: it is a {_dec.get('leadAgent')} task that needs your "
                         f"approval ({_why}). Nothing was changed and no approval was prepared automatically. "
                         "Press ▶ Run to run it as a team run with the normal approval gates, or tell me to change the task.")
            else:
                reply = d.respond(prompt, lang="en")
        except Exception as e:
            reply = f"(scheduler engine error: {e})"
        scopes.add_message(scope_id, cid, "assistant", reply)
        if _gated:
            try:
                import notifications_store as _nt  # type: ignore
                _nt.add("attention", f"⏸ {_pname if '_pname' in dir() else t['pid']}: scheduled run did not execute",
                        body=f"{t.get('title', '')} — needs your approval ({_gated})", pid=t["pid"], cid=cid,
                        severity="attention", icon="⏸")
            except Exception:
                pass""")
print("patched all")
