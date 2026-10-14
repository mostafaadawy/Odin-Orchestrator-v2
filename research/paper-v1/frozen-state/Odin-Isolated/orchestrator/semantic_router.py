"""
Semantic router — understand the INTENT of a request instead of counting keywords.

Why this exists: a hand-coded keyword scorer is brittle. Every new phrasing ("compare",
"sync", "is X up", a folder literally named 'frontend') needs another keyword or another
regex — endless whack-a-mole. Instead we ask the local model (qwen via Ollama: offline, free,
no API key) to read the request the way a smart engineer would and return a tiny structured
decision. It generalizes to wording we never anticipated.

This is ADVISORY for the label + a hint for the gate. It is NOT the safety authority: the
deterministic gate in dispatcher.py remains the floor (secrets/data/db always gated; pure
reads never gated). If the model is unavailable, the dispatcher falls back to keywords.
"""
from __future__ import annotations

import os
import json
import urllib.request

OLLAMA_URL = os.environ.get("ODIN_OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("ODIN_ROUTER_MODEL",
                              os.environ.get("ODIN_OLLAMA_MODEL", "qwen2.5:7b-instruct-q4_K_M"))

AGENTS = ["Frontend", "Backend", "DevOps & Cloud", "Security & Compliance",
          "QA & Testing", "Database", "CTO Brain"]

# One careful instruction beats a hundred keywords. The model routes by what the task DOES.
SYSTEM = (
    "You are the router for a CTO orchestration system. Read the user's request and decide, "
    "like an experienced engineer, (1) which specialist OWNS the work and (2) whether the task "
    "only READS/inspects state or would CHANGE it.\n\n"
    "Specialists:\n"
    "- Frontend: UI/UX, components, styling, client screens, web pages.\n"
    "- Backend: APIs, services, business logic, integrations, jobs, billing logic.\n"
    "- DevOps & Cloud: anything on a server or VM (Azure), deploys, infra, files/folders ON a "
    "remote machine, comparing local vs server, nginx, systemd, certificates, networking.\n"
    "- Security & Compliance: secrets, keys, auth, encryption, PII/PHI/cards, audits, exposure.\n"
    "- QA & Testing: tests, regressions, verification, 'is it safe to ship'.\n"
    "- Database: schema, tables, migrations, queries, backups.\n"
    "- CTO Brain: strategy, planning, or anything that fits none of the above.\n\n"
    "CRITICAL — route by the ACTION, not by names. Words inside a file/folder/branch/repo NAME "
    "(e.g. a folder literally called 'app-frontend' or 'payments') do NOT decide the owner. "
    "Comparing/listing/reading folders on the VM is DevOps + read, even if a folder is named "
    "'frontend'. Editing UI source code is Frontend + change.\n\n"
    "action = 'read' if it only inspects (compare, diff, list, show, status, read, check, is-it-up). "
    "action = 'change' if it would deploy, restart, write, edit, install, migrate, delete, rotate, "
    "or modify ANY state. If genuinely unsure, say 'change' (safer).\n\n"
    "Reply with ONLY compact JSON, no prose:\n"
    '{"agent":"<one specialist>","secondary":["<optional others>"],"action":"read|change","why":"<=8 words"}'
)


def classify(text: str, timeout: float | None = None) -> dict | None:
    """Return {'agents':[...], 'action':'read'|'change', 'why':..} or None if unavailable."""
    timeout = timeout if timeout is not None else float(os.environ.get("ODIN_ROUTER_TIMEOUT", "12"))
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "format": "json",          # ask Ollama to constrain output to valid JSON
        "options": {"temperature": 0, "num_predict": 120},
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": text},
        ],
    }
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        raw = (data.get("message", {}) or {}).get("content", "").strip()
        parsed = json.loads(raw)
    except Exception:
        return None  # model down / bad JSON → caller falls back to deterministic keywords

    agent = parsed.get("agent")
    if agent not in AGENTS:
        # tolerate near-misses ("DevOps", "devops & cloud")
        agent = next((a for a in AGENTS if a.lower().split(" &")[0] in str(agent).lower()), None)
    if not agent:
        return None
    agents = [agent]
    for s in (parsed.get("secondary") or []):
        m = next((a for a in AGENTS if a.lower().split(" &")[0] in str(s).lower()), None)
        if m and m not in agents:
            agents.append(m)
    action = "change" if str(parsed.get("action", "")).lower().startswith("chang") else "read"
    return {"agents": agents, "action": action, "why": parsed.get("why", "")}
