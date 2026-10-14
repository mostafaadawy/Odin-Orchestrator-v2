"""
Anchor Connect — HTTP API + local-machine poller (Phase 1).

Two sides, ONE contract (the same E2E uses):
  THIRD-PARTY / REMOTE side (calls the anchor):
    POST /anchor/v1/requests            {project, prompt|payload, webhook_url}  -> {request_id,status}
    GET  /anchor/v1/requests/{id}       -> status + result
    POST /anchor/v1/requests/{id}/ack   -> explicit acknowledgement
  LOCAL-MACHINE side (pulls + returns work):
    GET  /anchor/v1/poll                -> {tasks:[…]}   (only un-handed-out, never finished)
    POST /anchor/v1/requests/{id}/result {result}        -> stores + delivers webhook
  ADMIN:
    GET/POST /anchor/v1/admin/config    (retry_count, retry_interval_sec, poll_limit)
    GET  /anchor/v1/admin/requests      (all, with statuses) ; GET /anchor/v1/admin/counts

Auth: X-API-Key must equal ANCHOR_API_KEY from workspace/shared/oth/.cred when that key is set (local/dev open until
then). In Phase 1 the local poller runs in-process (calls the queue directly); when the anchor is
deployed to the VM (Phase 3) the local machine polls the SAME endpoints over HTTP — contract unchanged.
"""
from __future__ import annotations

import time
import threading

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

import anchor_queue as q


class AnchorIn(BaseModel):
    project: str
    prompt: str = ""
    payload: dict | None = None
    webhook_url: str = ""
    sender: str = ""


def _check_key(provided: str | None):
    try:
        from integrations import cred
        want = cred.get("ANCHOR_API_KEY", "")
    except Exception:
        want = ""
    if want and (provided or "") != want:
        raise HTTPException(401, "invalid or missing X-API-Key")


def _public(r: dict) -> dict:
    return {k: r.get(k) for k in ("id", "project", "status", "result", "webhook_attempts",
                                  "acked", "error", "created", "updated", "history")}


def build_router() -> APIRouter:
    r = APIRouter(prefix="/anchor/v1", tags=["anchor"])

    # ---- third-party / remote intake ----
    @r.post("/requests")
    def create_request(body: AnchorIn, x_api_key: str | None = Header(default=None)):
        _check_key(x_api_key)
        import projects
        if not projects.get_project(body.project):
            raise HTTPException(404, f"unknown target project '{body.project}'")
        payload = body.payload if body.payload is not None else {"prompt": body.prompt}
        req = q.enqueue(body.project, payload, body.sender, body.webhook_url)
        return {"request_id": req["id"], "status": req["status"],
                "message": "received — queued and being processed; the result will be delivered to your webhook."}

    @r.get("/requests/{rid}")
    def request_status(rid: str):
        rq = q.get(rid)
        if not rq:
            raise HTTPException(404, "no such request")
        return _public(rq)

    @r.post("/requests/{rid}/ack")
    def acknowledge(rid: str):
        return q.ack(rid)

    # ---- local machine (client) ----
    @r.get("/poll")
    def poll(x_api_key: str | None = Header(default=None)):
        _check_key(x_api_key)
        return {"tasks": q.next_pending()}

    @r.post("/requests/{rid}/result")
    def submit(rid: str, body: dict, x_api_key: str | None = Header(default=None)):
        _check_key(x_api_key)
        return q.submit_result(rid, body.get("result"))

    # ---- admin / dashboard ----
    @r.get("/admin/config")
    def get_cfg():
        return q.cfg()

    @r.post("/admin/config")
    def set_cfg(body: dict):
        return q.set_cfg(**body)

    @r.get("/admin/requests")
    def admin_requests(status: str = ""):
        return {"requests": [_public(x) for x in q.list_requests(status or None)]}

    @r.get("/admin/counts")
    def admin_counts():
        return {"counts": q.counts()}

    return r


# ---------------------------------------------------------------- local poller
def _connector_facts(proj: dict, prompt: str) -> dict | None:
    """REAL read-only data the agent's capability fetches from the connected service (Klaviyo/Veeqo)
    to GROUND its answer. GET-only — it can never create or modify anything in the owner's accounts.
    Returns a data dict (or {'error':...}) or None if no connector applies."""
    t = (proj.get("type") or "").lower()
    pl = (prompt or "").lower()
    try:
        if t in ("email", "marketing", "content", "social") or any(k in pl for k in ("klaviyo", "workflow", "flow", "campaign")):
            from integrations import klaviyo as kl
            if kl.configured():
                return {"source": "klaviyo", "flows": kl.flows_summary()}
        if t in ("fulfillment", "shipping") or any(k in pl for k in ("veeqo", "order", "shipment", "shipping")):
            import datetime
            from integrations import veeqo as vq
            if vq.configured():
                since = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).strftime("%Y-%m-%dT00:00:00Z")
                return {"source": "veeqo", "orders": vq.orders_summary(since), "since": since}
    except Exception as e:
        return {"error": str(e)}
    return None


def _format_facts(facts: dict, prompt: str) -> str:
    """Turn the live read-only connector data into a concise, human answer — no LLM needed, returns fast.
    Robust to whatever shape orders_summary/flows_summary return (int, list, or dict)."""
    import json as _j
    facts = facts or {}
    src = facts.get("source", "the connected service")
    if src == "veeqo":
        orders = facts.get("orders")
        since = facts.get("since", "")
        cnt = (orders if isinstance(orders, int)
               else len(orders) if isinstance(orders, list)
               else (orders.get("count") or orders.get("total")) if isinstance(orders, dict)
               else orders)
        return (f"Veeqo (live, read-only): {cnt} orders since {since}.\n\n"
                f"Raw: {_j.dumps(orders)[:700]}")
    if src == "klaviyo":
        flows = facts.get("flows")
        if isinstance(flows, dict):
            live, draft, total = flows.get("live"), flows.get("draft"), flows.get("total")
            head = f"Klaviyo (live, read-only): {total if total is not None else ''} flows"
            if live is not None or draft is not None:
                head += f" — {live} live, {draft} draft"
            return head + f".\n\nRaw: {_j.dumps(flows)[:700]}"
        if isinstance(flows, list):
            return f"Klaviyo (live, read-only): {len(flows)} flows.\n\nRaw: {_j.dumps(flows)[:700]}"
        return f"Klaviyo (live, read-only): {_j.dumps(flows)[:800]}"
    return f"{src} (live, read-only): {_j.dumps(facts)[:800]}"


def _last_answer(pid: str) -> str:
    """Pull the agent's final deliverable produced by the orchestration run. Prefer a recorded
    member deliverable; else the last substantive member reply in the shared pool (skip CTO
    plan/review lines)."""
    try:
        import main_task
        mt = main_task.get(pid) or {}
        # 1) most recent recorded member deliverable
        best = None
        for member, st in (mt.get("status") or {}).items():
            d = (st or {}).get("deliverable")
            ts = (st or {}).get("ts", 0)
            if d and (best is None or ts > best[0]):
                best = (ts, d)
        if best:
            return best[1]
        # 2) fall back to the last SUBSTANTIVE member reply in the pool — skip CTO plan/review lines AND
        #    the internal diagnostic breadcrumbs (▶ step start, ⏳/✓ phase:, ▶ starting step, audit/tool
        #    lines). Those are orchestration telemetry, NOT the agent's answer — returning one of them is
        #    exactly the bug we hit (result = "▶ step start — is_devops=…").
        _noise = ("▶ step start", "⏳ phase", "✓ phase", "▶ starting step", "🕵️", "🔧 executed",
                  "phase: engine call", "phase: vm access", "step start —", "◀", "quiet ", "working…")
        for e in reversed(mt.get("pool") or []):
            who = e.get("who", "")
            txt = (e.get("text") or "").strip()
            if not txt or len(txt) < 15:
                continue
            if "plan)" in who or "review)" in who or "checklist" in who.lower() or "orchestrator" in who.lower():
                continue
            tl = txt.lower()
            if any(tl.startswith(n) or n in tl[:45] for n in _noise):
                continue
            return txt
    except Exception:
        pass
    return "(no answer captured from the run)"


def process(task: dict, timeout: int = 300) -> dict:
    """Process an external request on the LOCAL machine through the REAL orchestration: the request
    becomes the goal, the CTO plans and assigns the project's agent, the agent works (grounded in REAL
    read-only connector data) and returns the result. This is the same CTO→team module used everywhere
    — so it genuinely takes time. Returns {answer, engine_used, facts, via, secs}."""
    import time as _t
    import json as _j
    pid = task.get("project")
    payload = task.get("payload") or {}
    prompt = payload.get("prompt") or _j.dumps(payload)
    proj = {}
    try:
        import projects
        proj = projects.get_project(pid) or {}
    except Exception:
        pass
    facts = _connector_facts(proj, prompt)      # REAL read-only data the agent answers from

    # FAST READ-ONLY PATH — for seeded read-only queries (Veeqo orders / Klaviyo flows) we already have
    # the REAL live data in `facts`, so answer DIRECTLY in seconds instead of spinning up the full
    # multi-agent CTO→team run (which takes minutes and can stall). Set ODIN_ANCHOR_FAST=0 to force the
    # heavy orchestration. If a connector errored, fall through to the orchestration.
    import os as _os
    if _os.environ.get("ODIN_ANCHOR_FAST", "1") != "0" and facts and not facts.get("error"):
        return {"answer": _format_facts(facts, prompt), "engine_used": False, "facts": facts,
                "via": "fast-readonly", "secs": 0}

    grounding = (f"\n\nLIVE READ-ONLY DATA (fetched now from the connected service — answer FROM this; "
                 f"if it shows an error, say so):\n{_j.dumps(facts)[:2000]}" if facts else "")

    # TIER 2 — FAST Q&A PATH: a SINGLE grounded engine call (ONE Claude CLI invocation) instead of the
    # full multi-agent CTO→team run (which fires MANY sequential calls = minutes and is what caused the
    # slowness/502). External anchor requests are Q&A, answerable in one grounded completion (seconds).
    # Only genuine multi-step BUILD tasks need the team (they set payload.orchestrate=1 or use build verbs).
    # HEAVY = real project WORK → must run the full CTO→team, exactly like the desktop (so a web/mobile
    # caller who asks to build/complete/continue a project gets the same power). Only pure informational
    # Q&A (how many / what is / list / status / summarize) takes the fast single-call path.
    _pl = prompt.lower()
    heavy = bool((payload or {}).get("orchestrate")) or any(w in _pl for w in (
        "build", "deploy", "implement", "create ", "set up", "setup", "refactor", "complete", "finish",
        "continue", "fix ", "add ", "update ", "write ", "make ", "generate ", "execute", "run the",
        "start the project", "resume", "carry on", "proceed"))
    _pname = proj.get("name", pid)
    # SCOPE + PRIVACY GUARD for EXTERNAL callers — sourced from the SHARED middleware helper so the owner
    # path and the external path use ONE system-wide rule (no per-project or per-path divergence). The shared
    # pool stays fully visible internally; this only shapes what an OUTSIDE caller receives.
    try:
        import workspace_mw as _mw
        _scope_guard = _mw.scope_answer_guard(_pname, external=True)
    except Exception:
        _scope_guard = (f"Answer only about the project '{_pname}' from its live data. If the question is "
                        f"outside this project's scope, do not reveal it — say it needs the owner's approval.")
    if not heavy and _os.environ.get("ODIN_ANCHOR_SINGLE", "1") != "0":
        qa_goal = (f"{_scope_guard}\n\nQUESTION: {prompt}{grounding}")
        try:
            import api_v2
            parts, final = [], None
            t0 = _t.time()
            for evd in api_v2._engine_stream(qa_goal, "en", None, "claude", cwd=None, readonly=True):
                k = evd.get("kind")
                if k == "text":
                    parts.append(evd.get("t", ""))
                elif k == "final":
                    final = evd.get("text") or "".join(parts)
                if (_t.time() - t0) > 90:   # hard cap so a stuck call can never hang the request
                    break
            answer = (final or "".join(parts)).strip() or "(no answer produced)"
            return {"answer": answer, "engine_used": True, "facts": facts,
                    "via": "single-call", "secs": round(_t.time() - t0, 1)}
        except Exception as e:
            return {"answer": f"(engine error: {e})", "engine_used": False, "facts": facts, "via": "single-error"}

    # TIER 3 — FULL CTO→team orchestration, ONLY for explicit multi-step build tasks (inherently async).
    goal = (f"External request via Anchor Connect for this project. As CTO, assign the right agent and "
            f"answer the question precisely.\n\n{_scope_guard}\n\nQUESTION: {prompt}{grounding}")
    try:
        import api_v2
        api_v2.start_run(pid, goal)
        t0 = _t.time()
        while api_v2.run_status(pid).get("running") and (_t.time() - t0) < timeout:
            _t.sleep(2)
        return {"answer": _last_answer(pid), "engine_used": True, "facts": facts,
                "via": "orchestration", "secs": round(_t.time() - t0, 1)}
    except Exception as e:
        return {"answer": f"(orchestration error: {e})", "engine_used": False, "facts": facts, "via": "error"}


def _process(task: dict) -> str:
    """Back-compat string wrapper used by the background poller."""
    return process(task).get("answer", "")


_started = False


def start_local_poller(interval: float = 5.0) -> None:
    """Background: the LOCAL machine pulls pending tasks, processes them, returns results, and runs
    the webhook retry sweep. In Phase 1 this calls the queue in-process; the contract is identical to
    polling the deployed anchor over HTTP later."""
    global _started
    import os
    if os.environ.get("ODIN_ANCHOR_NO_POLLER") == "1":
        return   # deterministic HTTP-contract testing drives poll/result manually
    if _started:
        return
    _started = True

    def loop():
        while True:
            try:
                for t in q.next_pending():
                    q.mark_processing(t["id"])
                    res = _process(t)
                    q.submit_result(t["id"], res)
                q.retry_due()
            except Exception:
                pass
            time.sleep(interval)

    threading.Thread(target=loop, daemon=True).start()
