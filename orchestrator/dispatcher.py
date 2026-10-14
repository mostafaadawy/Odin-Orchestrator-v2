"""
Odin-Orchestrator — Brain ↔ Agent Dispatcher.

A LEAN, DETERMINISTIC router (per ADR-005 — explicitly NOT a swarm). It:
  1. classifies a request to the right specialist agent(s) using the triggers in the agent
     definitions (agents/*.agent.md),
  2. loads core-rules (memory) before doing anything,
  3. detects whether the request would touch code/config/VM and therefore needs the
     APPROVAL GATE,
  4. fires named lifecycle hooks (pre-rule-load, pre-approval, post-log),
  5. exposes `respond(text, lang)` so it can drop into the voice loop as the Brain — replacing
     the raw Ollama handler while preserving the same interface.

No external dependencies (stdlib only). Free-form answering reuses brain_handler.OllamaBrain.
"""
from __future__ import annotations

import os
import json
import pathlib
import datetime
from dataclasses import dataclass, field

ROOT = pathlib.Path(__file__).resolve().parent.parent  # Odin-Orchestrator/

# --- Agent registry: name -> trigger keywords (mirrors agents/*.agent.md) -----
AGENT_TRIGGERS: dict[str, list[str]] = {
    "Frontend": ["ui", "component", "screen", "styling", "layout", "client", "mobile ui",
                 "ux", "form", "dashboard view", "css", "react", "page"],
    "Backend": ["api", "endpoint", "service", "business logic", "integration", "webhook",
                "job", "billing", "payment", "auth backend", "subscription"],
    "DevOps & Cloud": ["azure", "vm", "server", "deploy", "release", "ssl", "certificate",
                        "nginx", "config", "port", "firewall", "dns", "ci/cd", "infra",
                        "environment", "systemd", "scp", "proxy"],
    "Security & Compliance": ["pii", "phi", "payment", "card", "auth", "authorization",
                              "encryption", "secret", "token", "compliance", "audit",
                              "vulnerability", "exposure", "hipaa", "pci"],
    "QA & Testing": ["test", "qa", "regression", "release", "bug", "verify", "coverage",
                     "ci check", "safe to ship"],
    "Database": ["schema", "table", "column", "migration", "index", "query", "orm",
                 "data model", "backup", "restore", "foreign key"],
}

# --- Actions that REQUIRE approval (mirrors config/system.config.json) ---------
APPROVAL_TRIGGERS: dict[str, list[str]] = {
    "deployment": ["deploy", "release to", "ship to prod", "rebuild service", "cutover"],
    "azure-vm-action": ["vm", "azure", "ssh", "serial console", "systemctl", "scp", "firewall",
                        "nsg", "restart service"],
    "code-change": ["change the code", "edit the", "modify the", "refactor", "patch", "fix the bug in"],
    "config-change": ["config", "environment variable", "change setting", "nginx", "proxy config"],
    "ssl-certificate": ["ssl", "tls", "certificate", "certbot"],
    "database-migration": ["migration", "alter table", "drop table", "schema change"],
    "security-scan-active": ["port scan", "active scan", "pentest", "fuzz"],
    "production-data-access": ["production data", "prod db", "live data", "customer data"],
    "sensitive-data-handling": ["card data", "card payment", "payment data", "store card",
                                "pan", "phi", "pii", "card number"],
    "dependency-install": ["install package", "pip install", "npm install", "add dependency"],
    "secret-or-credential-change": ["secret", "credential", "api key", "rotate key", "password"],
}

SENSITIVE = ["pii", "phi", "payment", "card", "secret", "credential", "production data"]

# Read-only intent vs. change intent — used to NOT gate harmless questions/inspections.
READONLY_HINTS = ("list", "show", "status", "read", "check", "display", "view", "what",
                  "which", "are we", "do we", "is it", "is the", "get ", "ls", "cat ",
                  "tail", "print", "describe", "tell me", "see ", "how many", "exists",
                  "do you", "did you", "connected", "info", "details",
                  "compare", "diff", "difference", " vs ", "versus", "inspect", "review")
CHANGE_HINTS = ("deploy", "restart", "reboot", "delete", "remove", "rm ", "update",
                "upgrade", "install", "rebuild", "build ", "write", "create", "modify",
                "edit", "stop ", "start ", "kill", "chmod", "chown", "mv ", "cp ", "scp",
                "push", "migrate", "drop", "truncate", "reset", "rotate", "apply", "add ",
                "grant", "revoke", "open port", "firewall", "systemctl", "sudo")
# Read-only is only allowed to bypass the gate for these infra categories — NEVER for data/secrets.
READ_BYPASS_CATEGORIES = {"azure-vm-action", "deployment", "config-change"}
# Hard safety floor: these ALWAYS require approval, even if the request looks read-only — no
# semantic guess can wave them through. (Everything else is decided by understanding the action.)
ALWAYS_GATE = {"secret-or-credential-change", "production-data-access",
               "sensitive-data-handling", "security-scan-active"}


# --- Lifecycle hooks ----------------------------------------------------------
@dataclass
class HookContext:
    text: str
    lang: str = "en"
    agents: list[str] = field(default_factory=list)
    approval: dict | None = None
    notes: list[str] = field(default_factory=list)
    fired: list[str] = field(default_factory=list)


HookFn = "callable"  # (HookContext) -> None


def _hook_load_rules(ctx: HookContext) -> None:
    """pre-rule-load: confirm core-rules is read before acting."""
    rules = ROOT / "workspace" / "shared" / "directions" / "core-rules.md"
    ctx.notes.append("rules-loaded" if rules.exists() else "rules-MISSING")
    ctx.fired.append("pre-rule-load")


def _hook_pre_approval(ctx: HookContext) -> None:
    """pre-approval: if the action is gated, mark that we must stop for approval."""
    if ctx.approval and ctx.approval.get("required"):
        ctx.notes.append("approval-gate:STOP")
    ctx.fired.append("pre-approval")


def _hook_post_log(ctx: HookContext) -> None:
    """post-log: append a routing decision to the audit log."""
    ctx.fired.append("post-log")


DEFAULT_HOOKS = [_hook_load_rules, _hook_pre_approval, _hook_post_log]


# --- The dispatcher -----------------------------------------------------------
class Dispatcher:
    def __init__(self, hooks: list | None = None, brain=None, audit: bool = True):
        self.hooks = hooks if hooks is not None else DEFAULT_HOOKS
        self.audit = audit
        self._brain = brain  # lazy: a brain_handler.OllamaBrain-like object with respond()

    # -- classification --
    @staticmethod
    def _mask_names(text: str) -> str:
        """Route by the ACTION, not by data. Folder/file/branch names, paths and quoted
        strings often contain words like 'frontend' or 'page' that have nothing to do with
        the task ('compare the FRONTEND folder on the vm' is DevOps, not a Frontend job).
        Blank those tokens out before keyword scoring so naming can't misroute."""
        import re
        t = text.lower()
        # quoted strings  → drop
        t = re.sub(r"[\"'`][^\"'`]+[\"'`]", " ", t)
        # the token right after called/named/file/folder/dir/branch/repo  → drop
        t = re.sub(r"\b(?:called|named|file|folder|dir|directory|branch|repo|path)\s+\S+", " ", t)
        # path-like and hyphenated compound name tokens (e.g. a-frontend, /home/x) → drop
        t = re.sub(r"\S*[/\\]\S*", " ", t)          # anything containing a slash
        t = re.sub(r"\b\w+-\w[\w-]*\b", " ", t)      # hyphenated compound names
        return t

    @staticmethod
    def classify(text: str) -> list[str]:
        t = Dispatcher._mask_names(text)
        scored = []
        for agent, kws in AGENT_TRIGGERS.items():
            hits = sum(1 for k in kws if k in t)
            if hits:
                scored.append((hits, agent))
        scored.sort(reverse=True)
        agents = [a for _, a in scored]
        # A task that touches a VM / server / remote folder is DevOps work no matter what the
        # folders are named — pin DevOps to the lead so naming never mislabels infra work.
        infra = ("azure", " vm ", "vm ", " vm", "server", "deploy", "/home/", "ssh", "nsg",
                 "systemd", "nginx", "remote", "production vm")
        if any(s in t for s in infra) or any(s in text.lower() for s in ("azure", "vm", "/home/")):
            if "DevOps & Cloud" in agents:
                agents.remove("DevOps & Cloud")
            agents.insert(0, "DevOps & Cloud")
        # Security is an automatic co-owner when sensitive data is involved (veto authority).
        if any(s in t for s in SENSITIVE) and "Security & Compliance" not in agents:
            agents.append("Security & Compliance")
        return agents or ["CTO Brain"]

    @staticmethod
    def approval_check(text: str) -> dict:
        t = text.lower()
        matched = [c for c, kws in APPROVAL_TRIGGERS.items() if any(k in t for k in kws)]
        readonly = any(h in t for h in READONLY_HINTS)
        change = any(h in t for h in CHANGE_HINTS)
        # A sensitive category triggers approval, EXCEPT a pure read-only request against an
        # infra category (list/show/status with no change verb) — those answer freely.
        pure_read = readonly and not change
        bypass_ok = bool(matched) and all(c in READ_BYPASS_CATEGORIES for c in matched)
        required = bool(matched) and not (bypass_ok and pure_read)
        return {"required": required, "categories": matched, "readOnly": bypass_ok and pure_read}

    # -- routing --
    def route(self, text: str, lang: str = "en") -> dict:
        ctx = HookContext(text=text, lang=lang)

        # PRIMARY: understand the request (local model). FALLBACK: deterministic keywords.
        sem = None
        if os.environ.get("ODIN_SEMANTIC_ROUTER", "1") == "1":
            try:   # P4e: Jev mode — local decider for specialist + read/change; fallback = the semantic router
                import jev_decider as _jd
                _ja = _jd.jev_choice("D2_agent", text)
                _jr = _jd.jev_choice("D2_action", text) if _ja else None
                if _ja and _jr:   # co-owners from the deterministic keyword rules (the local decider picks the lead)
                    _co = [a for a in self.classify(text) if a != _ja]
                    sem = {"agents": [_ja] + _co, "action": _jr, "why": "Jev mode: local decider"}
            except Exception:
                sem = None
            if sem is None:
                try:
                    import semantic_router
                    sem = semantic_router.classify(text)
                except Exception:
                    sem = None

        kw_approval = self.approval_check(text)        # keyword view (also the safety floor)
        if sem:
            ctx.agents = sem["agents"]
            # Security co-owns whenever sensitive data is involved, regardless of route.
            if any(s in text.lower() for s in SENSITIVE) and "Security & Compliance" not in ctx.agents:
                ctx.agents.append("Security & Compliance")
            hard = any(c in ALWAYS_GATE for c in kw_approval["categories"])
            required = (sem["action"] == "change") or hard
            ctx.approval = {"required": required,
                            "categories": kw_approval["categories"],
                            "readOnly": sem["action"] == "read" and not hard,
                            "intent": sem["action"], "why": sem.get("why", "")}
            ctx.notes.append("router:semantic")
        else:
            ctx.agents = self.classify(text)
            ctx.approval = kw_approval
            ctx.notes.append("router:keyword-fallback")

        for h in self.hooks:
            h(ctx)
        decision = {
            "request": text,
            "lang": lang,
            "agents": ctx.agents,
            "leadAgent": ctx.agents[0],
            "approval": ctx.approval,
            "hooksFired": ctx.fired,
            "notes": ctx.notes,
            "ts": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }
        if self.audit:
            self._log(decision)
        return decision

    def _log(self, decision: dict) -> None:
        try:
            line = json.dumps({
                "ts": decision["ts"], "type": "ROUTE", "ref": decision["leadAgent"],
                "actor": "Dispatcher",
                "summary": f"Routed to {', '.join(decision['agents'])}; "
                           f"approval={'YES('+','.join(decision['approval']['categories'])+')' if decision['approval']['required'] else 'no'}.",
            })
            # Routing telemetry goes to a SEPARATE file so the main audit log
            # (history/log.jsonl) stays reserved for significant decisions/changes.
            with open(ROOT / "workspace" / "history" / "routing.jsonl", "a") as f:
                f.write(line + "\n")
        except Exception:
            pass  # never let logging break routing

    # -- voice-loop adapter: same interface as brain_handler.OllamaBrain --
    def respond(self, text: str, lang: str = "en") -> str:
        d = self.route(text, lang)
        ar = str(lang).startswith("ar")

        if d["approval"]["required"]:
            # F-31: never an empty reason
            cats = (", ".join(d["approval"]["categories"]) or str(d["approval"].get("why") or "").strip()
                    or "it would change files or state")
            if ar:
                return (f"هذا الطلب يخص {d['leadAgent']} ويتطلب موافقتك أولاً "
                        f"({cats}). سأجهّز طلب موافقة بالتفاصيل قبل أي تنفيذ.")
            return (f"That's a {d['leadAgent']} task and it needs your approval first "
                    f"({cats}). I'll prepare an approval request with the exact steps before doing anything.")

        # No gate → answer with a clean LLM reply (routing is recorded in /dispatch + routing.jsonl,
        # so we do NOT clutter the spoken/chat reply with a "[Routed to ...]" label).
        brain = self._get_brain()
        try:
            return brain.respond(text, lang=lang)
        except Exception:
            if ar:
                return "تعذّر الوصول إلى النموذج المحلي حالياً."
            return "The local model is unavailable right now."

    def _get_brain(self):
        """The engine behind free-form answers. CORE design = Claude CLI (Claude Code on the
        project). Falls back to local Ollama only if the `claude` CLI isn't available, or if
        ODIN_ENGINE=ollama is set explicitly."""
        if self._brain is None:
            import sys
            sys.path.insert(0, str(ROOT / "server"))
            engine = os.environ.get("ODIN_ENGINE", "claude").lower()
            if engine == "claude":
                from claude_cli import ClaudeCLIBrain, available  # type: ignore
                if available():
                    self._brain = ClaudeCLIBrain()
                else:
                    from brain_handler import OllamaBrain  # type: ignore
                    self._brain = OllamaBrain()
            else:
                from brain_handler import OllamaBrain  # type: ignore
                self._brain = OllamaBrain()
        return self._brain


# Singleton used by the server.
default_dispatcher = Dispatcher()
