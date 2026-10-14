"""F-10 (owner 2026-10-12): after an audit violation, the audit PROPOSES a rule change; the owner approves.
NEVER automatic.

For every hard violation whose file was created by a known agent (G8 created_by), Odin creates ONE pending
'rule_change' approval: add a rule to that agent's 'Custom rules' that would have prevented it. Nothing in the
agent's capability.md changes until the owner approves. On approval the rule is ADDED (never replaces or
removes a rule — the 07-19 rule-loss lesson) as ONE logged batch, reversible with
`python server/rewrite_log.py revert <batch>`. Rejecting changes nothing."""
from __future__ import annotations
import re, pathlib

KIND = "rule_change"
RULES = {
    "duplicate": "Before creating a file, ask the middleware whether the capability already exists (shared/ or "
                 "another project); reuse it or add a delta — never copy another project's file.",
    "foreign-ref": "Never read or reference another project's private files; use the shared/ copy (ask the "
                   "middleware to promote it).",
    "dangling-ref": "Only reference files that exist; when a file moves to shared/, point to its new path.",
    "misplaced": "Write only into your project's canonical slots (code/, deploy/, tests/, files/) — never loose "
                 "files at the project root.",
    "external-write": "Never write outside the workspace and your project's declared folder.",
    "parallel-registry": "The database is the only registry — never create a parallel registry file "
                         "(projects.json-style lists).",
}


def _agent_of(label: str) -> str:
    a = (label or "").split(" (", 1)[0].strip()
    return "" if (not a or a == "unknown" or a.startswith("project ")) else a


def _pid_of(path: str) -> str:
    parts = pathlib.Path(str(path or "")).parts
    return parts[2] if len(parts) > 2 and parts[0] == "workspace" and parts[1] == "projects" else "company"


def _cap(agent: str) -> pathlib.Path:
    import agents_registry, workspace_mw as mw
    return mw.WS / "agents" / agents_registry._slug(agent) / "capability.md"


def has_rule(agent: str, rule: str) -> bool:
    p = _cap(agent)
    return p.exists() and rule.lower() in p.read_text(encoding="utf-8", errors="replace").lower()


def propose_from_issues(issues) -> list:
    """Create pending rule proposals (one per agent + rule). Returns the new approvals. Changes no rule."""
    import approvals
    out = []
    pending = {(a.get("rule_agent"), a.get("rule_text")) for a in approvals.list_pending(None) if a.get("kind") == KIND}
    for i in issues or []:
        rule = RULES.get(i.get("type"))
        if not rule:
            continue
        cb = i.get("created_by")
        pairs = list(cb.items()) if isinstance(cb, dict) else [(i.get("path"), cb)]
        for path, label in pairs:
            agent = _agent_of(label if isinstance(label, str) else "")
            if not agent or (agent, rule) in pending or has_rule(agent, rule) or not _cap(agent).exists():
                continue
            pending.add((agent, rule))
            a = approvals.create(_pid_of(path), agent, f"Rule for {agent}: prevent '{i.get('type')}'",
                                 summary=(f"The audit found a {i.get('type')} violation in {path} created by {agent}. "
                                          f"Approve to ADD this rule to {agent}'s Custom rules (nothing is removed): "
                                          f"\"{rule}\". Reject to change nothing."),
                                 kind=KIND)
            approvals.set_fields(a["id"], rule_agent=agent, rule_text=rule, rule_violation=i.get("type"),
                                 rule_path=str(path or ""))
            out.append(approvals.get(a["id"]))
    return out


def _add_rule(text: str, rule: str) -> str:
    line = f"- RULE: {rule}"
    lines = text.splitlines()
    for k, l in enumerate(lines):
        if re.match(r"^#+\s+custom rules", l.strip(), re.I):
            j = k + 1
            while j < len(lines) and not re.match(r"^#+\s", lines[j]):
                j += 1
            body = [x for x in lines[k + 1:j] if x.strip() not in ("- (none yet)", "- (none)")]  # placeholder only
            while body and not body[-1].strip():
                body.pop()
            return "\n".join(lines[:k + 1] + body + [line] + ([""] if j < len(lines) else []) + lines[j:]) + "\n"
    return text.rstrip("\n") + f"\n\n## Custom rules\n{line}\n"


def apply(aid: str) -> dict:
    """Owner approved: ADD the rule (one logged, reversible batch) and mark the approval applied."""
    import approvals, workspace_mw as mw
    a = approvals.get(aid) or {}
    if a.get("kind") != KIND or a.get("status") != "approved":
        return {"ok": False, "error": "not an approved rule proposal"}
    agent, rule = a.get("rule_agent", ""), a.get("rule_text", "")
    p = _cap(agent)
    if not p.exists():
        return {"ok": False, "error": f"no capability.md for {agent}"}
    with mw.rewrite_batch(f"F-10 add rule to {agent} (owner approved {aid})") as bid:
        before = p.read_text(encoding="utf-8")
        if rule.lower() not in before.lower():
            mw._apply_rewrite(p, before, _add_rule(before, rule), "", f"rule: {rule[:60]}")
    approvals.mark_applied(aid, f"rule added to {agent} (batch {bid})")
    return {"ok": True, "agent": agent, "rule": rule, "batch": bid}
