"""
General external API (the single anchor/access layer).

External systems (and future mobile apps) reach any project by its IDENTIFIER (the project id),
send a prompt, and get a smart response built from that project's brief + shared context.

  GET  /api/v1/health
  GET  /api/v1/projects                       -> [{identifier, name, type, description}]
  POST /api/v1/p/{identifier}/ask  {prompt}   -> {answer}   (routed to that project's brain)

Auth: header `X-API-Key` must match ODIN_API_KEY (from workspace/shared/oth/.cred) when that key is set; if it isn't
set yet, local/dev requests are allowed (so it works out-of-the-box on localhost).

Base URL is configurable — it's just where this router is mounted (localhost now; point a tunnel or
the Azure VM at it later). No deploy/orchestration code is touched by this module.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel


class AskIn(BaseModel):
    prompt: str
    lang: str = "en"


def _api_key() -> str:
    try:
        from integrations import cred
        return cred.get("ODIN_API_KEY", "")
    except Exception:
        return ""


def _check_key(provided: str | None):
    want = _api_key()
    if want and (provided or "") != want:
        raise HTTPException(401, "invalid or missing X-API-Key")


def build_router() -> APIRouter:
    r = APIRouter(prefix="/api/v1", tags=["external"])

    @r.get("/health")
    def health():
        return {"ok": True, "service": "odin-external-api", "auth_required": bool(_api_key())}

    @r.get("/projects")
    def projects_list(x_api_key: str | None = Header(default=None)):
        _check_key(x_api_key)
        import projects
        return {"projects": [{"identifier": p["id"], "name": p.get("name"), "type": p.get("type"),
                              "description": (p.get("description") or "")[:200]}
                             for p in projects.list_projects()]}

    @r.post("/p/{identifier}/ask")
    def ask(identifier: str, body: AskIn, x_api_key: str | None = Header(default=None)):
        _check_key(x_api_key)
        import projects
        proj = projects.get_project(identifier)
        if not proj:
            raise HTTPException(404, f"no project with identifier '{identifier}'")
        # build the project's context so the answer is grounded in THIS project's data/capabilities
        ctx = f"PROJECT: {proj.get('name')} ({identifier}) — type {proj.get('type')}.\n"
        ctx += f"BRIEF: {(proj.get('description') or '')[:1500]}\n"
        try:
            import main_task
            pool = main_task.pool_text(identifier, limit=4000)
            if pool:
                ctx += f"\nSHARED CONTEXT:\n{pool}\n"
        except Exception:
            pass
        prompt = (f"{ctx}\nA user is asking about this project via the external API. Answer smartly and "
                  f"concisely using the project's data/capabilities.\n\nQUESTION: {body.prompt}")
        answer = "(engine unavailable)"
        try:
            from dispatcher import default_dispatcher as d
            answer = d.respond(prompt, lang=body.lang)
        except Exception as e:
            answer = f"(engine error: {e})"
        return {"identifier": identifier, "answer": answer}

    return r
