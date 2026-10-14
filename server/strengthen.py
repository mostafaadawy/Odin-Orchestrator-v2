"""G13 — strengthen a reused agent (add a skill, delete nothing), only after the owner approves.

When the intake readiness says a project NEEDS a platform/service the team has not used ("by": "connector",
"status": "needs"), Odin proposes ONE approval per platform: add "<platform>" to the Skills of the project's
builder agent. Nothing changes until the owner approves. On approval the skill is ADDED to the agent's shared
capability.md (title, description, other skills and rules untouched) and to this project's roster, as ONE
logged batch — reversible with `python server/rewrite_log.py revert <batch>`."""
import re
import pathlib

KIND = "strengthen"
_BUILDERS = ("Fullstack", "Backend", "Frontend", "Mobile", "Data")


def platform_of(item: str) -> str:
    s = str(item or "").strip()
    s = re.split(r"\s+\(|\s+—\s+|\s+-\s+|:\s", s, maxsplit=1)[0].strip()
    return s[:80]


def pick_agent(pid: str) -> str:
    """The project's builder: Fullstack first, then another building role; never an operator."""
    import agents_registry
    names = [a["name"] for a in agents_registry.list_agents(pid)]
    for b in _BUILDERS:
        for n in names:
            if n.lower() == b.lower():
                return n
    for a in agents_registry.list_agents(pid):
        if (a.get("nature") or "technical") == "technical" and a["name"] not in ("QA", "Security", "DevOps"):
            return a["name"]
    return ""


def _cap(name: str) -> pathlib.Path:
    import agents_registry, workspace_mw as mw
    return mw.WS / "agents" / agents_registry._slug(name) / "capability.md"


def already_has(name: str, platform: str) -> bool:
    p = _cap(name)
    return p.exists() and platform.lower() in p.read_text(encoding="utf-8", errors="replace").lower()


def propose_from_readiness(pid: str, readiness) -> list:
    """Create one pending 'strengthen' approval per new platform. Returns the created approvals."""
    import approvals
    out, seen = [], set()
    agent = pick_agent(pid)
    if not agent:
        return out
    for r in readiness or []:
        if not isinstance(r, dict):
            continue
        if str(r.get("status", "")).lower() != "needs" or str(r.get("by", "")).lower() != "connector":
            continue
        plat = platform_of(r.get("item", ""))
        if not plat or plat.lower() in seen or already_has(agent, plat):
            continue
        seen.add(plat.lower())
        a = approvals.create(pid, agent, f"Strengthen {agent}: add skill \"{plat}\"",
                             summary=(f"This project needs {plat}, which {agent} has not used before. Approve to ADD "
                                      f"\"{plat}\" to {agent}'s skills (shared). Nothing is removed. "
                                      f"Reason: {str(r.get('need') or r.get('item'))[:300]}"),
                             kind=KIND)
        approvals.set_fields(a["id"], strengthen_agent=agent, strengthen_skill=plat)
        out.append(approvals.get(a["id"]))
    return out


def apply(aid: str) -> dict:
    """Owner approved: add the skill (additive), log it as one batch, mark the approval applied."""
    import approvals, agents_registry, workspace_mw as mw
    a = approvals.get(aid) or {}
    if a.get("kind") != KIND:
        return {"ok": False, "error": "not a strengthen approval"}
    agent, skill, pid = a.get("strengthen_agent", ""), a.get("strengthen_skill", ""), a.get("pid", "")
    p = _cap(agent)
    with mw.rewrite_batch(f"G13 strengthen {agent}: add skill '{skill}' (owner approved {aid})") as bid:
        if p.exists():
            before = p.read_text(encoding="utf-8")
            agents_registry._merge_skill_file(p, {"skills": [skill]})
            after = p.read_text(encoding="utf-8")
            if after != before:
                p.write_text(before, encoding="utf-8")            # write through the logged path
                mw._apply_rewrite(p, before, after, "", f"skill: {skill}")
        roster = agents_registry.list_agents(pid)
        for r in roster:
            if r["name"].lower() == agent.lower() and skill not in r.get("skills", []):
                r.setdefault("skills", []).append(skill)
        agents_registry._save(pid, roster)
    approvals.mark_applied(aid, f"skill '{skill}' added to {agent} (batch {bid})")
    return {"ok": True, "agent": agent, "skill": skill, "batch": bid}
