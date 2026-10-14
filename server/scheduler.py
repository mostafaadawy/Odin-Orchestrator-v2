"""
Per-project task scheduler (Phase 7 + Phase 3 periodic gate).

The owner can schedule a prompt to run for a project at a specific time or on a recurring
interval. A lightweight background thread checks due tasks and runs them through the engine.
No external cron — a simple, dependency-free runner.

Schedule kinds:
  - {"kind":"once","at": <epoch>}             run one time at/after `at`
  - {"kind":"interval","seconds": <int>}      run every N seconds
  - {"kind":"daily","hhmm": "06:00"}          run each day at local HH:MM

Phase 3 — periodic run gate (require_approval):
  Periodical projects should NOT silently auto-run. When such a task comes due AND the device is
  online (this process is running), it does not execute — it moves to status "pending_approval"
  and surfaces an alert. The owner approves → it runs; or skips → it rolls to the next slot.
  If the due time was MISSED because the device was off (the task is overdue beyond a grace
  window), it is rolled forward to the next future slot WITHOUT running ("if we miss it, no problem").
"""
from __future__ import annotations

import time
import uuid
import threading
import datetime
import store  # type: ignore


def list_tasks(pid: str | None = None) -> list:
    tasks = store.read_json("schedules.json", {"tasks": []})["tasks"]
    return [t for t in tasks if (pid is None or t.get("pid") == pid)]


def _all() -> list:
    return store.read_json("schedules.json", {"tasks": []})["tasks"]


def _save(tasks: list) -> None:
    store.write_json("schedules.json", {"tasks": tasks})


def get_task(tid: str) -> dict | None:
    for t in _all():
        if t["id"] == tid:
            return t
    return None


def create_task(pid: str, prompt: str, schedule: dict, title: str = "", assignee: str = "",
                require_approval: bool = False, kind_tag: str = "") -> dict:
    tasks = _all()
    t = {"id": uuid.uuid4().hex[:10], "pid": pid, "title": title or prompt[:40],
         "prompt": prompt, "schedule": schedule, "assignee": assignee, "enabled": True,
         "requireApproval": bool(require_approval), "kindTag": kind_tag,
         "status": "idle",                 # idle | pending_approval | running
         "pendingSince": None,
         "created": store.now(), "lastRun": None, "nextRun": _next_run(schedule, None),
         "runs": 0, "skips": 0}
    tasks.append(t)
    _save(tasks)
    return t


def update_task(tid: str, **fields) -> dict | None:
    tasks = _all()
    found = None
    for t in tasks:
        if t["id"] == tid:
            t.update({k: v for k, v in fields.items() if v is not None})
            if "schedule" in fields:
                t["nextRun"] = _next_run(t["schedule"], t.get("lastRun"))
            found = t
    if found:
        _save(tasks)
    return found


def delete_task(tid: str) -> bool:
    _save([t for t in _all() if t["id"] != tid])
    return True


DEFAULT_TZ = "Africa/Cairo"  # Egypt is the default timezone for schedules

def _next_calendar(schedule: dict) -> float | None:
    """Unified recurring schedule: MULTIPLE times/day + weekly/monthly, timezone-aware (default Egypt).
      {"kind":"calendar","times":["09:00","23:00"],"tz":"Africa/Cairo",
       "weekdays":[0..6] (empty=every day), "monthdays":[1..31] (empty=every day)}
    Returns the next strictly-future occurrence across all times × allowed days."""
    times = schedule.get("times") or [schedule.get("hhmm", "06:00")]
    tz = schedule.get("tz") or DEFAULT_TZ
    weekdays = set(schedule.get("weekdays") or [])   # 0=Mon .. 6=Sun (Python weekday())
    monthdays = set(schedule.get("monthdays") or [])
    try:
        from zoneinfo import ZoneInfo
        z = ZoneInfo(tz)
    except Exception:
        z = None
    now_dt = datetime.datetime.now(z) if z else datetime.datetime.now()
    best = None
    for day_off in range(0, 366):  # scan up to a year ahead for the next valid slot
        d = now_dt + datetime.timedelta(days=day_off)
        if weekdays and d.weekday() not in weekdays:
            continue
        if monthdays and d.day not in monthdays:
            continue
        for hm in times:
            try:
                hh, mm = (str(hm).split(":") + ["0"])[:2]
                cand = d.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
            except Exception:
                continue
            ts = cand.timestamp()
            if ts > now_dt.timestamp() and (best is None or ts < best):
                best = ts
        if best is not None:
            break
    return best


def _next_run(schedule: dict, last: float | None) -> float | None:
    now = time.time()
    k = schedule.get("kind")
    if k == "calendar":
        return _next_calendar(schedule)
    if k == "once":
        return schedule.get("at", now)
    if k == "interval":
        base = last or now
        return base + max(5, int(schedule.get("seconds", 3600)))
    if k == "daily":
        hh, mm = (schedule.get("hhmm", "06:00").split(":") + ["0"])[:2]
        tz = schedule.get("tz")
        if tz:  # tz-aware daily (e.g. America/New_York) — correct across DST, never hardcode UTC
            try:
                from zoneinfo import ZoneInfo
                z = ZoneInfo(tz)
                nowdt = datetime.datetime.now(z)
                run = nowdt.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
                if run.timestamp() <= now:
                    run += datetime.timedelta(days=1)
                return run.timestamp()
            except Exception:
                pass  # fall through to local time if zoneinfo unavailable
        nowdt = datetime.datetime.now()
        run = nowdt.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
        if run.timestamp() <= now:
            run += datetime.timedelta(days=1)
        return run.timestamp()
    return None


def _grace(schedule: dict) -> float:
    """How long after the due moment we still treat a run as 'fresh' (device was online around then).
    Beyond this, an overdue recurring task is considered MISSED and rolled forward without running."""
    k = schedule.get("kind")
    if k in ("daily", "calendar"):
        return 2 * 3600.0                       # act within 2h of a scheduled time
    if k == "interval":
        s = max(5, int(schedule.get("seconds", 3600)))
        return min(max(60.0, s * 0.5), 1800.0)  # half the interval, capped 1–30 min
    return float("inf")                          # 'once' always fires, even if late


def _next_future(schedule: dict) -> float | None:
    """Next strictly-future occurrence (used to roll a missed recurring task forward)."""
    now = time.time()
    k = schedule.get("kind")
    if k == "interval":
        s = max(5, int(schedule.get("seconds", 3600)))
        return now + s
    return _next_run(schedule, None)  # daily/calendar already compute the next future slot


# ---------------- approval gate (Phase 3) ----------------
def list_pending(pid: str | None = None) -> list:
    return [t for t in list_tasks(pid) if t.get("status") == "pending_approval"]


def approve(tid: str) -> dict | None:
    """Owner approved a due periodic task → run it now, then reschedule."""
    t = get_task(tid)
    if not t:
        return None
    _run_task(t)
    tasks = _all()
    for x in tasks:
        if x["id"] == tid:
            x["lastRun"] = time.time()
            x["runs"] = x.get("runs", 0) + 1
            x["status"] = "idle"
            x["pendingSince"] = None
            x["nextRun"] = None if x["schedule"].get("kind") == "once" else _next_run(x["schedule"], time.time())
            if x["schedule"].get("kind") == "once":
                x["enabled"] = False
            t = x
    _save(tasks)
    return t


def skip(tid: str) -> dict | None:
    """Owner skipped this occurrence → roll forward to the next slot, no run ('no problem')."""
    tasks = _all()
    found = None
    for x in tasks:
        if x["id"] == tid:
            x["skips"] = x.get("skips", 0) + 1
            x["status"] = "idle"
            x["pendingSince"] = None
            x["nextRun"] = None if x["schedule"].get("kind") == "once" else _next_future(x["schedule"])
            if x["schedule"].get("kind") == "once":
                x["enabled"] = False
            found = x
    if found:
        _save(tasks)
    return found


def _run_task(t: dict) -> None:
    """Execute a scheduled task through the engine, recorded in the relevant scope. If an agent is
    assigned, it runs as THAT team member (periodic agent, e.g. a security checker)."""
    try:
        import scopes  # type: ignore
        assignee = t.get("assignee")
        scope_id = f"member:{t['pid']}:{assignee}" if assignee else f"project:{t['pid']}"
        prompt = (f"[Scheduled task] As the {assignee} agent: {t['prompt']}" if assignee
                  else f"[Scheduled task] {t['prompt']}")
        cid = t.get("cid")  # a manual ▶ run posts INTO the current chat; a cron run makes its own ⏰ chat
        if not cid:
            cid = scopes.create_chat(scope_id, title=f"⏰ {t['title']}")["id"]
        # NOTIFY: a scheduled/recurring project has STARTED its run (shows on the live bell, on every page)
        _pname = t.get("pid", "")
        try:
            import projects as _pj  # type: ignore
            _pname = (_pj.get_project(t["pid"]) or {}).get("name", t["pid"])
        except Exception:
            pass
        try:
            import notifications_store as _nt  # type: ignore
            _nt.add("started", f"▶ {_pname} started its scheduled run",
                    body=t.get("title", ""), pid=t["pid"], cid=cid, project_name=_pname,
                    severity="info", icon="▶")
        except Exception:
            pass
        # AUTONOMOUS EXECUTION: if the task carries a real shell command (the project's pipeline), EXECUTE it
        # directly — do NOT route through the propose-first engine (which would only ask for approval).
        run_cmd = t.get("run_cmd")
        if run_cmd:
            import subprocess
            # Thread the LIVE scope + chat into the command so the pipeline posts its own rich per-agent
            # messages straight into the chat the owner is viewing. {pid}/{cid} are substituted here.
            cmd = run_cmd.replace("{pid}", str(t["pid"])).replace("{cid}", str(cid or ""))
            # ALWAYS post a visible START line into the scope FIRST, so the ▶ Run button shows the run
            # immediately. Pipelines that post their own rich per-agent messages are additive; a pipeline
            # that stays silent (e.g. writes only report files) or is slow to its first post no longer
            # leaves the owner — or the acceptance test — staring at an empty chat. (This is exactly why a
            # security/SOC project's run read as "produced no output": its run_cmd ran soc_run.py, which
            # writes report FILES, and on success nothing was posted here.)
            try:
                scopes.add_message(scope_id, cid, "assistant",
                                   f"▶ Running **{t.get('title','the pipeline')}** now…")
            except Exception:
                pass
            try:
                r = subprocess.run(cmd, shell=True, cwd=(t.get("cwd") or None),
                                   capture_output=True, text=True, timeout=1800)
                if r.returncode:
                    tail = ((r.stderr or "") + "\n" + (r.stdout or "")).strip()[-1800:]
                    scopes.add_message(scope_id, cid, "assistant",
                                       f"⚠️ Pipeline exited {r.returncode}.\n\n```\n{tail}\n```")
                else:
                    # SUCCESS: guarantee a result line in the scope even if the pipeline itself posted
                    # nothing — the run is never invisible. Concise; the pipeline's own messages, if any,
                    # stay the rich detail.
                    out = (r.stdout or "").strip()
                    tail = out[-1200:] if out else "completed — see the project's report / output."
                    scopes.add_message(scope_id, cid, "assistant",
                                       f"✅ **{t.get('title','Run')}** complete.\n\n```\n{tail}\n```")
            except Exception as e:
                scopes.add_message(scope_id, cid, "assistant", f"⚠️ Pipeline run error: {e}")
            try:
                scopes.sync_up(scope_id, f"▶ ran pipeline: {t.get('title','')}")
            except Exception:
                pass
            try:
                import notifications_store as _nt  # type: ignore
                okrun = (r.returncode == 0)
                _nt.add("finished", f"{'✅' if okrun else '⚠️'} {_pname} finished its scheduled run",
                        body=t.get("title", "") + ("" if okrun else " — exited with an error, tap to review"),
                        pid=t["pid"], cid=cid, project_name=_pname,
                        severity=("info" if okrun else "attention"), icon=("✅" if okrun else "⚠️"))
            except Exception:
                pass
            return
        # PROJECT-LEVEL team run (no single assignee) → run the REAL multi-agent orchestration so the
        # project chat shows the full CTO↔agent↔QA conversation (the ping-pong) AND the work actually
        # executes — instead of one propose-only dispatcher reply ("That's a X task, needs approval").
        # A single-assignee periodic task (e.g. a security checker) stays a focused single-agent reply.
        if not assignee:
            try:
                import api_v2 as _av  # type: ignore
                goal = t.get("prompt") or (t.get("title") or "Run this project's task now")
                # Scheduled/manual runs are AUTONOMOUS: authorize LOCAL/read-only execution directly; any
                # VM/Azure state change still hits the approval gate INSIDE the orchestration.
                if not _av._touches_vm(goal):
                    goal = (goal + "\n\n[Scheduled autonomous run — approval already granted for this run: "
                            "execute local/read-only work directly and produce the full team conversation; "
                            "do NOT merely propose. Stop only at a real VM/Azure or publish gate.]")
                ran = _av.orchestrate_blocking(t["pid"], goal)
                if not ran:
                    scopes.add_message(scope_id, cid, "assistant",
                                       "▶ A team run is already in progress for this project — see the pool above.")
            except Exception as e:
                scopes.add_message(scope_id, cid, "assistant", f"(team run error: {e})")
            try:
                scopes.sync_up(scope_id, f"▶ ran team: {t.get('title','')}")
            except Exception:
                pass
            try:
                import notifications_store as _nt  # type: ignore
                _nt.add("finished", f"✅ {_pname} finished its run", body=t.get("title", ""),
                        pid=t["pid"], cid=cid, project_name=_pname, severity="info", icon="✅")
            except Exception:
                pass
            return
        # SINGLE-AGENT periodic task → focused reply as that member.
        scopes.add_message(scope_id, cid, "user", prompt)
        reply = "(engine unavailable)"
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
                pass
        scopes.sync_up(scope_id, f"⏰ ran scheduled task: {t['title']}")
        low = (reply or "").lower()
        if any(k in low for k in ("vulnerab", "cve-", "outdated", "needs fix", "needs update",
                                  "security issue", "critical", "high severity")):
            try:
                import projects  # type: ignore
                projects.auto_remediate(t["pid"], reply[:400])
            except Exception:
                pass
    except Exception:
        pass


def run_now(pid: str, task_id: str = "", prompt: str = "", cid: str = "") -> dict:
    """Fire a project's recurring/scheduled task RIGHT NOW — the exact AUTONOMOUS action the cron performs
    (it EXECUTES; it does NOT run in propose-first / ask-for-approval mode like the interactive chat).
    Triggered manually by the owner (the ▶ Run button). Runs in the BACKGROUND so the caller returns at
    once. If [cid] is given, the run posts INTO that chat so the owner sees it in place. If [prompt] is
    given, run the (primary) task with that overridden instruction; if the project has no scheduled task,
    run [prompt] as a one-off."""
    # DETERMINISTIC operator run: the HubSpot project's ▶ Run must ALWAYS confirm the connection and return
    # REAL counts + fire a notification — not an LLM narration. Handle it directly and return synchronously.
    if pid == "hubspot-crm-operator":
        try:
            import hubspot_api  # type: ignore
            ov = hubspot_api.run_overview(pid)
            return {"started": True, "ran": ["hubspot-overview"], "count": 1,
                    "message": ov.get("summary", "HubSpot overview"), "result": ov}
        except Exception as e:
            return {"started": False, "ran": [], "count": 0, "error": f"hubspot run failed: {e}"}
    import threading
    tasks = [t for t in list_tasks(pid) if t.get("enabled", True)]
    if task_id:
        tasks = [t for t in tasks if t.get("id") == task_id]
    if prompt:
        if tasks:
            base = dict(tasks[0]); base["prompt"] = prompt; tasks = [base]
        else:
            tasks = [{"id": "adhoc", "pid": pid, "prompt": prompt, "title": prompt[:40], "assignee": ""}]
    if not tasks:
        # no Odin scheduled task defined → still DO the recurring work autonomously as a one-off run
        tasks = [{"id": "adhoc", "pid": pid, "title": "Manual run",
                  "prompt": "Run this project's recurring/daily task now — do exactly what the daily "
                            "scheduled run does, using this project's rules and assigned agents. Execute it "
                            "fully (do not just propose); stop only at any real publish/approval gate.",
                  "assignee": ""}]
    ran = []
    for t in tasks:
        ran.append(t.get("id"))
        tt = dict(t)
        if cid:
            tt["cid"] = cid  # post the autonomous run's output into the chat the owner is viewing
        threading.Thread(target=_run_task, args=(tt,), daemon=True).start()
    return {"started": bool(ran), "ran": ran, "count": len(ran), "message": "Running now — autonomous, in this chat."}


def _tick() -> None:
    now = time.time()
    tasks = _all()
    changed = False
    for t in tasks:
        if not t.get("enabled") or t.get("status") == "pending_approval":
            continue
        nr = t.get("nextRun")
        if not nr or now < nr:
            continue
        overdue = now - nr
        sched = t.get("schedule", {})
        # MISSED while offline. Default: roll forward silently. But a CATCH-UP task (e.g. the continuous
        # SOC daily run) must NOT lose coverage — run it once now on this launch, then reschedule.
        if sched.get("kind") in ("interval", "daily") and overdue > _grace(sched):
            if t.get("catchup"):
                _run_task(t)
                t["lastRun"] = now
                t["runs"] = t.get("runs", 0) + 1
                t["nextRun"] = _next_run(sched, now)
                changed = True
                continue
            t["skips"] = t.get("skips", 0) + 1
            t["nextRun"] = _next_future(sched)
            changed = True
            continue
        # DUE + device online → if approval required, alert instead of running
        if t.get("requireApproval"):
            t["status"] = "pending_approval"
            t["pendingSince"] = now
            changed = True
            continue
        # otherwise run now (legacy Phase-7 behavior)
        _run_task(t)
        t["lastRun"] = now
        t["runs"] = t.get("runs", 0) + 1
        if sched.get("kind") == "once":
            t["enabled"] = False
            t["nextRun"] = None
        else:
            t["nextRun"] = _next_run(sched, now)
        changed = True
    if changed:
        _save(tasks)


_started = False


_last_audit_sentinel = [0.0]
def _audit_sentinel_maybe(every: float = 900.0) -> None:
    """Debounced proactive audit inside the scheduler loop (~every 15 min). Heals auto-fixables and raises a
    notification on any hard violation (e.g. external-write) so a breach can't sit unseen. Fully guarded."""
    now = time.time()
    if now - _last_audit_sentinel[0] < every:
        return
    _last_audit_sentinel[0] = now
    try:
        import workspace_audit as _wa
        _wa.sentinel()
    except Exception:
        pass


def start_background(interval: float = 20.0) -> None:
    global _started
    if _started:
        return
    _started = True

    def loop():
        while True:
            try:
                _tick()
            except Exception:
                pass
            try:
                _audit_sentinel_maybe()   # proactive workspace audit: heal + notify on violations (debounced)
            except Exception:
                pass
            time.sleep(interval)

    threading.Thread(target=loop, daemon=True).start()
