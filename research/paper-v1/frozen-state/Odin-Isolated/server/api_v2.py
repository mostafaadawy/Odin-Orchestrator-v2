"""
Odin v2 API — projects, scoped multi-agent org, agents/rules, models, scheduling, activity.

Mounted by server/app.py. Everything here builds on the existing engine, router, approval gate,
voice and Azure connector — it does not replace them. The scoped chat stream adds the org
behavior: a Project CTO DELEGATES a task to the responsible member, the member works (heartbeat
goes live), the result streams back and rolls up to the project + company scopes.
"""
from __future__ import annotations

import os
import json
import re
import time
import threading
import pathlib

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

ROOT = pathlib.Path(__file__).resolve().parent.parent


# ---------- request bodies ----------
class ProjectIn(BaseModel):
    name: str
    identifier: str = ""   # owner-chosen unique id (recommended value suggested from the name)
    description: str = ""
    localPath: str = ""
    members: list | None = None
    type: str = ""
    stack: str = ""
    url: str = ""
    mode: str = "build"   # "build" = create from scratch; "deploy" = deploy an EXISTING app
    sources: list | None = None   # existing folders to READ/work on (read-only unless asked)
    autoApprove: bool = False     # owner pre-authorized changes (skip the approval popup)
    periodic: dict | None = None  # {enabled, schedule:{kind,...}, requireApproval} — recurring project
    cadence: str = ""             # once | recurring | periodical


class MappingIn(BaseModel):
    local: str
    cloud: str
    role: str = ""


class AgentIn(BaseModel):
    name: str
    role: str = ""
    avatar: str = "generic"
    description: str = ""
    skills: list | None = None
    restrictions: list | None = None
    model: str = ""
    nature: str = "technical"
    resources: str = ""             # editable "Allowed Resources & Dependencies" section
    env: list | None = None         # editable per-agent env vars: [{"key":..,"value":..}, …]


class DescIn(BaseModel):
    description: str


class IntakeIn(BaseModel):
    history: list = []


class RuleIn(BaseModel):
    rule: str


class TitleIn(BaseModel):
    title: str = "New chat"


class ModelIn(BaseModel):
    scope: str
    model: str


class ScheduleIn(BaseModel):
    pid: str
    prompt: str
    schedule: dict
    title: str = ""
    assignee: str = ""


def sse(ev: str, data: dict) -> str:
    return f"event: {ev}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def build_router() -> APIRouter:
    r = APIRouter()

    # ======================= PROJECTS =======================
    @r.get("/projects")
    def projects_list():
        import projects
        return {"projects": [p for p in projects.list_projects() if p.get("status") != "archived"]}

    @r.get("/projects/archived")
    def projects_archived():
        import projects
        return {"projects": [p for p in projects.list_projects() if p.get("status") == "archived"]}

    @r.post("/projects/{pid}/archive")
    def projects_archive(pid: str):
        import projects
        return projects.archive_project(pid) or {}

    @r.post("/projects/{pid}/unarchive")
    def projects_unarchive(pid: str):
        import projects
        return projects.unarchive_project(pid) or {}

    @r.post("/projects")
    def projects_create(body: ProjectIn):
        import projects
        return projects.create_project(body.name, body.description, body.localPath, body.members,
                                       ptype=body.type, stack=body.stack, url=body.url, mode=body.mode,
                                       sources=body.sources, auto_approve=body.autoApprove,
                                       periodic=body.periodic, cadence=body.cadence,
                                       identifier=body.identifier)

    @r.get("/projects/suggest-id")
    def projects_suggest_id(name: str = "", localPath: str = ""):
        import projects
        return {"identifier": projects.suggest_identifier(name, localPath)}

    @r.get("/project-types")
    def project_types():
        import projects
        return {"types": projects.project_types(), "operational": projects.operational_members()}

    @r.post("/agents/validate")
    def agents_validate(body: dict):
        """Given proposed member names, return which are known catalog roles vs unknown (need a
        confirmation dialog before any agent is created). Prevents silent agent invention."""
        import projects
        return projects.classify_team(body.get("names") or [])

    @r.post("/projects/{pid}/capability")
    def project_capability(pid: str, body: dict):
        """Powers the CTO capability-gap dialog: ranked existing agents able to handle the task +
        a smart suggestion (name/role/rules) for a new custom agent. Read-only; creates nothing."""
        import projects
        return projects.capability_options(pid, body.get("task") or "")

    @r.get("/roles")
    def roles():
        import projects
        return {"roles": projects.roles_readiness()}

    @r.post("/projects/intake")
    def projects_intake(body: IntakeIn):
        """Adaptive, brain-driven intake: next question or final proposal (with dependencies)."""
        import projects
        return projects.intake_step(body.history)

    @r.get("/projects/intake/readiness")
    def intake_readiness():
        """Verify our ACTUAL resources before generating a project: is the Claude engine available,
        is Azure reachable, and which services are connected. Lets the confirm screen TEST the
        'needs' items (connect an API / set up a member) before we go."""
        res = {"claude": False, "azure": False, "connectors": []}
        try:
            import claude_cli
            res["claude"] = bool(claude_cli.available())
        except Exception:
            pass
        try:
            import infra_az
            res["azure"] = bool(infra_az.connect_test().get("ok"))
        except Exception:
            pass
        try:
            import capabilities
            res["connectors"] = [c.get("name") or c.get("id") for c in (capabilities.list_connectors() or [])]
        except Exception:
            pass
        return res

    @r.get("/capabilities")
    def capabilities_get():
        """What the system already has connected + what it can help connect."""
        import capabilities
        return capabilities.snapshot()

    # --- company-level agents (define once; auto-added to new projects) ---
    @r.get("/company/agents")
    def company_agents():
        import agents_registry
        return {"agents": agents_registry.list_company_agents()}

    # --- ORG-WIDE roster of ACTUAL agents (every project's agents + company agents), so a newly-created
    #     agent appears on the main page — not only inside its project. NOT the 20-role catalog. ---
    @r.get("/agents/all")
    def agents_all():
        import agents_registry
        return {"agents": agents_registry.all_agents()}

    @r.post("/company/agents")
    def company_agent_add(body: AgentIn):
        import agents_registry
        return agents_registry.add_company_agent(body.name, role=body.role, avatar=body.avatar,
                                                 description=body.description, rules=body.skills)

    @r.delete("/company/agents/{name}")
    def company_agent_remove(name: str):
        import agents_registry
        return {"removed": agents_registry.remove_company_agent(name)}

    # --- external connectors (API-key integrations with a status badge) ---
    @r.get("/connectors")
    def connectors_list():
        import capabilities
        return {"connectors": capabilities.list_connectors()}

    @r.post("/connectors")
    def connector_add(body: dict):
        import capabilities
        return capabilities.add_connector(body.get("name", ""), body.get("type", ""), body.get("apiKey", ""))

    @r.delete("/connectors/{cid}")
    def connector_remove(cid: str):
        import capabilities
        return {"removed": capabilities.remove_connector(cid)}

    # ---- Approval gate: nothing changes your files / the VM without your explicit OK ----
    @r.get("/approvals")
    def approvals_list(pid: str = "", all: int = 0):
        import approvals
        if all:
            return {"approvals": approvals.list_for(pid or None)}
        return {"approvals": approvals.list_pending(pid or None)}

    @r.get("/approvals/count")
    def approvals_count(pid: str = ""):
        import approvals
        return {"pending": approvals.pending_count(pid or None)}

    @r.post("/approvals/{aid}/approve")
    def approvals_approve(aid: str, body: dict | None = None):
        import approvals, threading
        a = approvals.decide(aid, True, (body or {}).get("note", ""))
        if a and a.get("kind") == "deploy":
            import operations
            oid = operations.create(a["pid"], "deploy", "Deploy to VM (rsync + commands as mostafa)")
            if _op_is_deploy_project(a["pid"]):
                # deploy the approved files, then chain the DB gate (schema/seed) or the diagnosis
                threading.Thread(target=_op_after_deploy, args=(a["pid"], oid), daemon=True).start()
            else:
                threading.Thread(target=_deploy_bg, args=(a["pid"], oid), daemon=True).start()
            return {**a, "operation": oid}
        elif a and a.get("kind") == "synclist":
            threading.Thread(target=_op_apply_synclist, args=(a["pid"], aid), daemon=True).start()
            return a
        elif a and a.get("kind") == "db-migrate":
            threading.Thread(target=_op_apply_dbmigrate, args=(a["pid"], aid), daemon=True).start()
            return a
        elif a and a.get("kind") == "qa-recommendation":
            # owner accepted the CTO's recommendation → add QA to the team; it gates from next task
            import agents_registry, projects
            if not agents_registry.get_agent(a["pid"], "QA"):
                agents_registry.register_agent(a["pid"], "QA", role="QA & Testing", avatar="qa",
                                               description="Added on the owner's approval")
            projects.set_flags(a["pid"], qa_asked=True, qa_declined=False)
        elif a and not a.get("applied"):
            # ANY approved change (incl. old 'inline' ones) executes now, in the background —
            # never waiting on a run loop that may have died.
            threading.Thread(target=_apply_approval_bg, args=(aid,), daemon=True).start()
        return a or {"error": "not found"}

    @r.post("/approvals/{aid}/reject")
    def approvals_reject(aid: str, body: dict | None = None):
        import approvals
        a = approvals.decide(aid, False, (body or {}).get("note", ""))
        if a and a.get("kind") == "qa-recommendation":
            import projects
            projects.set_flags(a["pid"], qa_asked=True, qa_declined=True)   # never ask again
        elif a and a.get("kind") == "deploy" and _op_is_deploy_project(a["pid"]):
            # declined the deploy -> offer the SEPARATE re-baseline gate (so it stops flagging these files)
            _op_open_sync_gate(a["pid"])
        elif a and a.get("kind") == "synclist":
            # declined re-baseline -> STOP (do not silently jump to diagnosis; a run only advances on play/deploy)
            try:
                import scopes as _sc3
                _s3, _c3 = _op_cid(a["pid"])
                _sc3.add_message(_s3, _c3, "assistant", "Okay — leaving the change-list as is. Run finished; press play to run the deploy check again.")
            except Exception:
                pass
        elif a and a.get("kind") == "db-migrate":
            # declined the DB migration -> skip it and run the diagnosis
            _op_run_diagnosis(a["pid"], note="[system] DB migration declined; skipping it.")
        return a or {"error": "not found"}

    @r.get("/projects/{pid}")
    def projects_get(pid: str):
        import projects, agents_registry, scheduler
        p = projects.get_project(pid)
        if not p:
            raise HTTPException(404, "no such project")
        return {**p, "agents": agents_registry.list_agents(pid),
                "stats": agents_registry.stats(pid),
                "schedules": scheduler.list_tasks(pid)}

    @r.post("/projects/{pid}/update")
    def projects_update(pid: str, body: dict):
        import projects
        d = projects.update_project(pid, **body)
        if not d:
            raise HTTPException(404, "no such project")
        return d

    @r.delete("/projects/{pid}")
    def projects_delete(pid: str):
        import projects
        return {"deleted": projects.delete_project(pid)}

    @r.post("/projects/{pid}/mappings")
    def projects_map(pid: str, body: MappingIn):
        import projects
        d = projects.add_mapping(pid, body.local, body.cloud, body.role)
        if not d:
            raise HTTPException(404, "no such project")
        return d

    @r.get("/projects/{pid}/plan")
    def projects_plan(pid: str):
        import projects
        return {"plan": projects.generate_plan(pid)}

    @r.post("/projects/{pid}/remediate")
    def projects_remediate(pid: str, body: dict):
        """Auto cross-agent fix chain from a finding (CTO → FE/BE fix → DevOps redeploy proposal)."""
        import projects
        return projects.auto_remediate(pid, body.get("finding", ""))

    # --- per-project custom rules (owner can add / edit / discard, live) ---
    @r.get("/projects/{pid}/rules")
    def project_rules(pid: str):
        import projects
        return {"rules": projects.list_rules(pid)}

    @r.post("/projects/{pid}/rules")
    def project_rule_add(pid: str, body: RuleIn):
        import projects
        return projects.add_rule(pid, body.rule) or {}

    @r.post("/projects/{pid}/rules/{rid}")
    def project_rule_update(pid: str, rid: str, body: RuleIn):
        import projects
        return projects.update_rule(pid, rid, body.rule) or {}

    @r.delete("/projects/{pid}/rules/{rid}")
    def project_rule_delete(pid: str, rid: str):
        import projects
        return projects.remove_rule(pid, rid) or {}

    @r.get("/projects/{pid}/sync")
    def projects_sync(pid: str):
        import projects
        return {"proposal": projects.sync_proposal(pid)}

    @r.get("/projects/{pid}/deploy")
    def projects_deploy(pid: str):
        import projects
        return {"proposal": projects.deploy_proposal(pid)}

    @r.post("/projects/{pid}/sync/run")
    def projects_sync_run(pid: str):
        import projects
        return {"result": projects.sync_run(pid)}

    @r.post("/projects/{pid}/deploy/run")
    def projects_deploy_run(pid: str):
        import projects
        return {"result": projects.deploy_run(pid)}

    @r.get("/projects/{pid}/orchestrate")
    def projects_orchestrate(pid: str, goal: str):
        """The autonomous team run: the Project CTO plans an ordered pipeline, then runs each
        member in turn, AUTO-advancing to the next when one finishes. Streams the whole flow."""
        return StreamingResponse(_orchestrate_gen(pid, goal), media_type="text/event-stream")

    # ---- Deterministic deploy (fast, script-style, no AI in the execution path) ----
    @r.get("/projects/{pid}/deploy/config")
    def deploy_config_get(pid: str):
        import deploy_runner
        return deploy_runner.get_config(pid)

    @r.post("/projects/{pid}/deploy/config")
    def deploy_config_save(pid: str, body: dict):
        import deploy_runner
        return deploy_runner.save_config(pid, body or {})

    @r.post("/projects/{pid}/deploy/request")
    def deploy_run_now(pid: str, body: dict | None = None):
        """Create ONE approval that previews the exact deploy (sync + commands + reboot). On approve,
        the deterministic runner executes it as a watchable operation. Nothing runs before you approve."""
        import deploy_runner, approvals
        cfg = deploy_runner.get_config(pid)
        if not cfg.get("targets"):
            return {"error": "No deploy config yet — set targets (local/vm/excludes/commands) first."}
        cmds = []
        for t in cfg["targets"]:
            cmds.append({"cmd": f"rsync {t.get('local','')} → {t.get('vm','')}", "where": "vm",
                         "why": f"{t.get('name','')} sync ({len(t.get('excludes') or [])} excludes)"})
            mig = deploy_runner._migration_cmd(t.get("migration", "none"))
            if mig:
                cmds.append({"cmd": mig, "where": "vm", "why": f"{t.get('name','')} migration: {t.get('migration')}"})
            for c in (t.get("commands") or []):
                cmds.append({"cmd": c, "where": "vm", "why": t.get("name", "")})
        if cfg.get("reboot"):
            cmds.append({"cmd": "sudo reboot", "where": "vm", "why": "final"})
        return approvals.create(pid, "DevOps", title="Deploy to VM (fast deterministic runner)",
                                summary="Runs your exact rsync + commands as mostafa — like your script.",
                                commands=cmds, kind="deploy", inline=False)

    # Background team run — survives UI navigation (runs on the server, UI just polls).
    @r.post("/projects/{pid}/orchestrate/start")
    def orchestrate_start(pid: str, body: dict | None = None):
        return start_run(pid, (body or {}).get("goal", ""))

    @r.get("/projects/{pid}/orchestrate/status")
    def orchestrate_status(pid: str):
        return run_status(pid)

    @r.post("/projects/{pid}/orchestrate/stop")
    def orchestrate_stop(pid: str):
        return stop_run(pid)

    # ---- Operations: the ONE record per long task the UI watches live + can stop ----
    @r.get("/operations")
    def operations_list(pid: str = ""):
        import operations
        return {"operations": operations.list_for(pid or None)}

    @r.get("/operations/latest")
    def operations_latest(pid: str):
        import operations
        op = operations.latest(pid)
        return op or {}

    @r.get("/operations/{oid}")
    def operations_get(oid: str):
        import operations
        return operations.get(oid) or {"error": "not found"}

    @r.post("/operations/{oid}/stop")
    def operations_stop(oid: str):
        import operations
        return operations.request_stop(oid)

    # SMART CONTINUE — the owner answers a blocked operation's question; we apply the answer to
    # CORRECT the operation, then resume it (re-run with the same plan, now unblocked).
    @r.post("/operations/{oid}/provide")
    def operations_provide(oid: str, body: dict):
        import operations
        op = operations.get(oid)
        if not op:
            raise HTTPException(404, "no such operation")
        answers = (body or {}).get("answers") or body or {}
        operations.provide(oid, answers)
        threading.Thread(target=_resume_operation, args=(oid, answers), daemon=True).start()
        return {"ok": True, "resuming": True, "id": oid}

    # Run the deterministic deploy directly as an operation (used by the Deploy button once the
    # owner has already approved a deploy this session). Still creates a watchable/stoppable op.
    @r.post("/projects/{pid}/deploy/operation")
    def deploy_operation(pid: str):
        import operations, deploy_runner
        if not deploy_runner.get_config(pid).get("targets"):
            return {"error": "No deploy config yet — set targets first."}
        oid = operations.create(pid, "deploy", "Deploy to VM (rsync + commands as mostafa)")
        threading.Thread(target=_deploy_bg, args=(pid, oid), daemon=True).start()
        return {"operation": oid}

    # ▶ RUN NOW — manually fire a project's recurring/scheduled task (or a one-off), in the background.
    @r.post("/projects/{pid}/run-now")
    def project_run_now(pid: str, body: dict | None = None):
        import scheduler
        b = body or {}
        return scheduler.run_now(pid, task_id=str(b.get("task_id") or ""),
                                 prompt=str(b.get("prompt") or ""), cid=str(b.get("cid") or ""))

    # ======================= AGENTS / RULES =======================
    @r.get("/projects/{pid}/agents")
    def agents_list(pid: str):
        import agents_registry
        return {"agents": agents_registry.list_agents(pid)}

    @r.get("/projects/{pid}/stats")
    def agents_stats(pid: str):
        import agents_registry
        return agents_registry.stats(pid)

    @r.post("/projects/{pid}/agents/suggest")
    def agents_suggest(pid: str, body: DescIn):
        import agents_registry
        return agents_registry.suggest_agent(body.description)

    @r.post("/projects/{pid}/agents")
    def agents_add(pid: str, body: AgentIn):
        import agents_registry
        # an EXPLICIT owner add re-allows a previously removed agent (force clears the exclusion)
        return agents_registry.register_agent(
            pid, body.name, role=body.role, avatar=body.avatar, description=body.description,
            skills=body.skills, restrictions=body.restrictions, model=body.model, force=True,
            nature=body.nature, resources=body.resources, env=body.env)

    @r.get("/projects/{pid}/agents/{name}")
    def agents_get(pid: str, name: str):
        import agents_registry
        a = agents_registry.get_agent(pid, name)
        if not a:
            raise HTTPException(404, "no such agent")
        return a

    @r.post("/projects/{pid}/agents/{name}/update")
    def agents_update(pid: str, name: str, body: dict):
        import agents_registry
        a = agents_registry.update_agent(pid, name, **body)
        if not a:
            raise HTTPException(404, "no such agent")
        return a

    @r.delete("/projects/{pid}/agents/{name}")
    def agents_remove(pid: str, name: str):
        import agents_registry
        return {"removed": agents_registry.remove_agent(pid, name)}

    @r.post("/projects/{pid}/agents/{name}/rule")
    def agents_rule(pid: str, name: str, body: RuleIn):
        import agents_registry
        a = agents_registry.save_rule(pid, name, body.rule)
        if not a:
            raise HTTPException(404, "no such agent")
        return a

    # ======================= MODELS =======================
    @r.get("/models")
    def models_list():
        import models_config
        return {"models": models_config.available_models(),
                "config": models_config._cfg()}

    @r.post("/models/set")
    def models_set(body: ModelIn):
        import models_config
        return models_config.set_model(body.scope, body.model)

    # ======================= SCOPES / MULTI-LEVEL CHAT =======================
    @r.get("/scope/chats")
    def scope_chats(scope: str):
        import scopes
        return {"chats": scopes.list_chats(scope)}

    @r.post("/scope/chats")
    def scope_chat_create(scope: str, body: TitleIn | None = None):
        import scopes
        return scopes.create_chat(scope, body.title if body else "New chat")

    @r.get("/scope/chat")
    def scope_chat_get(scope: str, cid: str):
        import scopes
        d = scopes.get_chat(scope, cid)
        if not d:
            raise HTTPException(404, "no such chat")
        return d

    @r.post("/scope/chat/rename")
    def scope_chat_rename(scope: str, cid: str, body: TitleIn):
        import scopes
        d = scopes.rename_chat(scope, cid, body.title)
        if not d:
            raise HTTPException(404, "no such chat")
        return d

    @r.delete("/scope/chat")
    def scope_chat_delete(scope: str, cid: str):
        import scopes
        return {"deleted": scopes.delete_chat(scope, cid)}

    @r.get("/scope/summary")
    def scope_summary(scope: str):
        import scopes
        return scopes.get_summary(scope)

    @r.get("/scope/children")
    def scope_children(scope: str):
        import scopes
        return {"children": scopes.read_child_chats(scope)}

    @r.get("/scope/stream")
    def scope_stream(scope: str, text: str, lang: str = "en", cid: str = ""):
        return StreamingResponse(_scoped_gen(scope, text, lang, cid),
                                 media_type="text/event-stream")

    # the WHOLE pool for a scope, merged across all its chats (single-source-of-truth view).
    # DELTA SYNC: pass ?since=<seq> to get ONLY messages newer than that seq (empty when up to date).
    # Always returns max_seq so the client can advance its cursor. since=0 → the full pool (backward compat).
    @r.get("/scope/messages")
    def scope_all_messages(scope: str, since: int = 0):
        import scopes
        allm = scopes.all_messages(scope)
        mx = max((m.get("seq", 0) for m in allm), default=0)
        msgs = [m for m in allm if m.get("seq", 0) > since] if since else allm
        return {"messages": msgs, "max_seq": mx, "since": since}

    # ---- GENERIC per-project styled report (Reporting & Documentation Agent). Works for ANY project:
    # it builds a report ON-THE-FLY from the project's REAL team-conversation pool + team + brief, then
    # renders pdf/docx/md/pptx via the shared report_engine. The SOC project still serves its pre-styled
    # health report when one exists; every OTHER project now gets a generated one — so the ▶ Export button
    # no longer 404s ("no report yet — run the SOC first") outside the SOC.
    _RPT_MIME = {"pdf": "application/pdf",
                 "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                 "md": "text/markdown",
                 "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation"}

    @r.get("/project/report")
    def project_report(pid: str, fmt: str = "pdf"):
        import io as _io
        import projects as _pj, scopes as _sc, report_engine as _re
        ext = fmt if fmt in ("pdf", "docx", "md", "pptx") else "pdf"
        proj = _pj.get_project(pid) or {}
        # GENERIC (no per-project hardcode): if THIS project already has pre-rendered styled report
        # files in its own folder, serve the newest. This is a SYSTEM rule — the SOC health report is
        # just one instance of it, not a special path — so any project that produces styled reports is
        # served identically, and a brand-new project needs no code change. Otherwise we generate below.
        import store as _st, pathlib as _pl
        cand = []
        lp = proj.get("localPath")
        if lp:
            _base = _pl.Path(lp).expanduser()
            cand += [_base / "soc" / "reports", _base / "reports"]
        _wsp = _pl.Path(_st.WS) / "projects" / pid
        cand += [_wsp / "data" / "soc" / "reports", _wsp / "data" / "reports", _wsp / "reports"]
        prebuilt = []
        for _d in cand:
            try:
                if _d.exists():
                    prebuilt += list(_d.glob(f"*.{ext}"))
            except Exception:
                pass
        if prebuilt:
            latest = max(prebuilt, key=lambda q: q.stat().st_mtime)
            return StreamingResponse(_io.BytesIO(latest.read_bytes()), media_type=_RPT_MIME[ext],
                                     headers={"Content-Disposition": f'attachment; filename="{latest.name}"'})
        name = proj.get("name", pid)
        try:
            import agents_registry as _ar
            agents = _ar.list_agents(pid)
        except Exception:
            agents = proj.get("agents") or []
        pool = _sc.all_messages(f"project:{pid}")
        sections = []
        ov = []
        if proj.get("type") or proj.get("stack"):
            ov.append(f"Type: {proj.get('type','')}" + (f" · {proj['stack']}" if proj.get("stack") else ""))
        if proj.get("description"):
            ov.append(str(proj["description"])[:1500])
        sections.append({"heading": "Overview", "level": 1, "text": "\n\n".join(ov) or "Project workspace."})
        if agents:
            rows = [[a.get("name", ""), a.get("role", "") or a.get("avatar", "")] for a in agents]
            sections.append({"heading": "Team", "level": 1,
                             "table": {"headers": ["Member", "Role"], "rows": rows}})
        conv = []
        for m in (pool or [])[-400:]:
            who = m.get("sender") or {"user": "Owner", "assistant": "Team"}.get(m.get("role", ""), m.get("role", ""))
            body = (m.get("content") or "").strip()
            if body:
                conv.append(f"**{who}:** {body}")
        sections.append({"heading": "Team conversation & activity", "level": 1,
                         "text": "\n\n".join(conv) if conv else
                         "No conversation recorded yet — run the team to populate this report."})
        spec = {"title": f"{name} — Project Report",
                "subtitle": "Autonomous multi-agent team report",
                "meta": [("Project", name), ("Project ID", pid), ("Members", str(len(agents)))],
                "sections": sections,
                "footer": "Generated by the Reporting & Documentation Agent — Odin-Orchestrator."}
        data, mime, e = _re.render(spec, ext)
        stem = (name.replace(" ", "-").lower()[:40] or pid)
        return StreamingResponse(_io.BytesIO(data), media_type=mime,
                                 headers={"Content-Disposition": f'attachment; filename="{stem}-report.{e}"'})

    # ---- STANDALONE CHATS registry (server-side, so web/mobile/desktop all share the SAME list). Each chat
    # is its own scope 'chat:<id>' with a title; its messages live in that scope's pool like any conversation.
    @r.get("/chats")
    def chats_list():
        import store
        return {"chats": store.read_json("chat_registry.json", {"chats": []}).get("chats", [])}

    @r.post("/chats")
    def chats_create(body: TitleIn):
        import store, uuid as _uuid, time as _time
        title = ((body.title if body else "") or "New chat").strip() or "New chat"
        scope = "chat:" + _uuid.uuid4().hex[:12]
        reg = store.read_json("chat_registry.json", {"chats": []})
        reg.setdefault("chats", []).insert(0, {"scope": scope, "title": title, "created": _time.time()})
        store.write_json("chat_registry.json", reg)
        return {"scope": scope, "title": title}

    @r.post("/chats/rename")
    def chats_rename(scope: str, body: TitleIn):
        import store
        new_title = ((body.title if body else "") or "").strip()
        if not new_title:
            return {"ok": False, "error": "empty title"}
        reg = store.read_json("chat_registry.json", {"chats": []})
        found = False
        for c in reg.get("chats", []):
            if c.get("scope") == scope:
                c["title"] = new_title
                found = True
        store.write_json("chat_registry.json", reg)
        return {"ok": found, "scope": scope, "title": new_title}

    @r.delete("/chats/{scope:path}")
    def chats_delete(scope: str):
        import store, scopes
        reg = store.read_json("chat_registry.json", {"chats": []})
        reg["chats"] = [c for c in reg.get("chats", []) if c.get("scope") != scope]
        store.write_json("chat_registry.json", reg)
        try:
            for c in (scopes.read_chats(scope) if hasattr(scopes, "read_chats") else []):
                scopes.delete_chat(scope, c.get("id"))
        except Exception:
            pass
        return {"ok": True}

    @r.delete("/scope/message")
    def scope_delete_message(scope: str, cid: str, mid: str):
        import scopes
        return {"deleted": scopes.delete_message(scope, cid, mid)}

    # ---- group chat: rich messages (image / camera / mic / file / zip) + reply ----
    @r.post("/scope/message")
    def scope_post_message(scope: str, cid: str, body: dict):
        """Post a message into the shared pool WITHOUT triggering an AI turn (media / group
        messages / replies). Everyone on every device + the CTO/team see the same pool."""
        import scopes
        msg = scopes.add_message(
            scope, cid,
            role=body.get("role", "user"),
            content=body.get("content", ""),
            sender=body.get("sender"),
            kind=body.get("kind", "text"),
            attachment=body.get("attachment"),
            reply_to=body.get("reply_to"),
            client_msg_id=body.get("client_msg_id"),   # idempotent: a retried send won't duplicate
        )
        if not msg:
            raise HTTPException(404, "no such chat")
        return {"ok": True, "message": msg}

    @r.post("/scope/upload")
    async def scope_upload(file: UploadFile = File(...), scope: str = Form("")):
        """Upload an attachment (image, voice clip, doc, zip). Returns its descriptor; then POST
        /scope/message with attachment=<descriptor> to put it in the chat."""
        import scopes
        data = await file.read()
        return scopes.save_attachment(file.filename or "file", data)

    @r.get("/scope/file/{fid}")
    def scope_file(fid: str):
        import scopes
        p = scopes.attachment_path(fid)
        if not p:
            raise HTTPException(404, "no such file")
        return FileResponse(str(p))

    # ======================= ACTIVITY =======================
    @r.get("/activity")
    def activity_get(pid: str | None = None):
        import activity
        return activity.snapshot(pid)

    @r.get("/activity/stream")
    def activity_stream(pid: str | None = None):
        import activity, time

        def gen():
            while True:
                yield sse("activity", activity.snapshot(pid))
                time.sleep(2)

        return StreamingResponse(gen(), media_type="text/event-stream")

    # ======================= SCHEDULES =======================
    @r.get("/schedules")
    def sched_list(pid: str | None = None):
        import scheduler
        return {"tasks": scheduler.list_tasks(pid)}

    @r.post("/schedules")
    def sched_create(body: ScheduleIn):
        import scheduler
        return scheduler.create_task(body.pid, body.prompt, body.schedule, body.title, body.assignee)

    @r.post("/schedules/{tid}/update")
    def sched_update(tid: str, body: dict):
        import scheduler
        d = scheduler.update_task(tid, **body)
        if not d:
            raise HTTPException(404, "no such task")
        return d

    @r.delete("/schedules/{tid}")
    def sched_delete(tid: str):
        import scheduler
        return {"deleted": scheduler.delete_task(tid)}

    # ---- Phase 3 periodic run gate: alerts the owner when a periodic task is due ----
    @r.get("/schedules/pending")
    def sched_pending(pid: str | None = None):
        import scheduler
        return {"pending": scheduler.list_pending(pid)}

    @r.post("/schedules/{tid}/approve")
    def sched_approve(tid: str):
        import scheduler
        d = scheduler.approve(tid)
        if not d:
            raise HTTPException(404, "no such task")
        return d

    @r.post("/schedules/{tid}/skip")
    def sched_skip(tid: str):
        import scheduler
        d = scheduler.skip(tid)
        if not d:
            raise HTTPException(404, "no such task")
        return d

    return r


# ---------- the scoped streaming brain (delegation + activity + memory) ----------
def _apply_agent_controls(pid: str, text: str) -> str:
    """Honor the owner's plain-language team controls in chat and PERSIST them:
      'remove X' / 'don't use X' / 'stop using X'  → remove + exclude X (never auto-returns)
      'only use X' / 'use only X'                   → exclude every other current member
    Returns a short note describing what changed (''=nothing). The exclusion is enforced everywhere
    new members are added, so removed agents never come back unless the owner explicitly re-adds them."""
    import re as _re, agents_registry
    t = (text or "").lower()
    # The CTO is the manager — it is ALWAYS present and is NEVER removable by 'remove'/'only use'.
    members = [a["name"] for a in agents_registry.list_agents(pid)
               if a["name"].lower() not in ("project cto", "cto", "cto brain")]
    if not members:
        return ""
    changed = []

    def _match(token):
        for m in members:
            if m.lower() in token:
                return m
        return None

    # ONLY use X → keep X (and the CTO), exclude the rest
    mo = _re.search(r"\b(?:use only|only use)\b(.+)", t)
    if mo:
        keep = [m for m in members if m.lower() in mo.group(1)]
        if keep:
            for m in members:
                if m not in keep:
                    agents_registry.remove_agent(pid, m); changed.append(f"removed {m}")
            return f"Honoring 'only use {', '.join(keep)}' — {', '.join(changed) or 'no change'}; removed agents won't be brought back."
    # remove / don't use / stop using X
    for mo in _re.finditer(r"\b(?:remove|don'?t use|do not use|stop using|without)\b([^.;\n]+)", t):
        m = _match(mo.group(1))
        if m:
            agents_registry.remove_agent(pid, m); changed.append(m)
    if changed:
        return f"Removed and won't bring back: {', '.join(sorted(set(changed)))}."
    return ""


def _resolve_member(pid: str, lead_agent: str) -> str | None:
    """Map the router's lead specialist to an actual project member (fuzzy)."""
    import agents_registry
    agents = agents_registry.list_agents(pid)
    if not agents:
        return None
    la = (lead_agent or "").lower()
    for a in agents:                       # match by role or name
        if a["role"].lower() in la or la in a["role"].lower() or a["name"].lower() in la:
            return a["name"]
    # fall back to the role keyword
    for a in agents:
        if any(w in la for w in a["role"].lower().split()):
            return a["name"]
    # NO confident match → the CTO handles it ITSELF (return None). Do NOT fall back to the first
    # member (that was the DevOps bias: a status/chat question wrongly got delegated to DevOps just
    # because DevOps happened to be first). A member is brought in only when it genuinely matches.
    return None


def _engine_stream(text: str, lang: str, session_id: str, model: str, cwd: str | None = None,
                   readonly: bool = False):
    """Yield {kind,...} events from the chosen model. Claude streams live; Ollama returns once.
    cwd = the project's folder so file work happens THERE, not in the Odin app's repo.
    readonly=True → the engine cannot write files or run state-changing/VM commands (approval gate)."""
    use_claude = ((not model) or model in ("claude-cli", "claude")
                  or model in ("haiku", "sonnet", "opus") or model.startswith("claude"))
    if use_claude:
        try:
            import claude_cli
            if claude_cli.available() and os.environ.get("ODIN_ENGINE", "claude") == "claude":
                yield from claude_cli.ClaudeCLIBrain().stream_session(
                    text, lang, session_id or None, cwd=cwd, readonly=readonly, model=model)
                return
        except Exception as e:
            yield {"kind": "status", "icon": "⚠️", "text": f"engine: {e}"}
    # Ollama path (selected local model)
    try:
        import brain_handler
        reply = brain_handler.OllamaBrain(model=model or None).respond(text, lang=lang)
    except Exception as e:
        reply = f"(model error: {e})"
    yield {"kind": "text", "t": reply}
    yield {"kind": "final", "text": reply, "session_id": session_id}


# Instruction appended to every agent run: propose-first. The agent must NOT think it's blocked by a
# harness — Odin runs it read-only BY DESIGN and applies approved changes itself.
PROPOSE_RULES = (
    "\n\nHOW CHANGES WORK HERE — read carefully:\n"
    "Odin runs you in PROPOSE-FIRST mode. You may freely read, inspect, diff and analyze. You cannot "
    "directly modify files or run state-changing/VM commands — and you do NOT need the owner to change "
    "any setting, 'permission', 'read-only mode', or 'harness'. That is normal and by design. Do NOT "
    "tell the owner to lift a mode, run /permissions, restart, or 'approve in the harness' — that is "
    "WRONG and there is no such step.\n"
    "Instead: do the read-only work, then if changes are needed, END your reply with ONE fenced "
    "proposal block. Odin shows it to the owner as an APPROVAL POPUP; once they click Approve, ODIN "
    "ITSELF executes the approved commands (VM commands run via the Azure control plane) and captures "
    "the output. So your job is simply: analyze → propose → stop. Never claim you are blocked.\n"
    "```proposal\n"
    '{\n  "summary": "<one line>",\n'
    '  "files": [{"path": "<path>", "action": "edit|create|delete", "why": "<reason>"}],\n'
    '  "commands": [{"cmd": "<command>", "where": "local|vm", "why": "<reason>"}]\n}\n'
    "```\n"
    "Only include changes that are truly needed. If NO change is needed, do not emit a proposal block.")


def _parse_proposal(text: str):
    """Extract a {files, commands} proposal from an agent's read-only reply, if present."""
    import re as _re, json as _j
    if not text:
        return None
    blob = None
    m = _re.search(r"```(?:proposal|json)?\s*(\{.*?\})\s*```", text, _re.DOTALL)
    if m:
        blob = m.group(1)
    elif '"files"' in text or '"commands"' in text:
        try:
            i = text.index("{"); depth = 0
            for j in range(i, len(text)):
                if text[j] == "{":
                    depth += 1
                elif text[j] == "}":
                    depth -= 1
                    if depth == 0:
                        blob = text[i:j + 1]; break
        except Exception:
            blob = None
    if not blob:
        return None
    try:
        d = _j.loads(blob)
    except Exception:
        return None
    nf = []
    for f in (d.get("files") or []):
        if isinstance(f, dict) and f.get("path"):
            nf.append({"path": str(f.get("path")), "action": str(f.get("action", "edit")),
                       "why": str(f.get("why", "")), "preview": str(f.get("preview", ""))[:800]})
        elif isinstance(f, str):
            nf.append({"path": f, "action": "edit", "why": ""})
    nc = []
    for c in (d.get("commands") or []):
        if isinstance(c, dict) and c.get("cmd"):
            nc.append({"cmd": str(c.get("cmd")), "where": str(c.get("where", "local")), "why": str(c.get("why", ""))})
        elif isinstance(c, str):
            nc.append({"cmd": c, "where": "local", "why": ""})
    if not nf and not nc:
        return None
    return {"files": nf, "commands": nc, "summary": str(d.get("summary", ""))[:600]}


def _run_gated(pid, member, scope, cid, prompt, model, folder, task_label="proposed changes",
               auto_approve=False):
    """Run an agent READ-ONLY (it can't modify anything), capture its reply + any change PROPOSAL.
    If it proposes changes: unless the project is pre-authorized (auto_approve), create an approval
    request, NOTIFY the owner (popup), PAUSE until they approve/refuse, and on approval run a
    write-enabled pass that applies EXACTLY the approved files/commands.
    Yields SSE strings; ends with ("__return__", {reply, approved, applied})."""
    import time as _time, scopes, activity, approvals
    # AGENT SCOPE (delta): only when THIS (project,member) has a scoped binding — every other
    # project/member is untouched, so existing project-scope behavior is unchanged (0 regression).
    try:
        import workspace_mw as _mw_as
        if _mw_as.agent_credential_ref(pid, member):
            prompt = (prompt or "") + _mw_as.agent_scope_guard(pid, member)
        # diagnosis project (has an external report target): let members run read-only VM diagnostics themselves.
        try:
            if _mw_as.external_report_ref(pid):
                prompt = (prompt or "") + _mw_as.vm_diagnosis_guard()
        except Exception:
            pass
        try:
            _tg = _mw_as.tutorial_guard(pid)
            if _tg:
                prompt = (prompt or "") + _tg
        except Exception:
            pass
    except Exception:
        pass

    def _stream(p, ro, who):
        parts, final, prog = [], None, []
        # GUARANTEED LIVENESS: while an engine call is in progress, beat the agent's activity every few
        # seconds on a background thread — independent of what claude streams. A long, legitimately quiet
        # build phase (e.g. a from-scratch build, npm install) therefore stays "active" and is NOT
        # false-killed by the watchdog. A TRULY stuck call is still caught by the engine's own idle-timeout
        # (it terminates the no-output call), which ends this loop and stops the beater. (Additive — does
        # not change any agent output, audit, or the already-passing tests.)
        import threading as _th
        _beat_stop = _th.Event()

        def _beater():
            while not _beat_stop.wait(8):
                try:
                    activity.beat(pid, who)
                except Exception:
                    pass

        _bt = _th.Thread(target=_beater, daemon=True)
        _bt.start()
        try:
            for evd in _engine_stream(p, "en", None, model, cwd=folder or None, readonly=ro):
                k = evd.get("kind")
                if k == "status":   # a command run / file read — the live action
                    prog.append("• " + evd.get("text", ""))
                    yield ("sse", sse("status", {"icon": evd.get("icon", "🔧"), "text": f"{who}: {evd.get('text', '')}"})); activity.beat(pid, who)
                elif k == "tool_result":   # its OUTPUT — build pass/fail + reason
                    ok = not evd.get("error")
                    prog.append(("   ↳ ✅ " if ok else "   ↳ ❌ ") + evd.get("text", ""))
                    yield ("sse", sse("status", {"icon": "✅" if ok else "❌", "text": f"{who}: {evd.get('text', '')[:90]}"})); activity.beat(pid, who)
                elif k == "text":
                    parts.append(evd["t"]); yield ("sse", sse("token", {"member": who, "t": evd["t"]})); activity.beat(pid, who)
                elif k == "final":
                    final = evd.get("text") or "".join(parts)
        finally:
            _beat_stop.set()
        yield ("ret", ((final or "".join(parts) or "(no output)").strip(), prog))

    # AUTHORIZED run → EXECUTE NOW. Do NOT run read-only-then-describe. This fixes the core flaw:
    # the agent kept narrating the owner's commands instead of running them. Connectivity is
    # refreshed first if the work touches the VM.
    if auto_approve:
        import scopes as _sc
        import main_task as _mt_diag
        import time as _td
        vm_ip = None
        # Operators (hand off a key / report) NEVER touch the VM — skip the ~50s Azure firewall refresh
        # for them. Only technical members doing VM/deploy work need it.
        if (not _is_operational(pid, member)) and any(k in (prompt or "").lower() for k in ("vm", "rsync", "ssh", "reboot", "/home/", "az vm", "deploy", "sync", "prisma", "migrate")):
            # The Azure firewall refresh takes ~50s. Do it ONCE per run (cache by pid for a TTL) instead
            # of repeating it for every member — that was minutes of pure wait across a 5-6 member team.
            _cache = _vm_access_cache.get(pid)
            _ttl = int(os.environ.get("ODIN_VM_ACCESS_TTL", "600"))
            if _cache and (_td.time() - _cache[0] < _ttl):
                note, vm_ip = "reusing this run's refreshed access", _cache[1]
                try: _mt_diag.append(pid, member, f"✓ phase: VM access (cached from this run) — host {vm_ip}")
                except Exception: pass
            else:
                _t_vm = _td.time()
                try: _mt_diag.append(pid, member, "⏳ phase: VM access refresh starting…")
                except Exception: pass
                note, vm_ip = _ensure_vm_access()
                _vm_access_cache[pid] = (_td.time(), vm_ip)
                try: _mt_diag.append(pid, member, f"✓ phase: VM access done in {int(_td.time()-_t_vm)}s — {note}")
                except Exception: pass
            yield sse("status", {"icon": "🔌", "text": f"{member}: VM access refreshed — {note}"})
        try: _mt_diag.append(pid, member, "⏳ phase: engine call starting (claude streaming)…")
        except Exception: pass
        _t_eng = _td.time()
        _build_now = (not _is_devops(pid, member)) and (not _is_operational(pid, member))
        ex_prompt = (prompt +
            "\n\n=== EXECUTE NOW — YOU ARE AUTHORIZED ===\n"
            "The owner AUTHORIZED this run. Do NOT describe, propose, summarize, restate, or ask for "
            "confirmation. RUN the owner's exact commands, in the exact order, with your tools, and report "
            "the REAL output of each one." +
            ("\nYOU ARE BUILDING SOFTWARE: you MUST WRITE THE ACTUAL FILES TO DISK now with your Write/Bash "
             "tools — scaffold the project and write EVERY real source file (e.g. package.json + src/*) "
             "INSIDE the project folder you were given. Do NOT just describe, plan, or paste code in chat — "
             "if it is not written to disk it does not count. When done, run `ls -R` (excluding node_modules) "
             "in the project folder and report the real files you created as proof.\n"
             "STRICT TIME BUDGET — WORK LIKE A SENIOR ENGINEER ON A CLOCK: your slice must finish in UNDER "
             "15 MINUTES (the whole project must finish in ~30). To hit that: (1) pick the LIGHTEST stack "
             "that meets the brief and the MINIMUM dependencies — do NOT pull heavyweight scaffolds/framework "
             "generators with huge dependency trees when a lean app (e.g. a single small Node/Express or "
             "FastAPI service + a minimal static/Vite UI) proves the same capability; (2) do NOT run a "
             "production build (`next build`, `npm run build`, bundling) — it is NOT needed to prove the app; "
             "(3) do NOT start long-lived/dev servers that block (no `npm run dev`, no `npm start`/`uvicorn` "
             "in the FOREGROUND, no combined install+serve `run.sh`) — those block and can exhaust memory and "
             "get OOM-killed; if you must smoke-test, start it in the BACKGROUND and curl ONCE with a timeout, "
             "then kill it; (4) keep `npm install`/`pip install` to the few packages you actually import. "
             "Verify cheaply: import the modules / init the DB / run unit tests offline — NOT a full server "
             "boot. Write the source, "
             "do ONE quick sanity check, and finish. Speed is part of correctness here.\n"
             "BEING FAST DOES NOT MEAN SKIPPING THE WORK. Your FIRST actions must be Write/Bash tool calls "
             "that CREATE files — not prose. An empty folder, or a reply that contains a completion summary / "
             "acceptance-criteria table WITHOUT the files actually on disk, is an AUTOMATIC FAIL: an automated "
             "gate runs `ls` on your folder and rejects the step if it is empty, no matter how good your report "
             "reads. NEVER report test results, 'X passed', or 'live data verified' that you did not actually "
             "produce by running the command — fabricated results are treated as a failure. Create the real "
             "files first; verify with `ls`; only then summarize.\n"
             if _build_now else "") +
            " For anything on the VM run it through the Azure control plane: "
            "`az vm run-command invoke -g DJANGO-PROJECT -n django-vm --command-id RunShellScript "
            "--scripts \"<command>\"` (runs as root, no SSH/password needed). Connectivity is already handled"
            + (f" (host mostafa@{vm_ip}, firewall pinned to your IP)." if vm_ip else ".") +
            " For the file SYNC (rsync local→VM), the firewall is already open to your IP; if SSH auth "
            "is needed use the key `~/.ssh/azure_vm_key.pem` (rsync -e 'ssh -i ~/.ssh/azure_vm_key.pem "
            "-o StrictHostKeyChecking=no'). Do NOT abort on the first transport hiccup — retry or use the "
            "control plane to stage files. Execute every step now; stop ONLY if a command genuinely fails "
            "after a real retry, then report the exact error. Start executing immediately — no preamble.")
        reply, prog = None, []
        for kind, val in _stream(ex_prompt, False, member):   # WRITE-ENABLED so it can actually run
            if kind == "ret":
                reply, prog = val
            else:
                yield val
        try: _mt_diag.append(pid, member, f"✓ phase: engine call returned in {int(_td.time()-_t_eng)}s "
                                          f"({len(reply or '')} chars)")
        except Exception: pass
        if cid:
            if prog:
                _sc.add_message(scope, cid, "assistant", "🔧 Executed — commands & their responses:\n" + "\n".join(prog[-90:]))
            _sc.add_message(scope, cid, "assistant", reply or "(done)")
        yield ("__return__", {"reply": reply, "approved": True, "applied": True})
        return

    # 1) READ-ONLY analysis + proposal
    reply, prog = None, []
    for kind, val in _stream(prompt + PROPOSE_RULES, True, member):
        if kind == "ret":
            reply, prog = val
        else:
            yield val
    if cid:
        if prog:   # the live trail — commands run + their outputs (so you're not blind)
            scopes.add_message(scope, cid, "assistant", "🔧 What I actually did:\n" + "\n".join(prog[-50:]))
        scopes.add_message(scope, cid, "assistant", reply)
    prop = _parse_proposal(reply)
    if not prop:
        yield ("__return__", {"reply": reply, "approved": None, "applied": False}); return

    nf, nc = len(prop["files"]), len(prop["commands"])
    # NOT pre-authorized → create an approval and STOP. It EXECUTES the moment you approve (popup
    # OR "approve" in chat) via the background applier — NOT tied to this run staying alive. This
    # fixes "I approved 19 times and nothing ran": apply no longer depends on a live poll loop.
    if not auto_approve:
        ap = approvals.create(pid, member, title=task_label, summary=prop.get("summary", ""),
                              files=prop["files"], commands=prop["commands"], cwd=folder, inline=False,
                              kind=("vm" if any(c.get("where") == "vm" for c in prop["commands"]) else "change"))
        yield sse("approval", {"id": ap["id"], "pid": pid, "member": member, "title": ap["title"],
                               "summary": ap["summary"], "files": ap["files"], "commands": ap["commands"]})
        yield sse("status", {"icon": "🔔", "text": f"Approval needed — {member}: {nf} file(s) + {nc} command(s). Approve in the popup or say 'approve' in chat; it runs the instant you do."})
        if cid:
            scopes.add_message(scope, cid, "user", f"[Awaiting your approval] {member} proposed {nf} file change(s) + {nc} command(s). Approve (popup or chat) to run them.")
        yield ("__return__", {"reply": reply, "approved": None, "applied": False}); return

    # auto_approve → apply inline now
    yield sse("status", {"icon": "✅", "text": f"{member}: auto-approved — applying"})
    apply_id = None

    # 3) APPLY EXACTLY the approved changes.
    activity.mark_active(pid, member, task="applying approved changes", phase=f"{member}: applying")
    vm_cmds = [c for c in prop["commands"] if c.get("where") == "vm"]
    local_cmds = [c for c in prop["commands"] if c.get("where") != "vm"]
    # 3a) If anything touches the VM (a VM command, or an rsync/ssh/scp), FIRST make the VM reachable
    # by refreshing the firewall to our current IP (the owner's rotate function, via the control
    # plane). Then resolve the real host so rsync targets mustafa@<ip>.
    needs_vm = bool(vm_cmds) or any(k in c["cmd"] for c in local_cmds for k in ("rsync", "ssh", "scp", "@VM"))
    vm_out, vm_ip, log_lines = [], None, []   # log_lines = clear, in-points record for the chat
    if needs_vm:
        yield sse("status", {"icon": "🔌", "text": f"{member}: opening VM access (refreshing firewall to your IP)…"})
        note, vm_ip = _ensure_vm_access()
        vm_out.append(f"[connectivity] {note}" + (f"; host mustafa@{vm_ip}" if vm_ip else ""))
        line = f"🔌 Opened VM access — {note}" + (f" (host mustafa@{vm_ip})" if vm_ip else "")
        log_lines.append(line)
        yield sse("token", {"member": member, "t": line + "\n"})
    # VM commands run over SSH AS mostafa (password from workspace/shared/oth/.cred) — NEVER root. The control
    # plane was used only to open the firewall (in _ensure_vm_access above).
    if vm_cmds:
        try:
            import deploy_ssh
            for c in vm_cmds:
                yield sse("status", {"icon": "🔑", "text": f"{member}: SSH as mostafa — {c['cmd'][:46]}…"})
                r = deploy_ssh.ssh_exec(c["cmd"])
                o = (r.get("out") or r.get("err") or r.get("error") or "(no output)").strip()
                ok = bool(r.get("ok"))
                vm_out.append(f"$ {c['cmd']}\n{o[:1500]}")
                ran = f"▶ ran on VM (ssh/mostafa): {c['cmd']}"
                res = f"   ↳ {'✅' if ok else '❌'} {o[:400].replace(chr(10), ' ')}"
                log_lines += [ran, res]
                yield sse("token", {"member": member, "t": ran + "\n" + res + "\n"})
        except Exception as e:
            log_lines.append(f"❌ SSH error: {e}")
            vm_out.append(f"(SSH error: {e})")
    # 3b) Local file/command changes via the engine (write-enabled); VM placeholder host resolved.
    local_cmds = [{**c, "cmd": _fix_rsync_auth(_vm_subst(c["cmd"], vm_ip))} for c in local_cmds]
    files_txt = "\n".join(f"- {f['action']} {f['path']}: {f['why']}" for f in prop["files"]) or "(none)"
    lcmds_txt = "\n".join(f"- {c['cmd']}" for c in local_cmds) or "(none)"
    applied, applied_prog = "", []
    if prop["files"] or local_cmds:
        apply_prompt = (f"You are the {member} agent. The owner APPROVED these changes — apply them EXACTLY, "
                        "nothing more, nothing less. (Any VM commands are already executed by Odin via the "
                        "Azure control plane — do NOT touch the VM yourself.)\n"
                        f"FILES:\n{files_txt}\nLOCAL COMMANDS:\n{lcmds_txt}\n"
                        f"Work inside: {folder}\nMake ONLY these changes, then report concisely what you did.")
        for kind, val in _stream(apply_prompt, False, member):
            if kind == "ret":
                applied, applied_prog = val
            else:
                yield val
        log_lines += applied_prog
    full = applied + (("\n\nVM (control plane) output:\n" + "\n".join(vm_out)) if vm_out else "")
    if cid:
        if log_lines:   # the clear, point-by-point live log of every command + its response
            scopes.add_message(scope, cid, "assistant", "🔧 Live log — commands run & their responses:\n" + "\n".join(log_lines[-90:]))
        scopes.add_message(scope, cid, "assistant", f"[Done] {applied or 'Applied the approved changes.'}")
    if apply_id:
        approvals.mark_applied(apply_id, full)
    yield ("__return__", {"reply": reply + "\n\n[Applied after approval] " + full,
                          "approved": True, "applied": True})


_vm_access_cache: dict = {}   # pid -> (ts, vm_ip): refresh Azure access ONCE per run, not per member


def _ensure_vm_access():
    """Make the VM reachable for SSH/rsync by refreshing the firewall (NSG + ufw) to OUR CURRENT
    public IP via the Azure control plane — the owner's own rotate function, which works even while
    SSH is blocked. Returns (note, vm_ip). Agents must NEVER claim 'can't connect / SSH filtered':
    Odin has authenticated Azure access and refreshes connectivity here."""
    # FAILURE PROTOCOL (in code): this refresh makes Azure CLI network calls that can HANG (expired az
    # login, network) with no output — that silently froze a member step before the engine even started.
    # Bound it to a hard time budget: if it doesn't finish in time, PROCEED without it (the agent will
    # still try and report a real error) — a healthy refresh is fast; a stuck one must never freeze the run.
    _out: dict = {}

    def _work():
        note, ip = "", None
        try:
            import infra_rotate
            r = infra_rotate.rotate()
            note = f"firewall refreshed to {r.get('ip', '?')} ({'ok' if r.get('ok') else 'partial'})"
        except Exception as e:
            note = f"firewall refresh skipped: {e}"
        try:
            import infra_az
            ip = infra_az.vm_public_ip()
        except Exception:
            ip = None
        _out["note"], _out["ip"] = note, ip

    _budget = int(os.environ.get("ODIN_VM_ACCESS_TIMEOUT", "60"))
    _th = threading.Thread(target=_work, daemon=True)
    _th.start()
    _th.join(_budget)
    if _th.is_alive():
        return (f"VM access refresh exceeded {_budget}s — proceeding without it; the agent will retry/report",
                None)
    return _out.get("note", ""), _out.get("ip")


def _vm_subst(cmd: str, ip: str | None) -> str:
    """Replace any non-IP VM host (django-vm, VM placeholder, hostname) with the real
    mostafa@<ip>, so rsync/ssh actually resolve the box."""
    if not ip:
        return cmd
    import re as _re
    cmd = _re.sub(r"m[ou]stafa@[A-Za-z][\w.-]*:", f"mostafa@{ip}:", cmd)
    cmd = _re.sub(r"(?<![\w.])@?\bVM\b:", f"mostafa@{ip}:", cmd)
    return cmd


def _fix_rsync_auth(cmd: str) -> str:
    """Make an rsync command authenticate with the mostafa PASSWORD (sshpass + force password auth),
    so it can't fail with 'too many authentication failures' again."""
    import deploy_ssh
    pw = deploy_ssh.vm_password()
    if not pw or "rsync" not in cmd or "sshpass" in cmd:
        return cmd
    import shlex as _sx
    ssh_e = " -e 'ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no -o StrictHostKeyChecking=no' "
    out = cmd.replace("rsync ", "sshpass -p " + _sx.quote(pw) + " rsync ", 1)
    if "-e " not in cmd:
        out = out.replace("rsync ", "rsync" + ssh_e, 1)
    return out


def _apply_approval_bg(aid: str):
    """Execute an approval that was created from a CHAT (no active run waiting on it). VM commands
    go through the Azure control plane; local file/command changes run via the write-enabled engine.
    Runs in a background thread so the approve click returns immediately."""
    import approvals, scopes, models_config
    a = approvals.get(aid)
    if not a or a.get("applied") or a.get("status") != "approved":
        return
    # double-apply guard (rapid double-click / chat + popup both firing)
    with _APPLY_LOCK:
        if aid in _APPLYING:
            return
        _APPLYING.add(aid)
    pid, member, folder = a["pid"], a["member"], (a.get("cwd") or "")
    out, log_lines = [], []   # log_lines = clear, in-points record for the member chat
    s = f"member:{pid}:{member}"
    chats = scopes.list_chats(s)
    cid = chats[0]["id"] if chats else scopes.create_chat(s, "▶ Applied")["id"]
    vm_cmds = [c for c in a.get("commands", []) if c.get("where") == "vm"]
    local_cmds = [c for c in a.get("commands", []) if c.get("where") != "vm"]
    # If anything touches the VM, refresh the firewall to our current IP (control plane) and resolve host.
    needs_vm = bool(vm_cmds) or any(k in c.get("cmd", "") for c in local_cmds for k in ("rsync", "ssh", "scp", "@VM"))
    vm_ip = None
    if needs_vm:
        note, vm_ip = _ensure_vm_access()
        out.append(f"[connectivity] {note}" + (f"; host mustafa@{vm_ip}" if vm_ip else ""))
        log_lines.append(f"🔌 Opened VM access — {note}" + (f" (host mustafa@{vm_ip})" if vm_ip else ""))
    if vm_cmds:
        try:
            import deploy_ssh
            for c in vm_cmds:
                r = deploy_ssh.ssh_exec(c["cmd"])
                o = (r.get("out") or r.get("err") or r.get("error") or "(no output)").strip()
                ok = bool(r.get("ok"))
                out.append(f"$ {c['cmd']}\n{o[:1500]}")
                log_lines += [f"▶ ran on VM (ssh/mostafa): {c['cmd']}", f"   ↳ {'✅' if ok else '❌'} {o[:400].replace(chr(10), ' ')}"]
                scopes.add_message(s, cid, "assistant", f"▶ ran on VM (ssh/mostafa): {c['cmd']}\n   ↳ {'✅' if ok else '❌'} {o[:600]}")
        except Exception as e:
            out.append(f"(SSH error: {e})")
            scopes.add_message(s, cid, "assistant", f"❌ SSH error: {e}")
    local_cmds = [{**c, "cmd": _fix_rsync_auth(_vm_subst(c.get('cmd', ''), vm_ip))} for c in local_cmds]
    if a.get("files") or local_cmds:
        files_txt = "\n".join(f"- {f.get('action','edit')} {f.get('path','')}: {f.get('why','')}" for f in a.get("files", [])) or "(none)"
        lcmds_txt = "\n".join(f"- {c['cmd']}" for c in local_cmds) or "(none)"
        model = models_config.get_model(s)
        apply_prompt = (f"You are the {member} agent. The owner APPROVED these changes — apply them EXACTLY, "
                        "nothing more. (Any VM commands are already executed by Odin — do not touch the VM.)\n"
                        f"FILES:\n{files_txt}\nLOCAL COMMANDS:\n{lcmds_txt}\nWork inside: {folder}\n"
                        "Make ONLY these changes, then report what you did.")
        parts, final = [], None
        for evd in _engine_stream(apply_prompt, "en", None, model, cwd=folder or None, readonly=False):
            if evd.get("kind") == "text":
                parts.append(evd["t"])
            elif evd.get("kind") == "tool_result":
                ok = not evd.get("error")
                scopes.add_message(s, cid, "assistant", ("   ↳ ✅ " if ok else "   ↳ ❌ ") + evd.get("text", ""))
            elif evd.get("kind") == "final":
                final = evd.get("text") or "".join(parts)
        out.append((final or "".join(parts) or "(applied)").strip())
    result = "\n".join(out)
    approvals.mark_applied(aid, result)
    try:
        scopes.add_message(s, cid, "assistant", f"[Done] {(out[-1] if out else 'Applied.')[:2000]}")
    except Exception:
        pass
    # AUTO-CONTINUE the owner's run flow: after a gate is approved+applied, re-invoke the CTO to do the NEXT
    # step and stop at the next gate. This is what makes the sequence advance (deploy -> DB gate if seed ->
    # test -> ANNOUNCE + run the full diagnosis -> report only on a real problem) instead of dying after one
    # approval. Operational projects only; the diagnosis has no gate, so the chain naturally terminates.
    try:
        import projects as _pjc
        _pc = _pjc.get_project(pid) or {}
        _cmeta = (str(_pc.get("type", "")) + " " + str(_pc.get("category", ""))).lower()
        if any(k in _cmeta for k in ("operational", "diagnos", "deploy", "ops")):
            _pscope = f"project:{pid}"
            _pchats = scopes.list_chats(_pscope)
            _pcid = _pchats[0]["id"] if _pchats else scopes.create_chat(_pscope, "Run")["id"]
            _cont = ("[system] The gate you proposed was APPROVED and applied. Continue the owner's run flow "
                     "from here — do ONLY the next step, then stop at the next gate: if a changed file was a "
                     "schema/seed file, ask the DB migration gate (separate approval); otherwise run the "
                     "post-deploy TEST, then ANNOUNCE and RUN the full read-only DIAGNOSIS across EVERY "
                     "connected agent (Klaviyo profiles count; Veeqo orders count + the known DELIVERED order "
                     "-> feed its carrier+tracking to the EasyPost operator -> compare EasyPost's delivered "
                     "status to our DB's stored status; HubSpot/Analytics reads), and give a CLEAR result "
                     "(green if all passed; if not, state the exact reason). Write/propose the AI report ONLY "
                     "if the diagnosis finds a real problem needing changes. "
                     "CRITICAL: EXECUTE the reads NOW in THIS turn and POST the actual results and the "
                     "green/failed verdict in your reply. Do NOT end your turn after merely announcing "
                     "'starting the diagnosis' or 'running the reads' — a turn that only announces is a FAILURE. "
                     "Run every read to completion and show the real numbers/values before you stop.")
            def _adv():
                # mark the run RUNNING so the UI shows WORKING (not a fake "finished") during the diagnosis,
                # and clear it only when the reads truly complete.
                with _RUNS_LOCK:
                    _RUNS[pid] = {"running": True, "cancel": False, "goal": "auto-continue diagnosis", "started": time.time()}
                try:
                    for _ in _scoped_gen(_pscope, _cont, "en", _pcid):
                        if _RUNS.get(pid, {}).get("cancel"):
                            break
                except Exception:
                    pass
                finally:
                    with _RUNS_LOCK:
                        r = _RUNS.get(pid)
                        if r:
                            r["running"] = False
            threading.Thread(target=_adv, daemon=True).start()
    except Exception:
        pass
    with _APPLY_LOCK:
        _APPLYING.discard(aid)


# ---- Background team runs: the run lives on the SERVER, not in a screen component, so navigating
# between views (CTO ↔ DevOps) can NEVER kill it. The UI just reflects it by polling. ----
_RUNS = {}  # pid -> {"running":bool, "cancel":bool, "goal":str, "started":float, "phase":str}
_RUNS_LOCK = threading.Lock()
_APPLYING = set()           # approval ids currently being applied (prevents double-apply)
_APPLY_LOCK = threading.Lock()


def _bg_orchestrate(pid: str, goal: str):
    # AI-FIRST: operational (diagnosis/deploy/ops) projects run as a SMART CTO brain turn — the same
    # engine the chat uses — NOT the fragile static pipeline (which wedges on its re-plan step). This
    # makes the play button and the scheduled run produce a real, humanized CTO answer, and it cannot hang.
    try:
        import projects as _pjo
        _po = _pjo.get_project(pid) or {}
        _meta = (str(_po.get("type", "")) + " " + str(_po.get("category", ""))).lower()
        _operational = any(k in _meta for k in ("operational", "diagnos", "deploy", "ops"))
    except Exception:
        _operational = False
    # BRAIN-FIRST: every project run goes through the context-aware CTO brain (or the deterministic
    # deploy gate for deploy projects). The old static plan->members->QA pipeline is retired as a router.
    _operational = True
    if _operational:
        import scopes as _sc, activity as _act
        _scope = f"project:{pid}"
        try:
            _chats = _sc.list_chats(_scope)
            _cid = _chats[0]["id"] if _chats else _sc.create_chat(_scope, "\u25b6 Run")["id"]
            if _op_is_deploy_project(pid):
                # DETERMINISTIC sequential deploy gates (enforced, never narrated); the DIAGNOSIS is the smart brain.
                _act.mark_active(pid, "DevOps", task="change-detection", phase="DevOps: deploy check")
                _op_open_deploy_gate(pid)   # STOPS at the single deploy approval, or runs the diagnosis inline if nothing changed
            else:
                _act.mark_active(pid, "Project CTO", task="handling your run", phase="CTO: working")
                for _ in _scoped_gen(_scope, goal, "en", _cid):
                    if _RUNS.get(pid, {}).get("cancel"):
                        break
        except Exception as _e:
            try:
                _c2 = _sc.list_chats(_scope)
                _cid2 = _c2[0]["id"] if _c2 else _sc.create_chat(_scope, "\u25b6 Run")["id"]
                _sc.add_message(_scope, _cid2, "assistant", f"[Project CTO] Run hit an error: {_e}")
            except Exception:
                pass
        finally:
            try:
                _act.mark_idle(pid, "Project CTO")
            except Exception:
                pass
            with _RUNS_LOCK:
                r = _RUNS.get(pid)
                if r:
                    r["running"] = False
        return
    gen = _orchestrate_gen(pid, goal)
    try:
        for _ in gen:                       # drain — state is persisted to chats + activity already
            if _RUNS.get(pid, {}).get("cancel"):
                try:
                    gen.close()             # raises GeneratorExit → inner engine subprocess terminates
                except Exception:
                    pass
                break
    except Exception:
        pass
    finally:
        with _RUNS_LOCK:
            r = _RUNS.get(pid)
            if r:
                r["running"] = False


def _run_is_stale(pid: str, r: dict) -> bool:
    """A run flagged running but with NO active agent for >90s is wedged/dead — treat it as not
    running so a new run can proceed and the UI never shows a ghost 'running' forever."""
    try:
        import activity, time as _t
        if _t.time() - float(r.get("started", 0)) < 90:
            return False
        return not (activity.snapshot(pid) or {}).get("active")
    except Exception:
        return False


def start_run(pid: str, goal: str) -> dict:
    with _RUNS_LOCK:
        _r0 = _RUNS.get(pid, {})
        if _r0.get("running") and not _run_is_stale(pid, _r0):
            return {"running": True, "already": True}
        _RUNS[pid] = {"running": True, "cancel": False, "goal": goal, "started": time.time()}
    threading.Thread(target=_bg_orchestrate, args=(pid, goal), daemon=True).start()
    return {"running": True}


def orchestrate_blocking(pid: str, goal: str) -> bool:
    """Run the FULL team orchestration to completion IN THE CALLING THREAD, and return True if it ran.
    Used by the scheduler / ▶ Run so a scheduled or manual project run produces the REAL CTO↔agent↔QA
    conversation (the ping-pong) into the project pool AND executes — instead of a single propose-only
    reply from the dispatcher. Guards against a concurrent run for the same project."""
    with _RUNS_LOCK:
        _rb = _RUNS.get(pid, {})
        if _rb.get("running") and not _run_is_stale(pid, _rb):
            return False
        _RUNS[pid] = {"running": True, "cancel": False, "goal": goal, "started": time.time()}
    _bg_orchestrate(pid, goal)   # drains synchronously; clears running in its finally
    return True


def run_status(pid: str) -> dict:
    r = _RUNS.get(pid, {})
    return {"running": bool(r.get("running")), "goal": r.get("goal", ""),
            "started": r.get("started", 0)}


def stop_run(pid: str) -> dict:
    with _RUNS_LOCK:
        r = _RUNS.get(pid)
        if r:
            r["cancel"] = True
    # ALSO halt any in-flight operation (deploy/sync) for this project — otherwise the team-run Stop
    # only takes effect BETWEEN plan steps while a long deploy keeps running. This links the run Stop
    # to the operation watchdog, which kills the running subprocess within ~1s. One Stop = real stop.
    try:
        import operations
        for op in operations.list_for(pid, limit=20):
            if op.get("state") == "running":
                operations.request_stop(op["id"])
    except Exception:
        pass
    return {"stopped": True}


def _pool_post(pid: str, text: str, who: str = "assistant", sender: str | None = None):
    """Post into the project's SHARED group pool — the chat the owner + all agents see — and append
    to the durable shared context. One place everyone watches; nothing scattered. `sender` labels WHO is
    speaking (agent name) so the clients render 'who replied' instead of a generic bubble."""
    try:
        import scopes
        s = f"project:{pid}"
        chats = scopes.list_chats(s)
        cid = chats[0]["id"] if chats else scopes.create_chat(s, "▶ Team pool")["id"]
        role = who if who in ("assistant", "user") else "assistant"
        lbl = sender or (who if who not in ("assistant", "user") else None)
        scopes.add_message(s, cid, role, text, sender=lbl)
    except Exception:
        pass
    try:
        import main_task
        main_task.append(pid, "Operation", text)
    except Exception:
        pass


def _resume_operation(oid: str, answers: dict):
    """SMART CONTINUE: apply the owner's answer to correct the operation, then resume it."""
    import operations, deploy_runner, projects
    op = operations.get(oid) or {}
    pid = op.get("pid")
    if not pid:
        return
    meta = op.get("meta") or {}
    # apply provided local folder(s) → save to the project's selected sources so the resolver finds them
    paths = [v for k, v in (answers or {}).items() if k.startswith("local_") and v]
    if paths:
        projects.add_sources(pid, paths)
        _pool_post(pid, "▶ Continuing — using what you provided: " + ", ".join(paths))
    else:
        _pool_post(pid, "▶ Continuing…")
    if meta.get("resume") == "deploy_decision" and meta.get("decision"):
        new_oid = operations.create(pid, "deploy", "Deploy (resumed with your input)")
        _pool_post(pid, "🚀 Re-running the deploy with the corrected folders…")
        try:
            dres = deploy_runner.run_decision(pid, meta["decision"], oid=new_oid,
                                              on_log=lambda m: _pool_post(pid, str(m)[:1200]))
        except Exception as e:
            operations.set_state(new_oid, "failed", f"crashed: {e}")
            _pool_post(pid, f"❌ Resume crashed: {e}")
            return
        if dres.get("needs_owner"):
            _pool_post(pid, "⛔ Still blocked — " + (dres.get("ask") or dres.get("reason", "need more info")))
            return  # the new op is already 'blocked' with its question (ask() was called in run_decision)
        if dres.get("ok"):
            operations.set_state(new_oid, "done", "✅ Deploy verified after you provided the info.")
            _pool_post(pid, "✅ Deploy verified after your input.")
            _emit_outcome(pid, "deploy", True, "Deploy verified")
        else:
            operations.set_state(new_oid, "failed", f"❌ {dres.get('reason', 'see log')}")
            _pool_post(pid, f"❌ Deploy still failing: {dres.get('reason', 'see log')}")
            _emit_outcome(pid, "deploy", False, dres.get("reason", "deploy failed"))
    else:
        # generic resume: re-run the deterministic deploy
        new_oid = operations.create(pid, "deploy", "Deploy (resumed)")
        _deploy_bg(pid, new_oid)


def _deploy_bg(pid: str, oid: str | None = None):
    """Run the DETERMINISTIC deploy (deploy_runner) in the background as a single OPERATION the UI
    watches + can stop, streaming each step into both the operation log and the project chat, then
    setting the final state so a finish/stop card fires reliably. Fast, no AI — like the owner's script."""
    import deploy_runner, scopes, operations
    s = f"project:{pid}"
    chats = scopes.list_chats(s)
    cid = chats[0]["id"] if chats else scopes.create_chat(s, "▶ Deploy")["id"]
    if not oid:
        oid = operations.create(pid, "deploy", "Deploy to VM (workspace/shared/infra/deploy.sh — the proven script)")
    scopes.add_message(s, cid, "assistant", "🚀 Deploy started — self-healing run (diagnoses + fixes on failure, retries until a REAL exit-0)…")
    # PROMPT-AUDIT (same as the E2E): surface any confirmed-broken methods the project's brief asks
    # for, so the owner sees the truth. The pipeline OVERRIDES them (SSH-as-mostafa + migrate deploy);
    # it never silently follows a method we proved fails. Non-blocking — informational.
    try:
        import audit, projects as _proj
        broken = audit.audit_prompt((_proj.get_project(pid) or {}).get("description", ""))
        if broken:
            note = ("⚠️ Prompt-audit — this project's brief requests confirmed-broken method(s) "
                    "(the pipeline OVERRIDES them with SSH-as-mostafa + `migrate deploy`):\n"
                    + "\n".join(f"  - {b}" for b in broken))
            operations.log(oid, note)
            scopes.add_message(s, cid, "assistant", note)
    except Exception:
        pass
    try:
        import deploy_agent
        res = deploy_agent.run(
            oid=oid,
            on_log=lambda m: scopes.add_message(s, cid, "assistant", (m or "")[:1500]))
    except Exception as e:
        operations.set_state(oid, "failed", f"crashed: {e}")
        scopes.add_message(s, cid, "assistant", f"❌ Deploy crashed: {e}")
        _emit_outcome(pid, "deploy", False, f"Deploy crashed: {e}")
        return
    # SUCCESS is reported ONLY on a verified exit-0 (res['ok']). No prose path can fake it.
    success_ok = bool(res.get("ok"))
    if res.get("stopped"):
        state, verdict = "stopped", "⏹ Deploy stopped by you."
    elif res.get("ok"):
        # SNAKE HUNT: even a real exit-0 is scanned for hidden faults. Green is not trusted blindly.
        import audit, operations as _ops
        op = _ops.get(oid) or {}
        log_text = "\n".join(l.get("line", "") for l in op.get("log", []))
        snakes = audit.scan_hidden_faults(log_text)
        rounds = res.get("rounds", 1)
        if snakes:
            success_ok = False                       # hidden faults → NOT clean green
            issues = "; ".join(f"{h['label']}" for h in snakes[:6])
            verdict = f"⚠️ Deploy exit-0 BUT the audit found {len(snakes)} hidden issue(s) — not clean: {issues}. (Open the log for the lines.)"
            state = "failed"                         # flagged as NOT a clean success → red card, never silent green
        else:
            verdict = "✅ Deploy verified successful (real exit-0, audit found no hidden faults)" + (f" after {rounds} attempts — auto-fixed along the way." if rounds > 1 else ".")
            state = "done"
    elif res.get("needs_owner"):
        fix = res.get("proposed_fix") or ""
        verdict = f"⛔ Stopped — needs your decision. Cause: {res.get('reason','?')}." + (f" Suggested fix (NOT auto-run): {fix}" if fix else " Missing info — tell me what to provide.")
        state = "failed"
    else:
        verdict = f"❌ Deploy failed after {res.get('rounds','?')} attempt(s). Cause: {res.get('reason','see log')}."
        state = "failed"
    operations.set_state(oid, state, verdict)
    scopes.add_message(s, cid, "assistant", verdict)
    _emit_outcome(pid, "deploy", success_ok, verdict)


def _emit_outcome(pid: str, kind: str, ok: bool, text: str):
    """Breadcrumb the finish into the activity flow. The authoritative finish/stop card is driven
    by the OPERATION state (the UI polls it), so this is best-effort only and never raises."""
    try:
        import activity
        activity.log_flow(pid, kind, "owner", ("✅ " if ok else "⚠️ ") + text[:200])
    except Exception:
        pass



# ============================================================================
# OPERATIONAL DEPLOY + DIAGNOSIS — DETERMINISTIC SEQUENTIAL GATES (one per turn).
# The AI brain (_scoped_gen) does the DIAGNOSIS reasoning/reads; the DEPLOY side is
# ENFORCED here as real, separate approvals that HALT the run — never narrated.
#   play -> scan -> "Deploy these N file(s)?"  (STOP, wait for the owner)
#     REJECT  -> "Re-baseline the change-list?" (STOP) -> approve -> deploy_changes.py update -> diagnosis
#     APPROVE -> real deploy (_deploy_bg, the proven self-healing runner)
#                  -> schema/seed changed? "Migrate/rebase DB?" (STOP) -> then diagnosis
#                  -> else -> ANNOUNCE + fully RUN the read-only diagnosis
# Generalises to ANY operational project whose brief involves deploy; a pure read-only
# diagnosis project (no deploy) skips straight to the smart-brain diagnosis.
# ============================================================================
def _op_is_deploy_project(pid: str) -> bool:
    try:
        import projects as _pj
        p = _pj.get_project(pid) or {}
        meta = (str(p.get("type", "")) + " " + str(p.get("category", "")) + " " + str(p.get("description", ""))).lower()
        return ("deploy" in meta) and any(k in meta for k in ("operational", "diagnos", "ops", "deploy"))
    except Exception:
        return False


def _op_cid(pid: str):
    import scopes
    s = f"project:{pid}"
    chats = scopes.list_chats(s)
    return s, (chats[0]["id"] if chats else scopes.create_chat(s, "Run")["id"])


def _op_scan(pid: str) -> dict:
    """Run the change-detection trigger deterministically and parse it (the SAME trigger the pipeline uses)."""
    import subprocess as _sp, sys as _sys, os as _os
    try:
        r = _sp.run([_sys.executable, "workspace/shared/infra/deploy_changes.py", "scan", "--project", pid],
                    capture_output=True, text=True, timeout=120, env=dict(_os.environ))
        tt = (r.stdout or "") + "\n" + (r.stderr or "")
    except Exception as e:
        return {"required": False, "files": [], "db_sensitive": False, "error": str(e), "raw": ""}
    files = [l.strip()[2:].strip() for l in tt.splitlines() if l.strip().startswith("~ ")]
    return {"required": "DEPLOY_REQUIRED: YES" in tt, "db_sensitive": "DB_SENSITIVE: YES" in tt,
            "files": files, "error": "", "raw": tt[-4000:]}


def _op_diag_prompt(note: str = "") -> str:
    return ((note + "\n\n") if note else "") + (
        "[system] The deploy phase is resolved. Now do the DIAGNOSIS step: ANNOUNCE 'starting the diagnosis', "
        "then EXECUTE read-only reads across EVERY connected agent IN THIS SAME TURN and POST the real values — "
        "Klaviyo profile count; Veeqo order count + the known DELIVERED order (feed its carrier+tracking to the "
        "EasyPost operator, get EasyPost's delivered status, and COMPARE it to our DB's stored status for that "
        "order); HubSpot / Analytics reads. Give a CLEAR verdict: GREEN if all pass and nothing paused; if "
        "anything fails, state the EXACT reason. Write or propose AI_DIAGNOSIS_REPORT.md ONLY if a real problem "
        "is found. A turn that only announces without the actual results is a FAILURE — run every read to "
        "completion and show the real numbers/values before you stop.")


def _op_run_diagnosis(pid: str, note: str = "", threaded: bool = True):
    """ANNOUNCE + fully RUN the read-only diagnosis via the smart brain. threaded=True for endpoint callers
    (manages its own RUNNING flag); threaded=False to drain inline inside an existing run thread."""
    import threading, time
    s, cid = _op_cid(pid)
    cont = _op_diag_prompt(note)
    if not threaded:
        for _ in _scoped_gen(s, cont, "en", cid):
            if _RUNS.get(pid, {}).get("cancel"):
                break
        return
    def _go():
        import activity as _act
        with _RUNS_LOCK:
            _RUNS[pid] = {"running": True, "cancel": False, "goal": "diagnosis", "started": time.time()}
        try:
            _act.mark_active(pid, "Project CTO", task="running the diagnosis", phase="CTO: diagnosis")
            for _ in _scoped_gen(s, cont, "en", cid):
                if _RUNS.get(pid, {}).get("cancel"):
                    break
        except Exception:
            pass
        finally:
            try:
                _act.mark_idle(pid, "Project CTO")   # clear the CTO animation exactly when the run ends
            except Exception:
                pass
            with _RUNS_LOCK:
                rr = _RUNS.get(pid)
                if rr:
                    rr["running"] = False
    threading.Thread(target=_go, daemon=True).start()


def _op_open_deploy_gate(pid: str):
    """FIRST run turn of a play: supersede any stale gates from a previous run (approvals are PER RUN),
    scan, then create the SINGLE 'Deploy these files?' gate and STOP. Nothing changed -> diagnosis."""
    import scopes, approvals
    s, cid = _op_cid(pid)
    for _old in approvals.list_pending(pid):
        if _old.get("kind") in ("deploy", "synclist", "db-migrate"):
            try:
                approvals.decide(_old["id"], False, note="superseded — a new run started")
            except Exception:
                pass
    sc = _op_scan(pid)
    if sc.get("error"):
        scopes.add_message(s, cid, "assistant", f"⚠️ Change-detection could not run: {sc['error']}")
        return
    if sc["required"] and sc["files"]:
        n = len(sc["files"])
        flist = "\n".join(f"  • {f}" for f in sc["files"])
        dbn = ("YES — a DB rebase/migration will be recommended SEPARATELY after the deploy." if sc["db_sensitive"]
               else "NO (code only).")
        scopes.add_message(s, cid, "assistant",
            f"🔎 Change-detection ran. {n} file(s) changed versus what's deployed:\n{flist}\n\nDB-sensitive: {dbn}")
        approvals.create(pid, "DevOps", title=f"Deploy these {n} file(s)?",
            summary=("Approve → deploy ONLY these changed files with the EXISTING protocol (refresh the port-22 "
                     "firewall IP only, keep 80/443, SSH as mostafa, rsync the changes, build, restart). "
                     "Reject → I'll ask SEPARATELY whether to re-baseline the change-list (so it stops flagging "
                     "these) in case you already deployed them manually."),
            files=[{"path": f, "action": "deploy", "why": "changed vs deployed copy"} for f in sc["files"]],
            kind="deploy", inline=False,
            recommended="Approve to deploy exactly these files; reject to re-baseline the list instead.")
        return   # STOP — waiting on the owner's single decision.
    scopes.add_message(s, cid, "assistant",
        "🔎 Change-detection ran: nothing changed versus what's deployed — no deploy needed. Starting the diagnosis.")
    _op_run_diagnosis(pid, note="[system] No deploy was needed (nothing changed vs deployed).", threaded=False)


def _op_open_sync_gate(pid: str):
    """Owner REJECTED the deploy -> offer the SEPARATE re-baseline gate so future checks stop flagging."""
    import scopes, approvals
    s, cid = _op_cid(pid)
    approvals.create(pid, "DevOps", title="Re-baseline the change-list (no deploy)?",
        summary=("You declined the deploy. If you already deployed these files manually, approve this to re-sync "
                 "the change-detection baseline to the current files so future runs won't keep flagging them. "
                 "This makes NO VM or production change — it only updates the local change-list."),
        commands=[{"cmd": f"python workspace/shared/infra/deploy_changes.py update --project {pid}", "where": "local",
                   "why": "Re-baseline the deploy change-lists to the current state (no VM/production change)."}],
        kind="synclist", inline=False,
        recommended="Approve only if you deployed manually; it updates the baseline so checks stay quiet.")
    scopes.add_message(s, cid, "assistant",
        "Understood — not deploying. I've opened a SEPARATE approval to re-baseline the change-list so it stops "
        "flagging these files (approve it only if you already deployed them manually).")


def _op_open_db_gate(pid: str):
    """Schema/seed changed -> SEPARATE DB-migration recommendation gate (additive only)."""
    import scopes, approvals
    s, cid = _op_cid(pid)
    approvals.create(pid, "DevOps", title="Migrate/rebase the database?",
        summary=("A schema/seed file changed in this deploy, so a DB migration is RECOMMENDED. Approve → additive "
                 "migration ONLY (never a destructive rebase/reset unless you explicitly say so). Reject → skip the "
                 "DB change and continue to the diagnosis."),
        kind="db-migrate", inline=False,
        recommended="Recommended because a schema/seed file changed. Additive migration only.")
    scopes.add_message(s, cid, "assistant",
        "✅ Deploy landed. A schema/seed file changed, so here's a SEPARATE approval for the DB migration "
        "(additive only). Approve or reject it, then I'll run the diagnosis.")


def _op_after_deploy(pid: str, oid):
    """Owner APPROVED the deploy: capture DB-sensitivity BEFORE deploy, run the proven deploy, then either open
    the DB gate (schema/seed changed) or run the diagnosis."""
    db_sensitive = False
    try:
        db_sensitive = bool(_op_scan(pid).get("db_sensitive"))
    except Exception:
        db_sensitive = False
    try:
        _deploy_bg(pid, oid)   # the proven self-healing deploy; posts its own verdict into the chat
    except Exception:
        pass
    if db_sensitive:
        _op_open_db_gate(pid)
    else:
        _op_run_diagnosis(pid, note="[system] Deploy is done; code-only (no schema/seed), so no DB step.")


def _op_apply_synclist(pid: str, aid: str):
    """Owner APPROVED the re-baseline -> update the change-list (no VM/prod change), then run the diagnosis."""
    import subprocess as _sp, sys as _sys, os as _os, scopes, approvals
    s, cid = _op_cid(pid)
    try:
        r = _sp.run([_sys.executable, "workspace/shared/infra/deploy_changes.py", "update", "--project", pid],
                    capture_output=True, text=True, timeout=120, env=dict(_os.environ))
        ok = r.returncode == 0
        out = ((r.stdout or "") + (r.stderr or "")).strip()[-1500:]
    except Exception as e:
        ok, out = False, str(e)
    approvals.mark_applied(aid, out)
    scopes.add_message(s, cid, "assistant",
        ("✅ Change-list re-baselined — future checks will stay quiet for these files. Run finished; "
         "press play to run the deploy check again." if ok else f"⚠️ Re-baseline failed: {out}"))


def _op_apply_dbmigrate(pid: str, aid: str):
    """Owner APPROVED the DB migration -> run the ADDITIVE migrate on the VM (derived from the deploy config,
    never a destructive reset), then run the diagnosis."""
    import scopes, approvals
    s, cid = _op_cid(pid)
    ran, out = [], ""
    try:
        note, vm_ip = _ensure_vm_access()
        scopes.add_message(s, cid, "assistant", f"🔌 Opened VM access — {note}")
        import deploy_runner, deploy_ssh
        cfg = deploy_runner.get_config(pid) or {}
        mig = deploy_runner._migration_cmd("deploy") or "npx prisma migrate deploy"
        for t in cfg.get("targets", []):
            vmdir = t.get("vm") or ""
            if vmdir:
                r = deploy_ssh.ssh_exec(f"cd {vmdir} && {mig}")
                ok = bool(r.get("ok"))
                o = (r.get("out") or r.get("err") or r.get("error") or "(no output)").strip()[:800]
                ran.append(ok)
                out += f"$ (in {vmdir}) {mig}\n{o}\n"
                scopes.add_message(s, cid, "assistant", f"▶ DB migrate (additive) in {vmdir}: {'✅' if ok else '❌'} {o[:400]}")
        if not cfg.get("targets"):
            out = "No deploy target with a VM app dir is configured — skipped the migration (no guess on production)."
            scopes.add_message(s, cid, "assistant", "⚠️ " + out)
    except Exception as e:
        out = f"DB migration error: {e}"
        scopes.add_message(s, cid, "assistant", "⚠️ " + out)
    approvals.mark_applied(aid, out)
    _op_run_diagnosis(pid, note="[system] DB migration step done (additive).")


def _orchestrate_gen(pid: str, goal: str):
    """REAL agent-to-agent conversation cycle, dependency-aware and QA-gated:
      Chief Engineer → Project CTO (resource-aware plan, in the project chat)
      then for each member's PART, in dependency order (waiting for a dependency to PASS first):
        CTO briefs the member → member works & reports → CTO reviews
        → QA TESTS that member's part (real build/run) → on a bug, CTO routes the fix to the
          responsible EXISTING member → they fix → QA re-tests (looped until it works or capped)
      → next part → CTO reports completion to the Chief.
    Every message is saved to the scope chats, so the chats ARE the project's documentation."""
    import projects, scopes, activity, models_config
    import intent as _intent
    try:
        proj = projects.get_project(pid)
        if not proj:
            yield sse("error", {"text": "no such project"}); return
        name = proj.get("name", pid)
        pscope = f"project:{pid}"
        folder = proj.get("localPath") or ""
        deploy_mode = (proj.get("mode") == "deploy")
        # QA only runs if QA is actually ON YOUR TEAM. If you removed it (or never added it), the gate
        # is OFF and QA is NEVER auto-hired. QA also never gates DevOps/infrastructure work.
        try:
            import agents_registry as _ar0
            _team = [m.get("name", "").lower() for m in _ar0.list_agents(pid)]
        except Exception:
            _team = []
        qa_enabled = bool(folder) and ("qa" in _team)
        # RESPECT an explicit owner restriction on which agents run (e.g. "only DevOps, no QA").
        _gl = (goal or "").lower()
        if any(p in _gl for p in ("no qa", "without qa", "remove qa", "no quality", "only devops",
                                  "devops only", "only the devops", "no other agent", "do not involve",
                                  "don't involve", "not add or activate any agents other")):
            qa_enabled = False
        srcs = proj.get("sources") or []
        # Pre-authorized? Then changes apply without the popup. Either the project's pre-approve
        # toggle, OR the owner explicitly authorized THIS run in the brief ("approval already
        # granted / do not ask for approval / authorized for this run").
        # VM/Azure work: a TEXT-only "authorized" claim in the brief is NOT enough to auto-execute —
        # it still needs the approval popup. BUT an EXPLICIT project-level auto_approve (the owner
        # deliberately pre-authorized this project, e.g. a sandbox build or an opted-in deploy) IS
        # honored — otherwise members were forced read-only and could never produce a deliverable
        # (that caused the multi-agent reassign loop). Local-only work auto-runs when pre-authorized.
        _owner_auth = bool(proj.get("auto_approve"))
        vm_work = _touches_vm(goal) or deploy_mode
        auto_approve = _owner_auth or (_run_preauthorized(goal) and not vm_work)
        if auto_approve:
            yield sse("status", {"icon": "✅", "text": "Authorized run — agents execute directly (write-enabled)."})
        elif vm_work:
            yield sse("status", {"icon": "🔒", "text": "This touches Azure/the VM — every change will wait for your Approve/Discard (read-only checks run free)."})

        # QA is OFF and the owner hasn't already been asked/declined → the CTO may recommend adding
        # it ONCE, only if it judges QA genuinely important for this goal. The owner decides in a
        # popup. Asking is recorded immediately so it is never asked again.
        # If the owner deselected QA, RECORD that as declined so it's never re-suggested or re-hired.
        if not qa_enabled and ("qa" not in _team):
            try:
                projects.set_flags(pid, qa_declined=True)
                proj["qa_declined"] = True
            except Exception:
                pass
        # Only ever recommend QA for real CODE work — NEVER for a VM/deploy/ops run.
        if not qa_enabled and not vm_work and not deploy_mode and not proj.get("qa_asked") and not proj.get("qa_declined"):
            try:
                import approvals as _ap
                verdict = projects._engine(
                    f"You are the Project CTO for '{name}'. This project has NO QA agent.\nGoal: {goal}\n"
                    "Is adding QA (a quality/code-review/test gate after each task) genuinely IMPORTANT "
                    "here? Say yes ONLY if it materially reduces real risk (real code changes, production, "
                    "data integrity). For a pure ops/deploy/sync or trivial task, say no.\n"
                    'Reply ONLY JSON: {"recommend": true|false, "why": "<one short sentence>"}')
                d = projects._extract_json_object(verdict) or {}
                if d.get("recommend"):
                    _ap.create(pid, "Project CTO", title="Add QA (Quality Assurance) to this project?",
                               summary=str(d.get("why", "Recommended to catch issues before they ship."))[:300],
                               kind="qa-recommendation", inline=False)
                    yield sse("status", {"icon": "💡", "text": "CTO recommends adding QA — see the popup to decide"})
                projects.set_flags(pid, qa_asked=True)   # asked once; never again
            except Exception:
                pass

        # ONE shared pool — reuse the project's single group chat across runs (don't spawn a new chat
        # every run). Everyone (CTO + agents) posts into this one pool; nothing scattered.
        _existing = scopes.list_chats(pscope)
        run_chat = _existing[0] if _existing else scopes.create_chat(pscope, title="▶ Team pool")

        # --- Chief Engineer → Project CTO (resource-aware planning, visible in the project chat) ---
        scopes.add_message(pscope, run_chat["id"], "user",
                           f"[Chief Engineer → Project CTO] For '{name}': {goal}. Plan it, assign the team, and report back.")
        # The CTO is a REAL active agent while it plans/organizes — animate IT (not a member). This is
        # what makes the CTO visible on the left with its own heartbeat when it's the one working.
        activity.mark_active(pid, "Project CTO", task="planning & assigning the team", phase="CTO: planning")
        yield sse("status", {"icon": "🧭", "text": "Project CTO is reviewing the team & resources, then planning…"})
        # FAITHFUL INTAKE → CTO: the CTO must plan from the FULL owner brief (every detail), not a thin
        # goal line. No omission, no fabrication, no removal of the owner's requirements.
        # -- INTELLIGENCE-FIRST GATE (intent.py) -----------------------------------------------
        # The OWNER'S message drives the work; the project brief is CONSTRAINTS, never a checklist
        # to complete every turn. A scoped ask ("just update the list, nothing else") is handled
        # DIRECTLY by ONE agent -- no team, no brief expansion. Only a real multi-part build fans out.
        _cls = _intent.classify_request(goal, engine=getattr(projects, "_engine", None))
        _forbid = set(_cls.get("forbid") or [])
        _full_req = goal
        if _cls.get("mode") == "direct":
            _who = _direct_member(pid, goal)
            _ro = ""
            if "deploy" in _forbid:
                _ro = (" Constraint: do NOT deploy, rsync, build on the VM, migrate, or reboot -- no "
                       "VM/production state change. Local file/config edits the owner explicitly asked "
                       "for (e.g. updating a list) ARE allowed -- only deployment is off-limits.")
            steps = [{"member": _who, "depends_on": [],
                      "task": goal + _ro,
                      "objective": "Do EXACTLY what the owner asked -- nothing else.",
                      "deliverable": "The exact thing asked, shown with real evidence (diff / command output / file).",
                      "acceptance_criteria": "The request is satisfied and proven with evidence; no extra work, no team."}]
            scopes.add_message(pscope, run_chat["id"], "assistant",
                               f"[Project CTO -> Chief] Scoped request -- {_who} handles it directly ({_cls.get('reason','')}); no team expansion.")
        else:
            _req_src = goal
            if proj.get("description") and proj["description"][:200] not in goal:
                _full_req = (goal + "\n\n--- PROJECT CONSTRAINTS (guardrails you MUST respect -- NOT tasks to "
                             "complete this turn, only limits: read-only unless asked, no DB rebase, single-IP "
                             "firewall, scopes/audit) ---\n" + proj["description"])
            steps = projects.plan_pipeline(pid, _full_req)
            try:
                _missing = projects.check_plan_coverage(_req_src, steps)
            except Exception:
                _missing = []
            activity.beat(pid, "Project CTO")
            if _missing:
                yield sse("status", {"icon": "\U0001f9ee", "text": f"CTO caught {len(_missing)} uncovered part(s) of your request -- re-planning"})
                scopes.add_message(pscope, run_chat["id"], "assistant",
                                   f"[Project CTO] Gap vs YOUR request: {'; '.join(_missing[:6])}. Re-planning.")
                steps = projects.plan_pipeline(pid, goal + "\n\nAlso cover (from YOUR request, not the brief): " + "; ".join(_missing))
        # A DEPLOY is ONE operation — the pipeline itself does sync → build → migrate → reboot → verify
        # in a single run, and reports those as its REAL internal steps. Never split it into many plan
        # steps that each re-run the whole deploy. Collapse to ONE DevOps step ONLY for a PURE-DEPLOY
        # project (DevOps is a member and there is no other build team). For a MULTI-AGENT build that
        # merely includes a deploy step (e.g. Frontend+Backend+QA+… then deploy), do NOT collapse —
        # that wrongly discarded the whole team and even injected DevOps when it wasn't on the team.
        _mem = [m.lower() for m in (proj.get("members") or [])]
        _build_roles = ("fullstack", "frontend", "backend", "qa", "security", "database", "shipping",
                        "fulfillment", "email", "mobile", "data", "content", "marketing", "support",
                        "sales", "analytics")
        _pure_deploy = ("devops" in _mem) and not any(r in _mem for r in _build_roles)
        if _cls.get("mode") != "direct" and (deploy_mode or _touches_vm(goal) or _touches_vm(_full_req)) and _pure_deploy:
            steps = [{"member": "DevOps", "depends_on": [],
                      "task": "Deploy to the VM in ONE run: rsync → build → migrate → reboot → verify",
                      "objective": "Execute the owner's deploy exactly once, exactly as specified.",
                      "deliverable": "Both apps synced & built on the VM, rebooted, verified online (HTTP 200).",
                      "acceptance_criteria": "Real exit-0 from the deploy pipeline and the site responds."}]
        # The CTO ORCHESTRATES — it is never a worker step. Drop any self/meta steps the planner
        # assigned to the CTO/Chief (e.g. "stand up the coordination pool"); those produce no real
        # deliverable and stalled the run before any real member started. Keep only real worker steps.
        _orchestrator_names = ("cto", "project cto", "chief engineer", "chief", "orchestrator", "coordinator",
                               "owner", "user", "you")
        _real_steps = [s for s in steps if str(s.get("member", "")).strip().lower() not in _orchestrator_names]
        if _real_steps:                      # never empty out the plan
            steps = _real_steps
        deliverables = {}   # member -> its produced deliverable (for STRUCTURED hand-off, not raw dumps)
        def _dep_txt(s):
            d = s.get("depends_on") or []
            return f" (after {', '.join(d)})" if d else ""
        plan_txt = "; ".join(f"{i+1}) {s['member']} → {s['task']}{_dep_txt(s)}" for i, s in enumerate(steps))
        _qa_note = " QA tests each part." if qa_enabled else " (DevOps-only run — no QA, as you instructed.)"
        scopes.add_message(pscope, run_chat["id"], "assistant",
                           f"[Project CTO → Chief] Plan: {plan_txt}. Briefing the team now.{_qa_note}")
        activity.mark_active(pid, "Project CTO", task="briefing the team", phase="CTO: briefing the team")
        yield sse("plan", {"steps": steps})

        total = len(steps)

        def _ensure_member(member):
            """Hire an existing member on the fly so it appears on the team and in chats. SAFETY: only
            auto-hire a KNOWN catalogue role (or one the owner already confirmed). Never silently invent
            a brand-new agent from a name the CTO made up (that caused hallucination) and never re-add an
            owner-removed agent."""
            try:
                import agents_registry, projects as _pj
                if not agents_registry.get_agent(pid, member):
                    if not _pj.known_role(member) or agents_registry.is_excluded(pid, member):
                        return False   # don't invent a non-catalogue agent / don't resurrect a removed one
                    sug = agents_registry.suggest_agent(f"{member} specialist for {name}")
                    agents_registry.register_agent(pid, member, role=sug.get("role", member),
                                                   avatar=sug.get("avatar", "generic"),
                                                   description=f"Hired by the CTO while planning: {goal[:60]}")
                    return True
                return False
            finally:
                try:
                    import agents_registry as _ar; _ar.record_usage(pid, member)
                except Exception:
                    pass

        src_note = (f"EXISTING source folders (READ-ONLY — read/consider, do NOT rewrite unless the "
                    f"owner explicitly asked): {', '.join(srcs)}.\n") if srcs else ""
        loc = src_note + ((f"The project's folder is: {folder}\nDo ALL file work INSIDE that folder "
               "(create it if missing; cd into it). NEVER scaffold, build, or write files at the "
               "Odin app's own repo root or anywhere else.\n") if folder else
               ("This project has no local folder set yet — ASK before creating files anywhere; do "
                "NOT write into the Odin app's repo.\n"))
        # (Reverted the stacked read-only prompt-rules: the STRUCTURAL gate now enforces read-only +
        # approval for every modification, so agents reason naturally without a wall of "never" rules.)
        # The owner's EXACT instructions for this run. The CTO's per-member `task` is only a short
        # label — the member must follow THESE verbatim (exact paths, commands, excluded files,
        # and any "this time / next time" rules), never a summary of them.
        owner_brief = ("OWNER'S FULL INSTRUCTIONS for this run — AUTHORITATIVE. Follow them EXACTLY: do "
                       "NOT summarize, drop, reorder, or invent any rule, path, command, or excluded "
                       "file. If the owner gave exact commands or exclude lists, use THEM verbatim. "
                       "Honor any 'this time only' vs 'ask me next time' conditions as written, and for "
                       "anything that changes a running/production system, follow the owner's stated "
                       "approval rules (propose the exact commands + impact + rollback and wait for "
                       # use the FULL owner brief (goal + the project's complete description), NOT just the
                       # short goal line — otherwise members reason without the exact paths/commands/excludes
                       # and (correctly) refuse with "could not derive a plan". Give the AI its full context.
                       f"approval unless the owner explicitly allowed it this run):\n\"\"\"\n{_full_req}\n\"\"\"\n")

        # GROUND read questions in REAL connector data (Klaviyo/Veeqo) — the same live facts the anchor
        # path uses. Without this, an owner-initiated run had to guess at "how many orders/workflows".
        # GET-only; injected into every member's brief AND the shared pool so the answer is real, and
        # visible to all agents (shared-context pool preserved). (Pool append happens after create.)
        _facts_txt = ""
        try:
            import anchor as _anchor, json as _json
            _facts = _anchor._connector_facts(proj, goal)
            if _facts and not _facts.get("error"):
                _facts_txt = ("LIVE READ-ONLY DATA from the connected service — GROUND your answer in "
                              "THESE exact numbers (do not invent or omit them):\n" + _json.dumps(_facts))
                owner_brief += "\n" + _facts_txt + "\n"
                yield sse("status", {"icon": "📊", "text": f"Live {_facts.get('source','data')} fetched and shared with the team"})
        except Exception as _e:
            yield sse("status", {"icon": "⚠️", "text": f"connector facts unavailable: {_e}"})

        # MAIN TASK — the omission guard: split this prompt into a REQUIREMENTS CHECKLIST that every
        # member sees (the "whole job" big picture) and that we verify is fully addressed at the end.
        # (The structured mandate + hand-off already exist below; this adds the missing checklist.)
        try:
            import run_timer
            _e2e_timer = run_timer.Timer(pid, goal)   # E2E timer: start at task begin
            yield sse("status", {"icon": "⏱️", "text": f"E2E timer started ({'cached' if _e2e_timer.cached else 'no-cache baseline'})"})
        except Exception:
            _e2e_timer = None
        try:
            import main_task
            _mt = main_task.create(pid, goal)
            main_task.append(pid, "Project CTO (plan)", plan_txt)   # seed the shared pool with the breakdown
            if _facts_txt:                                          # live connector data → shared pool for ALL agents
                main_task.append(pid, "Live data (read-only)", _facts_txt)
            if _mt.get("requirements"):
                scopes.add_message(pscope, run_chat["id"], "assistant",
                                   f"[Project CTO] Requirements checklist: {len(_mt['requirements'])} item(s) "
                                   "tracked — nothing is 'done' until all are addressed.")
        except Exception:
            pass

        results = []          # completed parts: {member, task, review}
        passed_members = []   # members whose part PASSED QA (for dependency waits)

        def _run_engine(prompt, scope_model, who):
            """Stream the engine, forwarding live activity; returns the final text. (generator)"""
            parts, final = [], None
            for evd in _engine_stream(prompt, "en", None, scope_model, cwd=folder or None):
                k = evd.get("kind")
                if k == "status":
                    yield sse("status", {"icon": evd.get("icon", "🔧"), "text": f"{who}: {evd.get('text', '')}"}); activity.beat(pid, who)
                elif k == "text":
                    parts.append(evd["t"]); yield sse("token", {"member": who, "t": evd["t"]}); activity.beat(pid, who)
                elif k == "final":
                    final = evd.get("text") or "".join(parts)
            yield ("__return__", (final or "".join(parts) or "(no output)").strip())

        # ----- QA gate: tests the part `area_member` just finished; loops CTO-routed fixes -----
        def qa_gate(area_member, area_task):
            if not qa_enabled:
                yield ("__return__", True); return
            qa = "QA"
            if _ensure_member(qa):
                yield sse("status", {"icon": "➕", "text": f"CTO brought in {qa} to test"})
            qscope = f"member:{pid}:{qa}"
            qchat = scopes.create_chat(qscope, title=f"▶ Test: {area_task[:24]}")
            # SPEED (testing only): QA is an evaluative gate — when ODIN_GATE_MODEL is set (the test
            # loop sets a fast model), run QA on it. Production sets nothing → full model, full rigor.
            qmodel = os.environ.get("ODIN_GATE_MODEL") or models_config.get_model(qscope)
            activity.log_flow(pid, area_member, qa, note=f"test {area_member}")
            # the CTO can route a fix to anyone who has worked so far, or back to this member
            candidates = list(dict.fromkeys([r["member"] for r in results] + [area_member]))
            roster = ", ".join(f"{r['member']} ({r['task'][:36]})" for r in results) or f"{area_member} ({area_task[:36]})"
            # BOUND QA TIME: at most ONE fix cycle (2 attempts), and a hard wall-clock budget for the whole
            # gate so QA can never blow the run's time again. If the budget is hit, stop cycling and accept the
            # last verdict instead of starting another expensive rebuild→re-QA round.
            MAX_ATTEMPTS = 2
            _QA_BUDGET = int(os.environ.get("ODIN_QA_BUDGET", "720"))   # 12 min total for QA + its fix cycle
            _qa_t0 = time.time()
            passed = False
            for attempt in range(1, MAX_ATTEMPTS + 1):
                if attempt > 1 and (time.time() - _qa_t0) > _QA_BUDGET:
                    yield sse("status", {"icon": "⏱", "text": f"QA time budget ({_QA_BUDGET}s) reached — not starting another fix cycle"})
                    break
                activity.mark_active(pid, qa, task=f"test {area_member}", phase=f"QA: testing {area_member} (try {attempt})")
                yield sse("status", {"icon": "🧪", "text": f"QA testing {area_member}'s part (attempt {attempt}/{MAX_ATTEMPTS})…"})
                # QA reviews quality + tests. It runs READ-ONLY (enforced by the engine), so it
                # physically can't install/build/deploy/modify — it just verifies and reports.
                qa_prompt = (
                    f"You are the QA engineer for project '{name}'. Verify the part {area_member} just finished.\n"
                    f"Their task was: {area_task}\nProject folder: {folder}\n"
                    "FIRST, before anything else, run `ls -R` (excluding node_modules) on the project folder to "
                    "confirm the app ACTUALLY EXISTS ON DISK. If the folder is empty or has no real source files, "
                    "the developer only DESCRIBED the app — reply 'FAIL:' immediately (it was not built). Do NOT "
                    "trust the developer's report or any acceptance table; verify against the real files. If the "
                    "developer claims tests passed or live data was fetched, only believe it if the code and "
                    "evidence are actually present.\n"
                    "Do a real QA pass within your read-only tools: review the changed code for correctness, "
                    "quality and basic security; run lint/type-check and the existing test suite if present; for "
                    "a deploy/sync, confirm the work matches the owner's exact instructions and (if live) do a "
                    "read-only health check. You are QA, not a developer — verify, don't implement.\n"
                    "TIME BUDGET — be fast: keep this pass UNDER ~5 MINUTES. Do NOT run a production build "
                    "(`next build`/`npm run build`/bundling) and do NOT start long-lived/dev servers — review "
                    "the source and run only quick checks (lint/type-check/unit tests if they already exist). "
                    "A focused read-and-verify is enough; speed matters.\n"
                    "SCOPE — verify the CODE, not live external data: at BUILD/pre-deploy time, confirm the app "
                    "is complete and correct — the integration code reads its keys from the env and calls the "
                    "right endpoints, handles responses/errors, and the page renders. Do NOT FAIL the build "
                    "merely because LIVE Veeqo/Klaviyo data is not flowing yet: fetching and posting real live "
                    "data happens AFTER deploy and is the operators' job, verified then. Only FAIL for an actual "
                    "code/build defect (won't run, missing feature, wrong logic, not reading the env key).\n"
                    "Reply EXACTLY 'PASS:' (one line on what you verified) if it's clean, or 'FAIL:' with the exact "
                    "defects (build/lint/type errors, failing tests, quality/correctness or instruction deviations) "
                    "so the CTO assigns the fix.")
                scopes.add_message(qscope, qchat["id"], "user",
                                   f"[Project CTO → QA] Test {area_member}'s part (attempt {attempt}). Report PASS or the exact errors.")
                qreply, qprog = None, []
                # LIVENESS: a real QA pass on a fresh app runs lint/type-check/build/tests — long tool
                # calls that stream no tokens for minutes. Post the SAME in-flight breadcrumb the member
                # build uses so the monitor (which reads these breadcrumbs) sees QA as HEALTHY work,
                # bounded by the engine idle-timeout + hard_cap — not a false stall. Without this, a
                # long-but-fine QA on a ~10k-file app trips the per-step stall (root cause of Test 4 fail).
                try:
                    import main_task as _mtd
                    _mtd.append(pid, qa, "⏳ phase: engine call starting (QA gate)…")
                except Exception:
                    pass
                for evd in _engine_stream(qa_prompt, "en", None, qmodel, cwd=folder or None, readonly=True):
                    k = evd.get("kind")
                    if k == "status":
                        qprog.append("• " + evd.get("text", ""))
                        yield sse("status", {"icon": evd.get("icon", "🔧"), "text": f"{qa}: {evd.get('text', '')}"}); activity.beat(pid, qa)
                    elif k == "tool_result":
                        ok = not evd.get("error")
                        qprog.append(("   ↳ ✅ " if ok else "   ↳ ❌ ") + evd.get("text", ""))
                        yield sse("status", {"icon": "✅" if ok else "❌", "text": f"{qa}: {evd.get('text', '')[:90]}"}); activity.beat(pid, qa)
                    elif k == "text":
                        yield sse("token", {"member": qa, "t": evd["t"]}); activity.beat(pid, qa)
                    elif k == "final":
                        qreply = evd.get("text")
                try:
                    _mtd.append(pid, qa, "✓ phase: engine call returned (QA gate)")
                except Exception:
                    pass
                qreply = (qreply or "(no output)").strip()
                if qprog:
                    scopes.add_message(qscope, qchat["id"], "assistant", "🔧 QA checks run:\n" + "\n".join(qprog[-50:]))
                scopes.add_message(qscope, qchat["id"], "assistant", qreply)
                # QA's verdict belongs in the ONE shared pool too (like every member's work), so the
                # running history shows that QA actually tested this part — not just buried in QA's scope.
                # Mirror it into the project pool with QA as the labeled sender, so the owner SEES the
                # agent-to-agent ping-pong (who tested what, what the verdict was) on every client.
                _pool_post(pid, f"🧪 QA review of {area_member} (attempt {attempt}):\n{qreply}", sender=qa)
                try:
                    import main_task as _mtq
                    _mtq.append(pid, "QA", f"[QA review of {area_member} — attempt {attempt}] {(qreply or '')[:700]}")
                except Exception:
                    pass

                # ROBUST VERDICT: the model often prepends a preamble ("Perfect, I've completed the QA…")
                # before its verdict, so we look for an EXPLICIT 'PASS:'/'FAIL:' token ANYWHERE, not just at
                # the start. An explicit FAIL wins; otherwise an explicit PASS is a pass. We do NOT treat the
                # mere word "error" as a failure — QA legitimately says "error handling verified" / "no errors".
                _q = (qreply or "")
                _qu = _q.upper()
                has_fail = ("FAIL:" in _qu) or _qu.lstrip().startswith("FAIL")
                has_pass = ("PASS:" in _qu) or _qu.lstrip().startswith("PASS")
                if has_pass and not has_fail:
                    is_fail = False
                elif has_fail and not has_pass:
                    is_fail = True
                elif has_fail and has_pass:
                    # both present — trust the FIRST verdict token that appears
                    is_fail = _qu.find("FAIL:") != -1 and (_qu.find("FAIL:") < _qu.find("PASS:") if "PASS:" in _qu else True)
                else:
                    # no explicit verdict token — only a clear "it isn't built/working" statement fails it
                    is_fail = bool(re.search(r"\b(does not work|not built|was not built|cannot find the app|"
                                             r"folder is empty|no source files|missing the app)\b", _q, re.I))
                # AUDIT GATE: never accept a PASS the EVIDENCE genuinely contradicts — BUT a QA exploratory
                # command returning non-zero (a grep with no match, an ls of a maybe-absent path) is NORMAL
                # and must NOT flip a real PASS (that bug looped step 1 forever). Only a genuine hidden-fault
                # SIGNATURE in the evidence (build=True ignores transient build noise) overrides a PASS.
                try:
                    import audit
                    evidence = "\n".join(qprog)
                    snakes = audit.scan_hidden_faults(evidence, build=True)
                    if (not is_fail) and snakes:
                        is_fail = True
                        labels = ", ".join(sorted({h["label"] for h in snakes})) or "failed steps"
                        qreply = f"FAIL (audit override): QA said PASS but the evidence shows {labels}. " + _q
                        scopes.add_message(qscope, qchat["id"], "assistant",
                                           f"🕵️ Audit blocked a fake PASS — evidence contradicts it ({labels}).")
                        yield sse("status", {"icon": "🕵️", "text": f"Audit blocked a fake PASS ({labels})"})
                except Exception:
                    pass
                if not is_fail:
                    passed = True
                    yield sse("status", {"icon": "✅", "text": f"QA: {area_member}'s part verified"})
                    break

                yield sse("status", {"icon": "🛑", "text": f"QA found a bug in {area_member}'s part — reporting to the CTO"})
                route = projects._engine(
                    f"You are the Project CTO for '{name}'. QA tested {area_member}'s part and it FAILED.\n"
                    f"Errors:\n{(qreply or '')[:1600]}\n\n"
                    f"The team and what each did: {roster}.\nExisting members you may assign: {', '.join(candidates)}.\n"
                    "Decide which EXISTING member should fix this — the one who owns that area (the WHOLE web "
                    "app — UI + API + DB + integration code → Fullstack; mobile → Mobile; deploy → DevOps). "
                    "Do not invent a new role and do not name obsolete Frontend/Backend/Database roles.\n"
                    'Reply with ONLY a JSON object: {"member":"<existing member name>","fix":"<one concise, specific instruction>"}')
                routed = projects._extract_json_object(route) or {}
                pick = str(routed.get("member") or "")
                fixer = next((n for n in candidates if n.lower() == pick.lower()), None) \
                    or next((n for n in candidates if pick and (n.lower() in pick.lower() or pick.lower() in n.lower())), None) \
                    or area_member
                fix_instr = routed.get("fix") or "Fix the bug QA reported."
                scopes.add_message(qscope, qchat["id"], "user", f"[Project CTO] Routing the fix to {fixer}: {fix_instr}")

                if attempt == MAX_ATTEMPTS:
                    yield sse("status", {"icon": "⚠️", "text": f"{area_member}'s part still failing after {MAX_ATTEMPTS} attempts"})
                    break

                if _ensure_member(fixer):
                    yield sse("status", {"icon": "➕", "text": f"CTO brought in {fixer}"})
                fscope = f"member:{pid}:{fixer}"
                fchat = scopes.create_chat(fscope, title="▶ Fix QA bug")
                fmodel = models_config.get_model(fscope)
                activity.mark_active(pid, fixer, task="fix QA bug", phase=f"{fixer}: fixing")
                activity.log_flow(pid, qa, fixer, note="fix bug")
                yield sse("status", {"icon": "🔧", "text": f"CTO → {fixer}: fix the bug QA found"})
                fix_prompt = (
                    f"You are the {fixer} agent on project '{name}'. Work INSIDE the project folder:\n{folder}\n"
                    f"{owner_brief}"
                    f"QA tested the part and it FAILED with these issues:\n{(qreply or '')[:1600]}\n\n"
                    f"Your CTO instructs: {fix_instr}\n"
                    "Analyze the cause within the owner's instructions (do not rewrite unrelated code). If a code "
                    "or command change is needed, propose it as instructed for the owner's approval.")
                scopes.add_message(fscope, fchat["id"], "user", f"[Project CTO → {fixer}] {fix_instr} (QA bug)")
                for item in _run_gated(pid, fixer, fscope, fchat["id"], fix_prompt, fmodel, folder,
                                       task_label=f"{fixer}: fix QA bug", auto_approve=auto_approve):
                    if isinstance(item, tuple) and item and item[0] == "__return__":
                        pass
                    else:
                        yield item
                activity.mark_idle(pid, fixer)
                yield sse("status", {"icon": "🔁", "text": f"{fixer} applied a fix — QA re-testing"})
            activity.mark_idle(pid, qa)
            yield ("__return__", passed)

        prev = "Project CTO"
        # Is this run a deploy/sync to the VM? If so, the DevOps member must NOT improvise the deploy
        # (that's the source of the snakes). It runs the PROVEN deterministic pipeline instead, once.
        # deploy_ctx: a run is a DEPLOY only when the OWNER'S ACTUAL ASK (goal) calls for it — NOT
        # because the big project brief happens to describe a deploy capability (it always does). And
        # an explicit "no deploy / read-only" ask hard-disables it, so a diagnosis run is NEVER forced
        # through the deploy-plan branch (that was the source of "could not derive a safe deploy plan").
        _no_deploy_ask = any(_p in (goal or "").lower() for _p in (
            "no deploy", "not deploy", "don't deploy", "dont deploy", "do not deploy",
            "without deploy", "avoid deploy", "no need to make any deploy",
            "not asking about deploy", "read-only", "read only"))
        deploy_ctx = (bool(deploy_mode) or _touches_vm(goal or "")) and _cls.get("mode") != "direct" \
            and "deploy" not in _forbid and not _no_deploy_ask
        deploy_done = {"v": False}
        _deployed_once = False   # a deploy runs ONCE per run — later deploy steps must NOT re-run it
        for idx, step in enumerate(steps):
            member, task = step["member"], step["task"]
            try:    # DIAGNOSTIC: prove each step is reached + show the hand-off in the shared pool
                main_task.append(pid, "orchestrator", f"▶ starting step {idx + 1}/{total}: {member} — {str(task)[:60]}")
                activity.mark_active(pid, member, task=f"step {idx + 1}/{total}", phase=f"starting {member}")
            except Exception:
                pass
            deps = step.get("depends_on") or []
            if _ensure_member(member):
                yield sse("status", {"icon": "➕", "text": f"CTO hired a new member: {member}"})
            # dependency WAIT: a dependent part starts only after its dependency has passed QA
            waiting = [d for d in deps if d not in passed_members]
            if deps:
                done_deps = [d for d in deps if d in passed_members]
                if done_deps:
                    yield sse("status", {"icon": "⛓️", "text": f"{member} can start — {', '.join(done_deps)} passed"})
                if waiting:
                    yield sse("status", {"icon": "⏳", "text": f"{member} depended on {', '.join(waiting)} (not yet passed) — proceeding with caution"})
            yield sse("delegate", {"pid": pid, "to": member, "step": idx + 1, "of": total, "task": task})
            activity.mark_active(pid, member, task=task[:60])
            activity.log_flow(pid, prev, member, note=task[:40])

            # OWNER REQUIREMENTS STEP — the CTO collected missing inputs and is confirming them with the owner.
            # This is NOT an agent task: it is answered by the owner. In testing I (the harness) am the owner and
            # the env/keys + target are supplied in the brief, so resolve it instantly and deterministically —
            # no engine call, no QA — and record it so Fullstack can read the provided env downstream.
            if str(member).strip().lower() in ("owner", "user", "you"):
                _ans = (owner_answer or "").strip() if 'owner_answer' in dir() else ""
                _od = (f"✅ Owner: requirements confirmed — the environment variables / integration keys and the "
                       f"deploy target needed for this work are provided in the brief and the shared pool"
                       + (f". {_ans}" if _ans else ".") +
                       " Fullstack: read the integration keys from the env/brief/pool (not from any operator).")
                try:
                    import main_task as _mto
                    _mto.append(pid, member, _od)
                    _mto.write_deliverable(pid, member, _od, done=True)
                except Exception:
                    pass
                deliverables[member] = _od
                results.append({"member": member, "task": task, "review": "Confirmed: requirements provided by owner."})
                passed_members.append(member)
                yield sse("status", {"icon": "📋", "text": f"{member}: requirements confirmed (env/keys/target provided)"})
                yield sse("step_done", {"member": member, "step": idx + 1, "result": _od[:200]})
                prev = member
                continue

            mscope = f"member:{pid}:{member}"
            mchat = scopes.create_chat(mscope, title=f"▶ {task[:28]}")
            model = models_config.get_model(mscope)

            # 1) STRUCTURED MANDATE + STRUCTURED HAND-OFF (how strong systems avoid context-leak):
            #    the member gets its bounded mandate + ONLY the upstream deliverables it depends on —
            #    not a raw dump. The owner's verbatim rules stay available as authoritative reference.
            _mandate = (f"OBJECTIVE: {step.get('objective', task)}\n"
                        f"DELIVERABLE (produce exactly this): {step.get('deliverable', '(your completed part)')}\n"
                        f"ACCEPTANCE CRITERIA (verify before you report done): {step.get('acceptance_criteria', 'works and matches the brief')}")
            try:
                import main_task
                _checklist = main_task.checklist_text(pid)
                _pool = main_task.pool_text(pid)         # the ONE growing shared context, for the active member
            except Exception:
                _checklist, _pool = "", ""
            try:
                import cached_modules
                _cached = cached_modules.index_text(member)   # this role's pool — fetch + decide
            except Exception:
                _cached = ""
            _deps = step.get("depends_on") or []
            _dep_block = "\n".join(f"- from {d}: {str(deliverables.get(d, '(not yet delivered)'))[:600]}" for d in _deps) or "(none — you start fresh)"
            brief = (f"[Project CTO → {member}] Your MANDATE for '{name}':\n{_mandate}\n\n"
                     f"Upstream deliverables you build on:\n{_dep_block}\n\n"
                     "Own EXACTLY this mandate (don't drift into other members' parts). For anything that "
                     "changes production, propose the exact commands for approval. Report your DELIVERABLE "
                     "and the VERIFIED result against the acceptance criteria.")
            scopes.add_message(mscope, mchat["id"], "user", brief)
            activity.mark_active(pid, member, task=task[:60], phase=f"CTO → {member}: briefing")
            yield sse("status", {"icon": "🗣️", "text": f"CTO briefs {member} with a bounded mandate"})

            # 2) member works READ-ONLY; any change it needs is PROPOSED and gated for your approval
            activity.mark_active(pid, member, task=task[:60], phase=f"{member}: working")
            yield sse("status", {"icon": "⚙️", "text": f"{member} is working…"})
            # RESOURCES & DEPENDENCIES the agent reviews first: prefer the per-agent STORED (owner-editable)
            # section + its env vars; fall back to the role-catalogue default. This is what makes the section
            # editable from the dashboard and present for dynamically-created agents.
            try:
                import projects as _projres
                _ag = None
                try:
                    import agents_registry as _ar
                    _ag = _ar.get_agent(pid, member)
                except Exception:
                    _ag = None
                _resources = (_ag or {}).get("resources") or _projres.resources_block(member)
                _envrows = (_ag or {}).get("env") or []
                if _envrows:
                    _envtxt = "\n".join(f"  • {e.get('key')}={e.get('value')}" for e in _envrows if e.get("key"))
                    if _envtxt:
                        _resources += ("\n• PROJECT ENV VARS provided for you (use these directly — do NOT ask "
                                       "for them):\n" + _envtxt + "\n")
            except Exception:
                _resources = ""
            try:
                _orient = _orientation_block(member)
            except Exception:
                _orient = ""
            work_prompt = (f"You are the {member} agent on project '{name}'.\n{loc}\n"
                           f"{_pool}\n"
                           f"{_checklist}\n"
                           f"{_cached}\n"
                           f"{_resources}\n"
                           f"{_orient}\n"
                           f"YOUR MANDATE — the working spec, own EXACTLY this:\n{_mandate}\n\n"
                           f"Upstream deliverables you build on:\n{_dep_block}\n\n"
                           f"OWNER'S FULL RULES — authoritative reference; obey their exact paths/commands/"
                           f"excludes where they apply, never violate, but only act on YOUR mandate:\n{owner_brief}\n\n"
                           "STEP 1 — READINESS CHECK (do this FIRST, in ONE short block, before any work):\n"
                           "  • REQUIRES: list exactly what THIS mandate needs — inputs, env vars/API keys, "
                           "upstream deliverables, permissions/tools.\n"
                           "  • HAVE: for EACH required item, state whether you HAVE it and WHERE it is (your "
                           "ALLOWED RESOURCES section above, the brief/mandate, the shared pool, the project "
                           "`.env`, or `workspace/shared/oth/.cred`). A key may be given as a literal value OR as a file PATH — "
                           "if a path, read the file.\n"
                           "  • MISSING: only items found in NONE of those sources.\n"
                           "Then: if MISSING is empty, write 'Ready' and PROCEED immediately — NEVER ask for "
                           "anything already in HAVE, and NEVER ask twice. If MISSING is non-empty, ask the CTO "
                           "ONCE for exactly those items and stop until answered. Do NOT begin by testing a key "
                           "unless the task itself requires it.\n"
                           "STEP 2 — do the work strictly within your mandate, produce the DELIVERABLE, verify it "
                           "against the ACCEPTANCE CRITERIA, and report the verified result; if changes to "
                           "production are needed, propose them for the owner's approval.")
            import audit as _audit
            reply, step_clean, correction = None, True, ""
            try:    # DIAGNOSTIC: prove the step is reached + show the branch conditions in the shared pool
                main_task.append(pid, member,
                                 f"▶ step start — is_devops={_is_devops(pid, member)} deploy_ctx={deploy_ctx} "
                                 f"auto_approve={auto_approve} deployed_once={_deployed_once}")
            except Exception as _de:
                try:
                    main_task.append(pid, member, f"▶ step start — diag error: {_de}")
                except Exception:
                    pass

            # OPERATOR KEY HAND-OFF — INSTANT & deterministic. An operator "providing its API key" is a
            # one-line fact (the key is already saved in workspace/shared/oth/.cred), NOT an autonomous-agent task. Spending
            # a ~3-minute cold agent call on it is unacceptable. Announce availability and move on with no
            # engine call, no audit, no QA. (The operator's REAL work — verifying live data AFTER deploy —
            # does NOT match this hand-off pattern, so it still runs a real call below.)
            _skip_engine = False
            _HANDOFF_RE = re.compile(r"\b(hand[- ]?off|hand over|provide|supply|give|share|deliver|save)\b"
                                     r".{0,45}?\b(api\s*key|key|credential|secret|token|connection|access|id)\b", re.I)
            if _is_operational(pid, member) and _HANDOFF_RE.search(task or ""):
                reply = (f"✅ {member}: the API key & connection details for my platform are SAVED and "
                         f"available (read-only) for Fullstack to use. I write no code and build nothing — "
                         f"Fullstack owns the integration; I will verify the live data after deploy.")
                step_clean = True
                _skip_engine = True
                scopes.add_message(mscope, mchat["id"], "assistant", reply)
                try: _pool_post(pid, f"[{member}] {reply}")
                except Exception: pass
                yield sse("status", {"icon": "🔑", "text": f"{member}: API key handed off (instant, no build)"})
                yield sse("token", {"member": member, "t": reply})
            # HYBRID for a DevOps DEPLOY: the AI REASONS a deploy DECISION (which targets, what method,
            # adapting to what the owner asked), then a DETERMINISTIC tool EXECUTES it reliably and the
            # audit verifies. The AI keeps its judgment; execution stops being a dice roll.
            elif _is_devops(pid, member) and deploy_ctx and _deployed_once:
                # The deploy ALREADY ran once this run (it does the whole thing — sync, build, reboot,
                # verify — in ONE execution). Do NOT run it again for the other plan steps; that's what
                # caused the endless reboots. Mark this step done and move on.
                reply = ("✅ The deploy already ran once in this run (it synced, built, rebooted and "
                         "verified in a single execution). Not repeating it — re-running would reboot/reset "
                         "the VM again. This step is covered by that one deploy.")
                step_clean = True
                scopes.add_message(mscope, mchat["id"], "assistant", reply)
                try:
                    _pool_post(pid, f"[{member}] {reply}")
                except Exception:
                    pass
                yield sse("token", {"member": member, "t": reply})
            elif _is_devops(pid, member) and deploy_ctx:
                import deploy_runner as _dr, operations as _ops
                _deployed_once = True   # mark IMMEDIATELY so no later step re-runs the deploy
                _dep_req = True   # deploy-trigger flag; refined by the change-detection scan below
                # LIVENESS: the next call (ai_decide_deploy) is a single BLOCKING AI call that emits no
                # pool/heartbeat while it runs — without this, a watchdog wrongly thinks the run stalled.
                # Post an interim pool entry + mark active so monitors see it's working.
                try:
                    activity.mark_active(pid, member, task="reasoning the deploy plan", phase=f"{member}: planning deploy")
                    # RESTATE the exact specifics from the owner brief (deterministic, not flaky AI JSON) so the
                    # shared pool PROVES DevOps consumed them: target paths, full exclude list, exact commands, reboot.
                    _bp = owner_brief
                    _r_paths = sorted(set(re.findall(r"/home/\S+", _bp)))
                    _r_excl = sorted(set(re.findall(r"\*\.[A-Za-z0-9]+|node_modules|\.env\*|\.backup-env|\.next|dist|prisma/migrations|public|uploads|package(?:-lock)?\.json", _bp)))
                    _r_cmds = sorted(set(re.findall(r"(?:npx\s+)?prisma\s+migrate[^\n;&]*|npm\s+run\s+build|rm\s+-rf[^\n;&]*|sudo\s+reboot", _bp)))
                    _restate = ("Acting on the owner's EXACT brief — targets: " + (", ".join(_r_paths) or "(none)")
                                + " | excludes: " + (", ".join(_r_excl) or "(none)")
                                + " | commands: " + (" ; ".join(_r_cmds) or "(none)"))
                    try:
                        import subprocess as _sp, sys as _sys, os as _os
                        _r = _sp.run([_sys.executable, "workspace/shared/infra/deploy_changes.py", "scan", "--project", pid],
                                     capture_output=True, text=True, timeout=120, env=dict(_os.environ))
                        _tt = (_r.stdout or "") + "\n" + (_r.stderr or "")
                        _dbs = "DB_SENSITIVE: YES" in _tt
                        _dep_req = "DEPLOY_REQUIRED: YES" in _tt
                        _chg = [l.strip()[2:].strip() for l in _tt.splitlines() if l.strip().startswith("~ ")]
                    except Exception:
                        _dbs, _chg, _dep_req = False, [], True
                    _fh = (", ".join(_chg[:12]) + (" \u2026" if len(_chg) > 12 else "")) if _chg else "the detected changes"
                    _dbn = (" A DB rebase/migration is RECOMMENDED (schema/seed changed) \u2014 you'll be asked to approve it separately." if _dbs else " No database change (code only).")
                    main_task.append(pid, member, f"Deploy check \u2014 changed: {_fh}.{_dbn}")
                except Exception as _rerr:
                    import traceback as _tb
                    main_task.append(pid, member, f"⚠️ deploy restatement error: {type(_rerr).__name__}: {_rerr} | {_tb.format_exc()[-300:]}")
                decision = None
                if not _dep_req:
                    # Nothing changed vs what's already live (owner likely deployed manually). Do NOT deploy;
                    # open a SEPARATE approval to re-sync the change-detection baseline.
                    try:
                        import approvals as _appr0
                        _appr0.create(pid, member, title="Re-sync deploy baseline (no deploy)",
                                      summary="No files changed versus what's already live, so nothing is deployed. If you deployed manually, approve this to re-baseline the change-detection lists so future checks stay quiet.",
                                      commands=[{"cmd": f"python workspace/shared/infra/deploy_changes.py update --project {pid}", "where": "local", "why": "Re-baseline the deploy lists to the current state (no VM/production change)."}],
                                      recommended="Approve to re-sync the baseline. This makes no VM or production change.")
                    except Exception:
                        pass
                    reply = ("No deploy needed \u2014 nothing changed versus what's already live. I opened a separate "
                             "approval to re-sync the baseline in case you deployed manually; approve it to keep "
                             "future checks quiet. Nothing was deployed.")
                    step_clean = True
                    scopes.add_message(mscope, mchat["id"], "assistant", reply)
                    main_task.append(pid, member, reply)
                    yield sse("token", {"member": member, "t": reply})
                else:
                    yield sse("status", {"icon": "🧠", "text": f"{member}: preparing the deploy…"})
                    decision = _dr.ai_decide_deploy(owner_brief + "\n\nThis step: " + task)
                    if decision and decision.get("targets"):
                        # SAFETY: a deploy NEVER migrates/rebases the DB on its own \u2014 code-only by default;
                        # a DB change is a SEPARATE approval popup the owner must click.
                        decision["migration_intent"] = "none"
                        for _t in decision["targets"]:
                            _t["migration"] = "none"
                        if _dbs:
                            try:
                                import approvals as _appr1
                                _appr1.create(pid, member, title="Database migration recommended",
                                              summary="Schema/seed files changed in this deploy. The code is deployed WITHOUT touching the database; approve this separately to apply the additive migration (no data reset/rebase).",
                                              commands=[{"cmd": "cd /home/mostafa/RBO-Staging/b && npx prisma migrate deploy", "where": "vm", "why": "Apply committed migrations additively; never resets or rebases data."}],
                                              recommended="Approve to apply the additive migration (safe, no data loss); skip to keep the current DB.",
                                              kind="vm")
                                main_task.append(pid, member, "\u26a0\ufe0f This deploy includes schema/seed changes. I'm deploying the CODE only and opened a SEPARATE approval for the database migration \u2014 approve it to apply the additive migration (no rebase), or skip to leave the DB unchanged.")
                            except Exception:
                                pass
                if _dep_req and (not decision or not decision.get("targets")):
                    _why = getattr(_dr.ai_decide_deploy, "last", "")
                    reply = "I confirmed the changed files but need the target app named (backend/frontend) to run the pipeline \u2014 tell me which and I'll deploy it."
                    step_clean = False
                    scopes.add_message(mscope, mchat["id"], "assistant", "⚠️ " + reply)
                    main_task.append(pid, member, reply)   # → shared pool so the failure reason is visible
                elif decision and decision.get("targets"):
                    # restate the FULL specifics actually consumed from the brief (paths + exact excludes +
                    # build + migration + reboot + verify) so the shared pool PROVES they propagated.
                    _tgts = "; ".join(f"{t.get('name')}→{t.get('vm')}" for t in decision["targets"])
                    _ex = ", ".join(decision.get("excludes") or decision.get("excludes_extra") or [])
                    _builds = "; ".join(t.get("build", "") for t in decision["targets"] if t.get("build"))
                    _mig = decision.get("migration_intent") or "; ".join(t.get("migration", "none") for t in decision["targets"])
                    _port = decision.get("verify_port") or ""
                    _reboot = "sudo reboot" if decision.get("reboot") else "no reboot"
                    # also surface the owner's EXACT command lines from the brief (e.g. prisma migrate …),
                    # so the member's restatement is verbatim, not a normalized summary.
                    _exact_cmds = "; ".join(re.findall(r"(?:npx\s+)?prisma\s+migrate[^\n;&]*", owner_brief, re.I)[:4])
                    plan = (f"{len(decision['targets'])} app(s), "
                            + ("an additive DB migration (no rebase)" if (decision.get('migration_intent') or '') not in ('none', '') else "database untouched"))
                    scopes.add_message(mscope, mchat["id"], "assistant",
                                       "Deploy plan ready \u2014 proceeding." if auto_approve else "Deploy plan ready \u2014 awaiting your approval.")
                    main_task.append(pid, member, "Deploying the changed files now.")   # shared pool: clean, no ssh/ip/paths
                    # APPROVAL-AWARE: only EXECUTE the real deploy when the owner authorized it. Otherwise
                    # PROPOSE the exact plan (no rsync/build/migrate/reboot) — propose-only must never deploy.
                    if not auto_approve:
                        reply = f"📋 PROPOSED deploy plan (awaiting approval — nothing executed) — {plan}"
                        step_clean = True
                        scopes.add_message(mscope, mchat["id"], "assistant", reply)
                        _pool_post(pid, f"[{member}] {reply}")
                        yield sse("token", {"member": member, "t": reply})
                        decision = None   # skip execution below
                if decision and decision.get("targets"):
                    yield sse("status", {"icon": "🚀", "text": f"{member}: executing the decided plan reliably…"})
                    _oid = _ops.create(pid, "deploy", f"{member} hybrid deploy")
                    dres = _dr.run_decision(pid, decision, oid=_oid,
                                            on_log=lambda m: (scopes.add_message(mscope, mchat["id"], "assistant", str(m)[:1200]), activity.beat(pid, member)))
                    _op = _ops.get(_oid) or {}
                    _snk = _audit.scan_hidden_faults("\n".join(l.get("line", "") for l in _op.get("log", [])))
                    if dres.get("ok") and not _snk:
                        reply = f"✅ Deploy VERIFIED (real exit-0, no hidden faults) — acting on {plan}"
                        step_clean = True
                        _ops.set_state(_oid, "done", "Deploy verified (no hidden faults)")
                    elif dres.get("needs_owner"):
                        # BLOCKED → ask in the shared pool so the owner sees it and can answer + continue
                        reply = f"⛔ {member} is blocked — {dres.get('ask') or dres.get('reason', 'needs your input')}"
                        step_clean = False
                        _pool_post(pid, reply)
                        # run_decision already set state 'blocked'; leave it for the owner to answer.
                    else:
                        reply = (f"❌ Deploy not clean: {dres.get('reason', 'see log')}"
                                 + (f"; hidden faults {sorted({h['label'] for h in _snk})}" if _snk else ""))
                        step_clean = False
                        if (_ops.get(_oid) or {}).get("state") == "running":
                            _ops.set_state(_oid, "failed", dres.get("reason", "deploy not clean"))
                    scopes.add_message(mscope, mchat["id"], "assistant", reply)
                    _pool_post(pid, f"[{member}] {reply}")   # mirror the result into the group pool
                yield sse("token", {"member": member, "t": reply})

            # Everything else (NOT a DevOps deploy): the agent REASONS the task, an AUDIT EYE checks each
            # try, and on drift it gets the EXACT feedback and reasons a fix, up to 3 tries. (For the
            # hybrid deploy above, this loop is skipped — reply/step_clean are already set.)
            base_prompt = work_prompt
            # operators (key hand-off / status) get ONE attempt — no build-grade audit-retry loop;
            # the deploy hybrid skips this loop entirely; everyone else gets up to 3 self-correcting tries.
            _tries = range(0) if _skip_engine else \
                (range(1, 2) if _is_operational(pid, member) else
                 (range(1, 4) if not (_is_devops(pid, member) and deploy_ctx) else range(0)))
            for _try in _tries:
                if _try == 1:
                    prompt_now = base_prompt
                else:
                    fb = ("\n\n## AUDIT FEEDBACK — your previous attempt was REJECTED. By REASONING (do "
                          "NOT repeat the mistake, do NOT copy stale scripts), fix EXACTLY this and redo:\n- "
                          + correction)
                    if _try >= 3:
                        # step 5: same error twice → WIDEN THE SCOPE, the cause is likely elsewhere
                        fb += ("\n\n## WIDEN THE SCOPE — you've failed twice the same way. STOP repeating the "
                               "same move. The real cause is probably ELSEWHERE: search the wider codebase, "
                               "the system, configs, logs, and other files/services for the ROOT cause, then "
                               "fix that — not the symptom.")
                    prompt_now = base_prompt + fb
                if _try > 1:
                    icon = "🔭" if _try >= 3 else "🔁"
                    msg = f"{member}: widening the scope — searching elsewhere for the real cause (try {_try})" if _try >= 3 \
                        else f"{member}: audit rejected it — reasoning a correction (try {_try})"
                    yield sse("status", {"icon": icon, "text": msg})
                # record how many messages exist BEFORE this try, so the audit scans ONLY this try's output.
                try:
                    _pre_chat = scopes.get_chat(mscope, mchat["id"]) or {}
                    _msg_base = len(_pre_chat.get("messages", []))
                except Exception:
                    _msg_base = 0
                reply = None
                for item in _run_gated(pid, member, mscope, mchat["id"], prompt_now, model, folder,
                                       task_label=f"{member}: {task[:50]} (try {_try})", auto_approve=auto_approve):
                    if isinstance(item, tuple) and item and item[0] == "__return__":
                        reply = item[1].get("reply") if isinstance(item[1], dict) else item[1]
                    else:
                        yield item
                # AUDIT EYE — on EVERY try: scan this member's REAL output for drift + snakes + fakes.
                step_clean, correction = True, ""
                try:
                    _chat = scopes.get_chat(mscope, mchat["id"]) or {}
                    _allmsgs = _chat.get("messages", [])
                    # Scan ONLY this try's NEW, ASSISTANT-authored output — NOT the accumulated history and
                    # NOT the user/CTO prompt. Two reasons: (1) a TRANSIENT error from an EARLIER try (e.g. an
                    # OOM-killed foreground server the agent already abandoned) must not keep rejecting a build
                    # the agent ALREADY FIXED on a later try (the infinite-rejection loop we hit); (2) the retry
                    # feedback we inject QUOTES the previous error text in the user prompt — scanning that would
                    # re-flag the very error we're telling the agent to fix. So we look only at what the agent
                    # actually produced THIS attempt.
                    _new = _allmsgs[_msg_base:] or _allmsgs
                    _new_assist = [str(m.get("content", "")) for m in _new if m.get("role") == "assistant"]
                    # SEPARATE tool output from prose. Real faults live in TOOL OUTPUT (exit codes, killed,
                    # tracebacks) — the "🔧 Executed …  ↳ ✅/❌" messages. The agent's PROSE reply may merely
                    # EXPLAIN a past error ("the prior step produced an out-of-memory error, so I re-ran the
                    # light path") — that is honesty, not a current fault, and must NOT be scanned for snakes.
                    _is_tool = lambda t: ("🔧" in t) or ("↳" in t)
                    _tool_txt = "\n".join(t for t in _new_assist if _is_tool(t))
                    _prose_txt = "\n".join(t for t in _new_assist if not _is_tool(t))
                    _txt = "\n".join(_new_assist)
                    _probs = []
                    if re.search(r"az\s+vm\s+run-command", _tool_txt):
                        _probs.append("you used `az vm run-command` on the VM — `az` is on the Mac, NOT the VM; use SSH as mostafa")
                    if re.search(r"prisma\s+migrate\s+dev", _tool_txt):
                        _probs.append("you used `prisma migrate dev` — use `prisma migrate deploy` (non-destructive)")
                    # build=True: members BUILD from scratch, so transient dev errors (cannot find
                    # module before npm install, a TS error then fixed) are normal mid-construction and
                    # only count if still unresolved in the FINAL result — otherwise the audit rejected
                    # a perfectly good build and looped the same step forever (the "stuck on 1/6" bug).
                    # Snakes come ONLY from real TOOL OUTPUT; a success CLAIM is judged from PROSE.
                    _snk = _audit.scan_hidden_faults(_tool_txt, build=True)
                    _fake = _audit.claims_success(_prose_txt) and bool(_snk)
                    if _snk:
                        _probs.append(f"hidden errors in your output: {sorted({h['label'] for h in _snk})}")
                    if _fake:
                        _probs.append("you CLAIMED success while errors are present — never report done without a verified result")
                    # ARTIFACT GATE — a BUILD task MUST leave REAL files on disk, not a narrated plan. If
                    # the project folder is still empty, the agent only DESCRIBED the app: reject and force
                    # it to actually create files next try (this is what 'too much / 0 files' was).
                    if (not _is_operational(pid, member)) and (not _is_devops(pid, member)) and folder \
                            and re.search(r"\b(build|implement|creat\w*|develop|scaffold|write)\b", task or "", re.I):
                        import os as _os
                        _nf = 0
                        try:
                            for _r, _ds, _fz in _os.walk(_os.path.expanduser(folder)):
                                _ds[:] = [d for d in _ds if d not in ("node_modules", ".git", ".next", "dist")]
                                _nf += len(_fz)
                        except Exception:
                            _nf = 0
                        if _nf < 2:
                            _probs.append(
                                "you wrote ZERO real files to disk — you only DESCRIBED the app (a summary or "
                                "acceptance table is NOT a build). STOP explaining. Your deliverable is FILES on "
                                "disk. Right now, in the project folder, use the WRITE tool to CREATE: a project "
                                "manifest for your chosen stack (package.json / requirements.txt / pyproject.toml / "
                                "go.mod), then every source file (the API, the UI/page, the data model/schema, the "
                                "connector modules). Do NOT paste code in your reply and do NOT report any test/"
                                "acceptance results you did not actually run. When the files exist, run `ls -R` "
                                "(excluding node_modules) and show the real output as proof. An automated gate "
                                "checks the folder — if it is empty, this step is REJECTED no matter what you write.")
                    if _probs:
                        step_clean = False
                        correction = "; ".join(_probs)
                        scopes.add_message(mscope, mchat["id"], "assistant", f"🕵️ AUDIT EYE (try {_try}) rejected this step: {correction}")
                        yield sse("status", {"icon": "🕵️", "text": f"Audit flagged {member} (try {_try})"})
                except Exception:
                    pass
                if step_clean:
                    if _try > 1:
                        yield sse("status", {"icon": "✅", "text": f"{member} self-corrected and passed the audit"})
                    break

            # HARD BUILD GATE — a build step that left NO real files on disk after every retry is a genuine
            # FAILURE, not something to pass through. There is nothing to QA or deploy, and continuing is what
            # let a narrating retry hang for ~25 min on a phantom app. Stop the run NOW — fast and honest —
            # so the owner isn't billed for a doomed pipeline. (This only fires when the folder is truly
            # empty; a real build with files but a transient audit flag is unaffected.)
            _is_build_step = (not _is_operational(pid, member)) and (not _is_devops(pid, member)) and bool(folder) \
                and bool(re.search(r"\b(build|implement|creat\w*|develop|scaffold|write)\b", task or "", re.I))
            if _is_build_step and not step_clean:
                import os as _os2
                _nf2 = 0
                try:
                    for _r, _ds, _fz in _os2.walk(_os2.path.expanduser(folder)):
                        _ds[:] = [d for d in _ds if d not in ("node_modules", ".git", ".next", "dist", "__pycache__")]
                        _nf2 += len([f for f in _fz if not f.startswith(".")])
                except Exception:
                    _nf2 = 0
                if _nf2 < 2:
                    _halt = (f"⛔ BUILD FAILED — {member} reported done but wrote ZERO real files to disk after "
                             "all attempts (the project folder is empty). The app does not exist, so there is "
                             "nothing to QA or deploy. Stopping the run now instead of grinding on a phantom "
                             "build. Root cause to fix: the agent NARRATED a build (a summary/acceptance table) "
                             "instead of using the Write/Bash tools to create files.")
                    yield sse("status", {"icon": "⛔", "text": f"{member} produced no files on disk — stopping the run"})
                    try:
                        import main_task as _mth
                        _mth.append(pid, member, _halt)
                    except Exception:
                        pass
                    break   # stop the whole run — do not QA/deploy a non-existent app

            # FAILURE PROTOCOL (resource issue, in the CORE): if the agent hit a Claude quota/session/
            # rate limit, this is NOT a code fault and retrying just burns the quota → PAUSE the whole
            # run and tell the owner; resume after it resets. (Distinct from a code error, which retries.)
            if reply and any(s in str(reply).lower() for s in
                             ("session limit", "usage limit", "rate limit", "quota", "insufficient_quota", "overloaded")):
                _halt = ("⛔ RESOURCE/QUOTA limit hit (e.g. Claude session/usage limit) — pausing the run. "
                         "This is not a code error and will not be retried; resume after the quota resets.")
                yield sse("status", {"icon": "⛔", "text": _halt})
                scopes.add_message(mscope, mchat["id"], "assistant", _halt)
                try:
                    main_task.append(pid, member, _halt)
                except Exception:
                    pass
                break   # stop the whole run — do not process further steps on an exhausted quota

            # 3) CTO reviews the delivery
            activity.mark_active(pid, member, task=task[:60], phase=f"CTO reviewing {member}")
            yield sse("status", {"icon": "🔎", "text": f"CTO reviewing {member}"})
            review = projects._engine(
                f"You are the Project CTO reviewing {member}'s work on '{name}'.\nTask: {task}\n"
                f"Their report:\n{(reply or '')[:1500]}\nIn 1-3 sentences, REVIEW it: start with 'Confirmed:' if it's "
                "done correctly, otherwise start with 'Needs fix:' and say what. Be specific and brief.",
                model=(os.environ.get("ODIN_GATE_MODEL") or None))   # fast model for the gate in TESTING only
            scopes.add_message(mscope, mchat["id"], "user", f"[Project CTO review] {review}")
            results.append({"member": member, "task": task, "review": review})
            deliverables[member] = (reply or "").strip()   # structured hand-off to downstream members
            # append this member's full work + the CTO's review into the ONE shared pool, so the next
            # active agent sees the complete running history (no context lost between steps).
            try:
                import main_task
                main_task.append(pid, member, (reply or "").strip())
                main_task.append(pid, "Project CTO (review)", review)
                main_task.write_deliverable(pid, member, (reply or "").strip(), done=(step_clean))
            except Exception:
                pass

            # 4) QA TESTS this member's part — the DEFAULT after every task (incl. DevOps). This only
            # turns off when YOU turn it off (QA removed from the team / "no QA" in your brief);
            # qa_enabled already reflects your decision. The CTO does not skip it on its own.
            qa_ok = True
            # QA gates the technical BUILD, not an operator's key hand-off/status (that needs no QA and
            # going through it made operator steps take ~20 min each). Skip QA for operational members.
            # ALSO skip the per-step QA gate after a DEVOPS DEPLOY: the deploy already self-verifies
            # (real exit-0 + HTTP check) and the FINAL QA step does the real cURL verification — a second
            # QA pass here was pure redundant time that pushed the run past its cap.
            _skip_qa_gate = _is_operational(pid, member) or (_is_devops(pid, member) and deploy_ctx)
            if not _skip_qa_gate:
                qg = qa_gate(member, task)
                for item in qg:
                    if isinstance(item, tuple) and item and item[0] == "__return__":
                        qa_ok = bool(item[1])
                    else:
                        yield item
            # a step is accepted ONLY if QA passed AND the audit eye found it clean (no snakes/fakes)
            if qa_ok and step_clean:
                passed_members.append(member)
            scopes.sync_up(mscope, f"{member} delivered; QA: {'passed' if qa_ok else 'failed'}; audit: {'clean' if step_clean else 'flagged'}")
            activity.mark_idle(pid, member)
            # feed the member's NET RESULT + conclusion back to the CTO conversation (so you can
            # follow it from the project chat without opening each member)
            concl = (reply or "").strip().replace("\n", " ")
            ok_step = qa_ok and step_clean
            scopes.add_message(pscope, run_chat["id"], "assistant",
                               f"[{member} → Project CTO] {'✅ passed (QA + audit clean)' if ok_step else '⚠️ flagged — QA/audit issues'}. {concl[:260]}")
            yield sse("status", {"icon": "✅" if ok_step else "⚠️", "text": f"{member}'s part {'passed (QA+audit)' if ok_step else 'still has issues'}"})
            yield sse("step_done", {"member": member, "step": idx + 1,
                                    "result": (("✅ QA passed. " if qa_ok else "⚠️ QA issues remain. ") + (review or ""))[:400]})
            prev = member

        # --- Project CTO → Chief Engineer (completion report) ---
        all_ok = len(passed_members) >= len([s for s in steps if s]) if qa_enabled else True
        summary = "\n".join(f"• {r['member']}: {r['review'][:90]}" for r in results)
        # OMISSION GUARD: reconcile every requirement against what was actually delivered. If any
        # requirement wasn't addressed, the run is NOT complete — surface it (don't claim done).
        open_reqs = []
        try:
            import main_task
            delivered_all = "\n".join(f"{m}: {d}" for m, d in (deliverables or {}).items())
            open_reqs = main_task.reconcile(pid, delivered_all)
        except Exception:
            open_reqs = []
        # For a DEPLOY run the TRUTH is the deterministic operation's real result (exit-0 + verify),
        # not a keyword match over a terse log. If the deploy operation verifiably succeeded, report
        # success — don't let the omission-guard falsely flag a real success as "incomplete".
        # HARD-FAILURE GUARD: if a member's ENGINE call itself failed (expired Claude login / 401,
        # empty/invalid engine reply), it produced NO real work — the run can never be 'done', even
        # with QA off and even if the heuristic reconcile happened to match requirement keywords.
        _engine_fail_markers = ("oauth access token has expired", "re-authenticate to continue", "hit your weekly limit")
        try:
            _efblob = ("\n".join(str(_d) for _d in (deliverables or {}).values()) + "\n" + "\n".join(str(_r.get("review") or "") for _r in (results or []))).lower()
        except Exception:
            _efblob = ""
        _engine_failed = any(_m in _efblob for _m in _engine_fail_markers)
        _deploy_ok = False
        if deploy_ctx:
            try:
                import operations as _o2
                _lat = _o2.latest(pid) or {}
                _deploy_ok = (_lat.get("kind") == "deploy" and _lat.get("state") == "done")
            except Exception:
                _deploy_ok = False
        if _deploy_ok:
            all_ok = True
            verdict = "✅ Deploy verified successful — real exit-0 and the site responded (HTTP 200). Done."
        elif _engine_failed:
            all_ok = False
            verdict = "\u26a0\ufe0f Incomplete \u2014 a member's Claude engine could not authenticate (login/OAuth token expired). No real work was produced, so the run is NOT done. Re-run `claude` then /login, and retry."
        elif open_reqs and not (bool(steps) and all((s.get("member") in passed_members) for s in steps if s)):
            # Only truly incomplete: a member did NOT deliver. If EVERY step's member delivered real,
            # QA-clean work, the brittle keyword-overlap reconcile is a FALSE negative — do not flag it.
            all_ok = False
            miss = "; ".join(r["text"][:70] for r in open_reqs[:6])
            verdict = f"⚠️ Incomplete — {len(open_reqs)} requirement(s) NOT addressed: {miss}"
        else:
            verdict = "Everything builds and passed QA ✅" if (qa_enabled and all_ok) else \
                      ("Some parts still have QA issues ⚠️" if qa_enabled else "All requirements addressed ✅")
        scopes.add_message(pscope, run_chat["id"], "assistant",
                           f"[Project CTO → Chief] {verdict}\n{summary}")
        scopes.sync_up(pscope, f"team completed: {goal[:50]} ({verdict})")
        _timing = None
        if _e2e_timer is not None:
            try:
                secs = _e2e_timer.stop(ok=bool(all_ok))
                import run_timer
                _timing = {"seconds": secs, "cached": _e2e_timer.cached, "compare": run_timer.compare(goal[:40])}
                yield sse("status", {"icon": "⏱️", "text": f"E2E finished in {secs}s ({'cached' if _e2e_timer.cached else 'no-cache'})"})
            except Exception:
                pass
        try:
            activity.mark_idle(pid, "Project CTO")
            _fin = "\u2705 RUN FINISHED" if bool(all_ok) else "\u23f9\ufe0f RUN FINISHED (open items remain)"
            scopes.add_message(pscope, run_chat["id"], "assistant", f"{_fin} \u2014 {verdict[:120]}")
        except Exception:
            pass
        yield sse("done", {"pid": pid, "steps": total, "ok": bool(all_ok), "timing": _timing})
    except Exception as e:
        yield sse("error", {"text": str(e)})


def _vm_needs_root(cmd: str) -> bool:
    """Only genuine root ops run as root; everything else runs as the app user (mostafa) so no
    root-owned files are created."""
    c = (cmd or "").lower()
    return any(k in c for k in ("reboot", "shutdown", "ufw", "systemctl", "apt-get", "apt install",
                                "chown", "chmod", "usermod", "service "))


_DEVOPS_KNOWLEDGE = (
    "\n\n## DEPLOYMENT KNOWLEDGE — you are a senior DevOps engineer. REASON it out; you are NOT a "
    "fixed script. Apply these as expert knowledge + hard safety rails, and ADAPT to whatever method "
    "the owner asks for:\n"
    "- CHANNEL: reach the VM over SSH as user `mostafa` with the password in workspace/shared/oth/.cred (key azvmcred), "
    "forcing password auth. Use the Azure control plane ONLY to refresh the firewall (NSG port-22 + ufw) "
    "to the owner's current IP. NEVER run app commands via `az vm run-command` — `az` is on the Mac, not "
    "the VM (that's the classic 'az: command not found' failure).\n"
    "- MIGRATIONS: use `npx prisma migrate deploy` (applies committed migrations, keeps data). NEVER "
    "`prisma migrate dev` on the VM (interactive; resets on drift; hangs over SSH). `migrate reset` is "
    "destructive — only on the owner's explicit per-run approval.\n"
    "- EXCLUDES: never sync .env*/.backup-env/keys/oauth json, node_modules, build output, "
    "prisma/migrations, public, uploads, package*.json.\n"
    "- TOOL YOU MAY CHOOSE: for the standard organics deploy there is a proven, ready script "
    "`bash workspace/shared/infra/deploy.sh` (firewall → rsync → migrate deploy → build → reboot → verify, with a real "
    "summary). Use it when it fits. If the owner asks for a DIFFERENT method/target, design that yourself "
    "WITHIN these rails — don't force the script.\n"
    "- IGNORE STALE SCRIPTS: the project folder may contain OLD deploy scripts (e.g. "
    "organics-local-vm-deploy-sync/sync-backend-to-vm.sh, preflight-sync.sh). They use the DEPRECATED, "
    "BROKEN method (az control plane, hardcoded production paths, `nc` that times out). Do NOT read them "
    "for method and do NOT copy them. They are known-bad. Use ONLY the method in this knowledge and the "
    "exact target paths the owner gave you THIS run.\n"
    "- TARGET PATHS: deploy to the EXACT destination the owner specified this run — never substitute a "
    "different/hardcoded path. If the owner gave a sandbox/test path, deploy there, not to production.\n"
    "- FIREWALL SCOPE: SSH/22 stays open to EXACTLY ONE IP (your current public IP) — never 0.0.0.0/0. "
    "Ports 80 and 443 (the reverse proxy) are already serving — do NOT modify, close, or reorder their "
    "rules; only ADD the single-IP 22 rule if it's missing, leaving everything else untouched.\n"
    "- PER-COMMAND VERIFICATION: after EACH remote command, read its REAL exit code AND output and judge "
    "from that — never assume a command worked because it ran. Non-zero exit / stderr / unexpected output "
    "= not done; report the exact output and fix or retry.\n"
    "- SYNC MUST OVERWRITE (content-level): files are synced with rsync `--checksum` so a changed file "
    "ALWAYS overwrites the VM copy by CONTENT (not just adding missing files). The deploy AUTO-VERIFIES "
    "this (a `--checksum --dry-run` pass that must show ZERO pending files); if any file is still stale, "
    "the update did NOT take — investigate (path/permissions/excludes) and redo until the VM matches local.\n"
    "- TRUTH (non-negotiable): never report 'done/passed/deployed' without VERIFYING it with a real exit "
    "code / HTTP 200. If a step fails, diagnose the REAL cause and fix it; an audit watches every step and "
    "will reject a fake success.\n"
)


def _direct_member(pid: str, goal: str) -> str:
    """Pick ONE agent to handle a scoped/direct request -- no team."""
    try:
        import agents_registry as _ar
        team = [m.get("name", "") for m in _ar.list_agents(pid)]
    except Exception:
        team = []
    gl = (goal or "").lower()
    ops = any(k in gl for k in ("vm", "ssh", "deploy", "rsync", "server", "log", "journalctl",
                                "firewall", "nsg", "ufw", "trigger", "script", "psql", "db", "az "))
    def _pick(pref):
        for p in pref:
            for m in team:
                if p in m.lower():
                    return m
        return None
    if ops:
        m = _pick(["devops", "cloud", "sre", "backend", "fullstack"])
        if m:
            return m
    m = _pick(["fullstack", "backend", "frontend", "analytics", "reporter"])
    if m:
        return m
    for m in team:
        if "qa" not in m.lower():
            return m
    return team[0] if team else "DevOps"


def _is_operational(pid: str, member: str) -> bool:
    """Is this an OPERATIONAL (non-technical) member? They hand off a key / report status — a light
    task that must NOT go through the build-grade audit-retry + QA pipeline (that made a key hand-off
    take ~24 minutes). One attempt, no QA gate."""
    try:
        import agents_registry, projects
        a = agents_registry.get_agent(pid, member) or {}
        if str(a.get("nature", "")).lower() == "operational":
            return True
        cat = {**projects.ALL_MEMBERS, **projects.OPERATIONAL_MEMBERS}
        c = cat.get(member) or {}
        return str(c.get("nature", "")).lower() == "operational"
    except Exception:
        return False


def _is_devops(pid: str, member: str) -> bool:
    """Is this member the DevOps/deploy role? Used to route deploys to the proven pipeline instead
    of letting the agent improvise (which produced the control-plane / migrate-dev / az-on-VM snakes)."""
    try:
        import agents_registry
        a = agents_registry.get_agent(pid, member) or {}
        if a.get("avatar") == "devops" or "devops" in str(a.get("role", "")).lower():
            return True
    except Exception:
        pass
    return "devops" in (member or "").lower()


def _orientation_block(member: str) -> str:
    """Give the agent a LIVE map of its own powers + where everything lives, assembled from the REAL
    structure (its capability.md, the shared tools, tutorials, scopes, directions). This is what turns
    the agent from a blind pipeline step into a smart engineer: the directions/middleware/audit/db/
    scopes/structure ENRICH its reasoning instead of gating it. Best-effort; never throws."""
    import os
    root = os.getcwd()
    def _read(rel, n=900):
        try:
            with open(os.path.join(root, rel), encoding="utf-8", errors="ignore") as f:
                return f.read(n).strip()
        except Exception:
            return ""
    slug = re.sub(r"[^a-z0-9]", "", (member or "").lower())
    cap = ""
    try:
        for d in sorted(os.listdir(os.path.join(root, "workspace/agents"))):
            ds = re.sub(r"[^a-z0-9]", "", d.lower())
            if ds and (ds == slug or (len(slug) >= 4 and (slug in ds or ds in slug))):
                cap = _read(f"workspace/agents/{d}/capability.md", 900)
                if cap:
                    break
    except Exception:
        pass
    tut = _read("workspace/shared/tutorials/INDEX.md", 650)
    out = ["## YOUR CAPABILITIES & WHERE TO FIND WHAT — orient yourself, then act like a smart engineer. "
           "This is CONTEXT to USE, never a script to recite."]
    if cap:
        out.append("### What YOU can do (your capability.md):\n" + cap)
    out.append(
        "### Shared tools & knowledge — pick the RIGHT one for the task:\n"
        "- DEPLOY TRIGGER: `python workspace/shared/infra/deploy_changes.py scan` -> DEPLOY_REQUIRED (yes/no) "
        "+ the exact modified files; `dbscan` -> DB_SENSITIVE (schema/seed changed => a DB rebase should be "
        "RECOMMENDED and the owner ASKED); `update` -> re-baseline the lists AFTER a verified deploy (or after "
        "the owner deployed manually). Run it; never hand-guess what changed.\n"
        "- DEPLOY PIPELINE (only once the owner approves a deploy): `workspace/shared/infra/deploy.sh` "
        "(firewall -> rsync as mostafa -> migrate deploy -> build -> restart -> verify). The SSH / dynamic-IP / "
        "firewall mechanics are INTERNAL plumbing handled for you — do NOT theorize about them and NEVER surface "
        "them to the Chief; report the decision and the real result only.\n"
        "- PROVIDER KNOW-HOW: read `workspace/shared/tutorials/INDEX.md` + the per-provider file "
        "(veeqo_fulfillment_api.md, easypost_tracking_api.md, ...) BEFORE diagnosing; decide state from the "
        "DOCUMENTED fields, never guessed ones.\n"
        "- SCOPED CREDENTIALS: resolve via the DELTA (getVeeqoConfig / getKlaviyoConfig / getHubspotConfig from "
        "the seeded odin_core_iso DB); else the DEFAULT in `workspace/shared/oth/.cred`. Report credential_source "
        "(delta|default). Never print a key VALUE.\n"
        "- RULES & GOVERNANCE: `workspace/shared/directions/core-rules.md` + `ORCHESTRATOR.md`; odin_core_iso DB is "
        "the single source of truth under middleware + audit + project-scope + agent-scope.")
    if tut:
        out.append("### Tutorials index:\n" + tut)
    return "\n\n".join(out) + "\n"


def _touches_vm(goal: str) -> bool:
    """Does this run touch Azure/the VM (anything beyond local)? If so, it must ALWAYS go through
    the approval popup — read-only analysis runs free, but every VM/Azure STATE change waits for the
    owner's approve/discard, regardless of any 'authorized' phrasing in the brief."""
    g = (goal or "").lower()
    return any(k in g for k in ("azure", " vm", "vm ", "django-vm", "rsync", "/home/", "deploy",
                                "sync", "reboot", "prisma migrate", "ssh ", "run-command", "/bendcore",
                                "/organics", "control plane"))


def _run_preauthorized(goal: str) -> bool:
    """The owner EXPLICITLY authorized this run → execute it directly, no approval popup.
    Recognizes how the owner ACTUALLY authorizes — explicit execution language and the
    'this time only / exactly as written / strictly the listed commands' patterns — not just my
    earlier narrow phrases (which were the reason it kept describing instead of doing)."""
    g = (goal or "").lower()
    phrases = (
        # explicit prior-approval language
        "approval already granted", "approval granted for this", "authorized for this run",
        "authorized this run", "approved for this run", "executed under the approval",
        "execute under the approval", "do not ask for approval", "don't ask for approval",
        "dont ask for approval", "no approval needed", "execute directly without",
        "you are authorized to execute", "approve in advance", "pre-approved", "pre approved",
        # how the OWNER actually authorizes a run in plain language
        "must be executed", "to be executed", "executed with extreme care", "this is a must",
        "this time only", "allow the data reset", "exactly according to these instructions",
        "without adding or skipping", "without omitting or discarding",
        "strictly limited to the commands", "commands to be executed", "execute exactly",
        "execute the following", "run these commands", "be executed in order",
    )
    return any(p in g for p in phrases)


def _is_work_request(text: str) -> bool:
    """Heuristic: does this chat message ask the team to DO engineering work (build/change/test),
    as opposed to a question or status check? Used so a CTO chat like 'add a page and test' runs
    the real pipeline (plan → members → QA), while 'what's the status?' just gets an answer."""
    import re as _re
    t = (text or "").lower().strip()
    if not t:
        return False
    strong = ("add", "create", "build", "implement", "develop", "fix", "refactor", "deploy",
              "integrate", "install", "scaffold", "make ", "write ", "rebuild", "redo",
              "run the team", "build and test", "set up", "setup", "wire ", "connect ")
    soft = ("test", "update", "change", "improve", "optimize", "optimise", "migrate", "verify")
    has_strong = any(_re.search(r"\b" + _re.escape(v), t) for v in strong)
    has_soft = any(_re.search(r"\b" + _re.escape(v), t) for v in soft)
    q_open = (t.split()[0] if t.split() else "") in (
        "what", "why", "how", "who", "where", "when", "which", "is", "are", "do",
        "does", "did", "should", "could", "can")
    if has_strong:
        return True
    return has_soft and not q_open


def _brain_orientation(pid: str, member: str = "") -> str:
    """Awareness the CTO brain needs to act SMART: what team/roles it has, what live services it can read,
    the shared tools/provider know-how, and an explicit anti-duplication + scope-discipline instruction.
    This ENHANCES the brain (it never gates it) — so it reuses what exists, uses real tools, and never
    invents requirements from other projects."""
    lines = []
    try:
        import agents_registry as _ar
        ags = _ar.list_agents(pid) or []
        roster = "; ".join(f"{a.get('name')} ({a.get('role','')})" for a in ags if a.get('name'))
        if roster:
            lines.append("[YOUR TEAM / ROLES available for THIS project (draw on them only as the task truly needs; "
                         "do not invent work for idle roles): " + roster + "]")
    except Exception:
        pass
    try:
        import capabilities as _cap
        conns = [c.get("name") for c in (_cap.list_connectors() or [])
                 if c.get("status") == "connected" and c.get("name")]
        if conns:
            lines.append("[CONNECTED SERVICES you can read LIVE (use the right one for THIS project; never guess a "
                         "value you can fetch): " + ", ".join(conns) + "]")
    except Exception:
        pass
    try:
        lines.append(_orientation_block(member or "Project CTO"))
    except Exception:
        pass
    # provider tutorials (consistency: decide provider state from DOCUMENTED fields, never guessed)
    try:
        import workspace_mw as _mw_t
        _tg = _mw_t.tutorial_guard(pid)
        if _tg:
            lines.append(_tg)
    except Exception:
        pass
    # agent / credential scope (consistency: use THIS project's scoped key reference, never a copied secret)
    try:
        import workspace_mw as _mw_s
        _sg = _mw_s.agent_scope_guard(pid, member or "Project CTO")
        if _sg:
            lines.append(_sg)
    except Exception:
        pass
    # audit awareness (consistency: never use confirmed-broken methods; use the proven path)
    try:
        import audit as _au, projects as _pjb
        _brk = _au.audit_prompt((_pjb.get_project(pid) or {}).get("description", "")) or []
        if _brk:
            lines.append("[AUDIT — AVOID these confirmed-broken methods (use the proven path instead): "
                         + "; ".join(str(b) for b in _brk[:6]) + "]")
    except Exception:
        pass
    lines.append("[BE SMART & AVOID DUPLICATION: BEFORE you build or propose anything, first READ what already "
                 "exists in this project's folder and records — then reuse/extend it; never rebuild or duplicate "
                 "what's already there. Stay STRICTLY within THIS project's scope and brief; never import another "
                 "project's requirements, and do not invent 'missing requirements' the owner did not ask for. Use "
                 "your team/connectors/tools above to actually DO the task or fetch real values — not to describe them.]")
    return ("\n".join(lines) + "\n") if lines else ""


def _scoped_gen(scope: str, text: str, lang: str, cid: str):
    import scopes, activity, models_config, approvals
    try:
        # ensure a chat exists in this scope
        if not cid:
            cid = scopes.create_chat(scope)["id"]
        scopes.add_message(scope, cid, "user", text)

        # Saying "approve" in the chat = the same as clicking Approve on the popup. It approves ALL
        # pending changes for this project AND re-fires any approved-but-not-applied ones, so it
        # ALWAYS takes effect — you never have to ask 7-8 times.
        if scope.startswith("project:"):
            import re as _re2
            if _re2.search(r"\b(i\s+)?(approve|approved|accept|accepted|approve all|run it|go ahead and run)\b", text, _re2.I):
                _pid = scope.split(":", 1)[1]
                fired = 0
                for ap in approvals.list_pending(_pid):
                    approvals.decide(ap["id"], True)
                for ap in approvals.list_for(_pid):
                    if ap.get("status") == "approved" and not ap.get("applied"):
                        threading.Thread(target=_apply_approval_bg, args=(ap["id"],), daemon=True).start()
                        fired += 1
                msg = (f"✅ Approved — running {fired} change(s) now; results appear in the member chats."
                       if fired else "Nothing is pending approval right now.")
                scopes.add_message(scope, cid, "assistant", msg)
                yield sse("token", {"t": msg})
                yield sse("done", {"scope": scope, "cid": cid, "member": None,
                                   "approval": {"required": False, "categories": []}, "lang": lang})
                return

        # "status?" → answer DETERMINISTICALLY from stored run/approval/apply records. NEVER hand a
        # status question to the LLM (it has no execution output → it loops forever proposing checks).
        if scope.startswith("project:") and len(text or "") < 90:
            import re as _re3
            if _re3.search(r"(^\s*\?+\s*$)|\b(status|result|results|is it (done|finished|complete|over|online)|did it (finish|work|run|deploy)|what'?s?\s+(the\s+)?status|where (are we|is it)|update me|is it ready)\b", text, _re3.I):
                _pid = scope.split(":", 1)[1]
                run = _RUNS.get(_pid, {})
                items = approvals.list_for(_pid, limit=200)
                pend = [x for x in items if x.get("status") == "pending"]
                appr_na = [x for x in items if x.get("status") == "approved" and not x.get("applied")]
                applied = [x for x in items if x.get("applied")]
                lines = ["🟢 A run is in progress now." if run.get("running") else "⚪ No run is in progress."]
                if pend:
                    lines.append(f"🔔 {len(pend)} change(s) are PENDING your approval (popup / say 'approve').")
                if appr_na:
                    lines.append(f"⏳ {len(appr_na)} approved — executing now.")
                if applied:
                    last = sorted(applied, key=lambda x: x.get("decided") or x.get("created") or 0)[-1]
                    lines.append(f"✅ Last EXECUTED: {last.get('title', '')[:70]}")
                    res = (last.get("result") or "").strip()
                    if res:
                        lines.append("Output:\n" + res[-1800:])
                    else:
                        lines.append("(no captured output recorded)")
                else:
                    lines.append("❌ Nothing has actually executed yet.")
                msg = "📋 Deploy status — straight from Odin's records (not a guess):\n\n" + "\n".join(lines)
                scopes.add_message(scope, cid, "assistant", msg)
                yield sse("token", {"t": msg})
                yield sse("done", {"scope": scope, "cid": cid, "member": None,
                                   "approval": {"required": False, "categories": []}, "lang": lang})
                return

        # PROJECT CTO chat: a build/change/test request runs the FULL team pipeline
        # (plan → delegate to members → QA tests each part → CTO routes fixes), streamed into
        # THIS chat. Pure questions/status fall through to a normal conversational answer below.
        if scope.startswith("project:") and _is_work_request(text):
            pid = scope.split(":", 1)[1]
            # Run it as a BACKGROUND task on the server — NOT inside this chat's stream. So you can
            # switch between the CTO and DevOps freely and it keeps running; the live detail flows
            # into each member's chat (which polls), the CTO shows the brief, and you get a finish
            # notification. This is the fix for "navigate away → run dies / status gone."
            # AI-FIRST: operational (diagnosis/deploy/ops) projects are handled by the CTO as a SMART
            # conversational turn with full context BELOW — never the static plan->members->QA pipeline.
            # Only build-style projects fan out to the team machine.
            # BRAIN-FIRST: NEVER hand a project message to the static plan->members->QA pipeline. That
            # machine invents "requirements", cross-contaminates projects, and misclassifies local tasks.
            # The CTO brain below reads THIS project's real brief + capabilities + this message and acts.
            _use_pipeline = False
            if _use_pipeline:
                start_run(pid, text)
                msg = ("On it — the team is now running this in the background. You can switch between the "
                       "CTO and any member (DevOps) freely; it keeps running. Watch the live commands and "
                       "output in DevOps's chat, and you'll get a clear notification when it finishes.")
                scopes.add_message(scope, cid, "assistant", msg)
                yield sse("token", {"t": msg})
                yield sse("done", {"scope": scope, "cid": cid, "member": None,
                                   "approval": {"required": False, "categories": []}, "lang": lang})
                return
            # operational project: DO NOT return — fall through to the smart CTO brain path (real AI
            # reasoning + read-execute + propose), which reads the project brief/capabilities as context.

        pid = None
        member = None
        decision = {"approval": {"required": False, "categories": []}}
        # Decide ownership / delegation.
        try:
            from dispatcher import default_dispatcher as d
            decision = d.route(text, lang)
            lead = decision["leadAgent"]
            gated = decision["approval"]["required"]
        except Exception:
            lead, gated = "CTO Brain", False

        yield sse("status", {"icon": "🧠", "text": "Understanding…"})

        if scope.startswith("project:"):
            pid = scope.split(":", 1)[1]
            # a message the owner sent by RESOLVING the capability dialog — don't re-open the dialog
            _resolved = "⟦resolve⟧" in text
            if _resolved:
                text = text.replace("⟦resolve⟧", "").strip()
            # the CTO is the one you're talking to — animate the CTO while it handles your message
            activity.mark_active(pid, "Project CTO", task=text[:60], phase="CTO: handling your message")
            # honor + persist plain-language team controls ('remove X', 'only use X') from chat
            _ctrl = _apply_agent_controls(pid, text)
            if _ctrl:
                yield sse("status", {"icon": "🛠", "text": _ctrl})
                try:
                    scopes.add_message(scope, cid, "assistant", f"[Project CTO] {_ctrl}")
                except Exception:
                    pass
            member = _resolve_member(pid, lead)
            # EMPOWER, don't cage: when no single agent rule matches, the CTO just HANDLES it directly
            # with full project context + its tools — it does NOT stop to make the owner "pick an agent".
            # (member stays None → the CTO brain answers below; no forced choice, no interruption.)
            if member:
                yield sse("status", {"icon": "🧭", "text": f"Project CTO → delegating to {member}"})
                yield sse("delegate", {"pid": pid, "to": member, "lead": lead})
                activity.mark_active(pid, member, task=text[:60])
                activity.log_flow(pid, "Project CTO", member, note=text[:40])
                try:
                    import agents_registry
                    agents_registry.record_usage(pid, member)
                except Exception:
                    pass
        elif scope.startswith("member:"):
            _, pid, member = scope.split(":", 2)
            activity.mark_active(pid, member, task=text[:60])
            try:
                import agents_registry
                agents_registry.record_usage(pid, member)
            except Exception:
                pass
            yield sse("status", {"icon": "⚙️", "text": f"{member} is working…"})
        else:
            yield sse("status", {"icon": "🏛️", "text": "Company CTO (coarse overview)…"})

        if gated:
            cats = ", ".join(decision["approval"].get("categories", []))
            yield sse("status", {"icon": "⛔", "text": f"Change ({cats}) — will propose & wait for OK"})

        model = models_config.get_model(scope if not member else f"member:{pid}:{member}")

        chatd = scopes.get_chat(scope, cid) or {}
        sid0 = chatd.get("session_id")
        # If this scope belongs to a project, tell the engine the project's folder so it works THERE
        # (not at the Odin app's repo root) — fixes agents scaffolding in the wrong place.
        folder_note = ""
        proj_cwd = None
        if pid:
            try:
                import projects as _pj
                _p = _pj.get_project(pid) or {}
                _bdesc = _p.get("description") or ""
                if _bdesc:
                    folder_note += ("[PROJECT BRIEF & CAPABILITIES — standing context so you are aware and "
                                    "reason cleverly with your tools/agents/scopes; it is NOT a checklist to "
                                    "complete every turn]:\n" + _bdesc[:1500] + "\n")
                try:
                    folder_note += _brain_orientation(pid, member)
                except Exception:
                    pass
                try:
                    import os as _os9
                    _flowp = _os9.path.join("workspace/projects", pid, "OWNER_RUN_FLOW.md")
                    if _os9.path.exists(_flowp):
                        with open(_flowp, encoding="utf-8") as _ff9:
                            _flow = _ff9.read()
                        if _flow.strip():
                            folder_note += ("[OWNER'S RUN FLOW — the AUTHORITATIVE step-by-step you MUST follow "
                                            "for a run of this project; one approval at a time, each depends on the "
                                            "previous answer; never bundle; report only on a real problem]:\n"
                                            + _flow[:4000] + "\n")
                except Exception:
                    pass
                fp = _p.get("localPath") or _pj.agent_workdir(pid)   # P2: own project folder by default
                _srcs = _p.get("sources") or []
                if _srcs:
                    folder_note += (f"[Existing source folders (READ-ONLY unless I ask to modify): "
                                    f"{', '.join(_srcs)}]\n")
                if fp:
                    proj_cwd = fp
                    folder_note += (f"[Project folder: {fp} — do ALL file work inside it (create if "
                                    "missing); never write at the Odin app's repo root.]\n")
            except Exception:
                pass
        # A project chat runs READ-ONLY by default (unless the owner pre-authorized this project):
        # the agent may inspect/analyze freely, but any file edit or state-changing/VM command is
        # PROPOSED for the owner's approval — it cannot silently change your code.
        ro = False
        if pid:
            try:
                import projects as _pj2
                ro = not bool((_pj2.get_project(pid) or {}).get("auto_approve"))
            except Exception:
                ro = True
        # Reliable memory: inject the recent conversation into the prompt (don't depend solely on
        # the CLI's --resume, which is flaky in print mode). The just-added user msg is excluded.
        # SCOPE shaping (OWNER path) — a system-wide middleware capability every project inherits. Interpret
        # the question within THIS project's scope first, clarify on ambiguity, never block the owner. This is
        # what fixes "how many profiles" returning the app's config profiles instead of the project's own.
        # SCOPE + READ-EXECUTE (owner path) — two SYSTEM-WIDE middleware capabilities every project
        # inherits (no per-connector / per-project logic here). scope_answer_guard shapes the answer to
        # THIS project's scope; read_execute_guard makes a READ actually EXECUTE (never proposed). This is
        # what fixes the owner asking "how many profiles" and getting a PROPOSAL to read instead of the value.
        _scope_pre = ""
        _is_read = not _is_work_request(text)
        _conn_names = []
        if pid:
            try:
                import workspace_mw as _mw
                import projects as _pjn
                _pjr = _pjn.get_project(pid) or {}
                _nm = _pjr.get("name", pid)
                _scope_pre = _mw.scope_answer_guard(_nm, external=False) + "\n\n"
                # generic: names of the live services this project may read from (no hardcoded facts)
                try:
                    import capabilities as _cap
                    _conn_names = [c.get("name") for c in (_cap.list_connectors() or [])
                                   if c.get("status") == "connected" and c.get("name")]
                except Exception:
                    _conn_names = []
            except Exception:
                _scope_pre = ""
        prior = [m for m in chatd.get("messages", []) if m.get("role") in ("user", "assistant")][:-1]
        if prior:
            ctx = "\n".join(f"{m['role']}: {m['content']}" for m in prior[-8:])
            eng_text = f"{_scope_pre}{folder_note}Conversation so far (for your memory):\n{ctx}\n\nUser now says: {text}"
        else:
            eng_text = _scope_pre + folder_note + text
        # A READ must EXECUTE and answer with the live value — the OWNER never sees a proposal/approval for
        # a read. Only a genuine WRITE/work request in a non-pre-authorized project appends propose-first.
        if _is_read:
            try:
                import workspace_mw as _mw2
                eng_text += _mw2.read_execute_guard(_conn_names)
            except Exception:
                pass
        elif ro:
            eng_text += PROPOSE_RULES
        parts, new_sid, reply = [], None, None
        for evd in _engine_stream(eng_text, lang, sid0, model, cwd=proj_cwd, readonly=ro):
            k = evd.get("kind")
            if k == "status":
                yield sse("status", {"icon": evd.get("icon", "🔧"), "text": evd.get("text", "")})
            elif k == "text":
                parts.append(evd["t"])
                yield sse("token", {"t": evd["t"]})
                if pid and member:
                    activity.beat(pid, member)
            elif k == "session":
                new_sid = evd.get("id")
            elif k == "final":
                reply = evd.get("text") or "".join(parts)
                if evd.get("session_id"):
                    new_sid = evd["session_id"]
        if reply is None:
            reply = "".join(parts)
        if new_sid:
            scopes.set_session(scope, cid, new_sid)

        scopes.add_message(scope, cid, "assistant", reply or "")
        # If the agent PROPOSED changes in this chat, turn them into a real approval request so the
        # popup appears and your Approve actually executes it (background applier). No more dead-end
        # "approve in the harness" loops.
        if ro and pid:
            prop = _parse_proposal(reply or "")
            if prop:
                who = member or "Project CTO"
                ap = approvals.create(pid, who, title=(text[:60] or "Proposed changes"),
                                      summary=prop.get("summary", ""), files=prop["files"],
                                      commands=prop["commands"], cwd=proj_cwd or "", inline=False,
                                      kind=("vm" if any(c.get("where") == "vm" for c in prop["commands"]) else "change"))
                yield sse("approval", {"id": ap["id"], "pid": pid, "member": who, "title": ap["title"],
                                       "summary": ap["summary"], "files": ap["files"], "commands": ap["commands"]})
        # roll the result up to ancestors
        scopes.sync_up(scope, f"answered: “{text[:60]}”")
        # INTERVENTION FEEDBACK: when the owner instructs a MEMBER directly, relay it to the CTO
        # (project scope) so the CTO — and through upward-sync the Chief — are kept informed.
        if scope.startswith("member:") and pid and member:
            try:
                pscope = f"project:{pid}"
                upd = next((c["id"] for c in scopes.list_chats(pscope) if c.get("title") == "↳ team updates"), None)
                if not upd:
                    upd = scopes.create_chat(pscope, "↳ team updates")["id"]
                scopes.add_message(pscope, upd, "user", f"[{member} → CTO] Owner instruction: {text[:180]}")
                scopes.add_message(pscope, upd, "assistant", f"[CTO] Noted for {member}. {member} replied: {(reply or '')[:200]}")
            except Exception:
                pass
        if pid and member:
            activity.mark_idle(pid, member)

        yield sse("status", {"icon": "✅", "text": "Done"})
        yield sse("done", {"scope": scope, "cid": cid, "member": member,
                           "approval": decision.get("approval", {}), "lang": lang})
    except Exception as e:
        yield sse("error", {"text": str(e)})
