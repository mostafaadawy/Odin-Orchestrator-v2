"""
intent.py — INTELLIGENCE-FIRST routing for the orchestrator.

The whole point: the owner's ACTUAL message drives the work; the project brief is
CONSTRAINTS (guardrails enforced by middleware/audit/scopes), never a checklist to
complete on every turn. This module is the deterministic safety-net + decision core.
In production the engine (Claude) may refine the call, but these pure functions are
unit-tested and are what stop a scoped ask from exploding into the whole brief.

Nothing here violates the existing structure — scopes, audit, middleware and the DB
still gate every side effect. This only decides SCOPE and INTENT before planning.
"""
import re

_NEG = r"(?:no\b|not\b|n'?t\b|do ?not\b|don'?t\b|never\b|without\b|there is no need to\b|no need to\b)"


def forbidden(goal: str) -> set:
    """Actions the owner EXPLICITLY ruled out this turn (a veto, enforced downstream)."""
    g = (goal or "").lower()
    f = set()
    # deploy is forbidden on explicit negation, an explicit read-only/diagnosis-only ask
    if re.search(_NEG + r"[\w \-',]*deploy", g) \
       or "read-only" in g or "read only" in g \
       or re.search(r"\b(only|just)\b[\w \-',]*(diagnos|check the log|read the log|\blogs\b)", g):
        f.add("deploy")
    # db rebase/reset/reseed forbidden on explicit negation
    if re.search(_NEG + r"[\w \-',]*(rebase|reseed|db reset|reset the db|migrate dev)", g) \
       or "no db rebase" in g or "do not rebase" in g or "don't rebase" in g:
        f.add("db_rebase")
    return f


_APPROVE = re.compile(r"\b(i approve|approved\b|i authorize|authorized\b|go ahead|do it\b|proceed\b|yes,? (do|go|please)|make it)\b", re.I)
_SCOPED = re.compile(r"\bnothing else\b|\b(just|only)\b[\w \-',]*(update|edit|change|add|remove|fix|confirm|set|rename|the list|this|that|it)\b|\bonly (this|that|the)\b", re.I)
_QSTART = re.compile(r"^\s*(do|does|did|is|are|can|could|should|shall|will|would|how|what|why|where|when|which|who|am i|are we|have you|has |need to know)\b", re.I)
_CONFIRM = re.compile(r"\b(confirm\b|did you\b|have you\b|is (this|it) done\b|are we connected\b|just need to know\b|tell me\b|what is|what's)\b", re.I)
_BUILD = re.compile(r"\b(build|implement|develop|scaffold|create (the|a|an|my|our) (app|project|site|service|feature)|full app|end[- ]to[- ]end|the (whole|entire) (app|project)|make (the|a|an) (app|site|project))\b", re.I)
_DEPLOY = re.compile(r"\bdeploy\b|\brsync\b|\bbuild on (the )?vm\b", re.I)


def is_approval(goal: str) -> bool:
    return bool(_APPROVE.search(goal or ""))


def classify_request(goal: str, engine=None) -> dict:
    """Return the MINIMAL correct handling for the owner's message.

    mode: 'direct'      -> one agent (or the CTO) does it; NO team, NO brief expansion.
          'orchestrate' -> genuinely multi-part build; fan out to the team.
    action: 'approve' | 'do' | 'orchestrate'
    forbid: set of vetoed actions (e.g. 'deploy', 'db_rebase').
    """
    g = (goal or "").strip()
    gl = g.lower()
    forb = forbidden(g)

    # P4e: Jev mode — the local decider answers the CLOSED choice; low confidence falls back to the engine below.
    if engine is not None:
        try:   # a message that rules anything out ("do not deploy", "no db rebase", "without", "stop") always goes
            import jev_decider as _jd   # to the engine, so owner exclusions are never handled with less care
            _jm = None if re.search(r"\b(do not|don'?t|dont|never|no|not|without|avoid|stop|only|just|read-?only)\b", gl)                 else _jd.jev_choice("D1_mode", g)
        except Exception:
            _jm = None
        if _jm in ("direct", "orchestrate"):
            return {"mode": _jm, "action": "approve" if is_approval(gl) else ("orchestrate" if _jm == "orchestrate" else "do"),
                    "scoped": bool(_SCOPED.search(gl)) or "nothing else" in gl,
                    "forbid": sorted(set(forb)), "reason": "Jev mode: local decider", "source": "jev"}
    # Engine-first (smart) — but ALWAYS fall back to the deterministic net if it fails.
    if engine is not None:
        try:
            import json as _json
            raw = engine(
                "You are the Project CTO. The owner said:\n\"" + g[:1500] + "\"\n\n"
                "Decide the MINIMAL correct handling, like a smart engineer — do NOT expand it into a "
                "whole project.\n"
                "- mode: 'direct' if it is a single scoped task, a question, a confirmation, an approval, "
                "or a read-only diagnosis (you just DO it, no team). 'orchestrate' ONLY if it genuinely "
                "needs several specialists building/deploying.\n"
                "- forbid: list actions the owner explicitly ruled out (e.g. 'deploy', 'db_rebase').\n"
                'Reply ONLY JSON: {"mode":"direct|orchestrate","forbid":[...],"why":"..."}')
            m = re.search(r"\{.*\}", raw or "", re.S)
            if m:
                d = _json.loads(m.group(0))
                mode = d.get("mode") if d.get("mode") in ("direct", "orchestrate") else None
                if mode:
                    ef = set(forb) | set(x.lower() for x in (d.get("forbid") or []))
                    return {"mode": mode, "action": "approve" if is_approval(gl) else ("orchestrate" if mode == "orchestrate" else "do"),
                            "scoped": bool(_SCOPED.search(gl)) or "nothing else" in gl,
                            "forbid": sorted(ef), "reason": str(d.get("why", ""))[:200], "source": "engine"}
        except Exception:
            pass  # fall through to deterministic net

    scoped = ("nothing else" in gl) or bool(_SCOPED.search(gl))
    question = bool(_QSTART.match(gl)) or gl.endswith("?") or bool(_CONFIRM.search(gl))
    build = bool(_BUILD.search(gl))
    deploy_task = bool(_DEPLOY.search(gl)) and "deploy" not in forb

    if is_approval(gl):
        mode, action = "direct", "approve"
    elif scoped or question:
        mode, action = "direct", "do"
    elif "deploy" in forb:                      # read-only diagnosis is NOT a build
        mode, action = "direct", "do"
    elif build or deploy_task:
        mode, action = "orchestrate", "orchestrate"
    else:
        mode, action = "direct", "do"           # a lone ask is direct; fan out only when clearly multi-part

    return {"mode": mode, "action": action, "scoped": scoped, "question": question,
            "forbid": sorted(forb), "reason": _why(mode, scoped, question, build, deploy_task, forb),
            "source": "heuristic"}


def _why(mode, scoped, question, build, deploy_task, forb):
    if mode == "direct":
        if scoped: return "scoped single action ('just…/nothing else') — do exactly that"
        if question: return "a question/confirmation — answer directly"
        if "deploy" in forb: return "read-only/no-deploy ask — diagnose only, never deploy"
        return "single ask — one agent handles it"
    return "genuinely multi-part build/deploy — fan out to the team"


def requirements_for_run(goal: str) -> list:
    """Requirements come from the OWNER'S MESSAGE, not the brief. A scoped ask yields one
    item; a multi-part ask splits on 'and'/';'/newlines. The brief is NOT a requirement source."""
    g = (goal or "").strip()
    if not g:
        return []
    cls = classify_request(g)
    if cls["mode"] == "direct":
        return [g[:160]]
    parts = re.split(r"\n|;|\band then\b|\band also\b|, and | and ", g)
    reqs = [p.strip()[:160] for p in parts if len(p.strip()) > 6]
    return reqs[:8] or [g[:160]]


def accept_done(claim: str, evidence=None) -> dict:
    """Evidence gate: a completion/✅ claim is only accepted with CONCRETE evidence.
    Narration ('✅ passed', 'done', 'addressed') without proof is BLOCKED."""
    c = (claim or "").lower()
    claims_done = any(k in c for k in ("✅", "passed", "done", "addressed", "complete", "updated", "confirmed", "success"))
    if not claims_done:
        return {"accepted": True, "reason": "no completion claimed — nothing to gate"}
    ok = False
    if isinstance(evidence, dict):
        ok = any(str(evidence.get(k, "")).strip() for k in
                 ("diff", "file_mtime", "command_output", "exit_code", "db_read", "artifact", "path", "http_status"))
    elif evidence:
        ok = bool(str(evidence).strip())
    return {"accepted": bool(ok),
            "reason": "evidence present" if ok else "completion claimed WITHOUT evidence — blocked"}
