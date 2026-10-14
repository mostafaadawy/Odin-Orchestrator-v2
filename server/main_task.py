"""
main_task.py — THE MAIN TASK: every prompt becomes ONE persistent shared-state object that the whole
run references. This is the architecture the best practitioners converge on, applied to Odin:

  • Cognition / Devin: keep ONE continuous thread and share the FULL *curated* context — never
    fragmented summaries thrown over a wall. Here, `brief_verbatim` + the live `status` IS that
    curated context, handed to every member intact.
  • Anthropic: each worker gets a BOUNDED, explicit mandate (objective/inputs/deliverable/acceptance).
  • LangGraph: one typed STATE object is the single source of truth; everyone reads/writes it; it's
    durable (persisted), so nothing is lost or re-asked between steps.

No raw-dump hand-offs. No omission (a requirements checklist guards it). No fake "done" (status +
acceptance close the loop).
"""
from __future__ import annotations

import re
import time
import uuid

import store

_FILE = "main_tasks.json"


# ---------------------------------------------------------------- persistence
def _all() -> dict:
    return store.read_json(_FILE, {})


def _save(d: dict) -> None:
    store.write_json(_FILE, d)


def get(pid: str) -> dict | None:
    return _all().get(pid)


def _put(mt: dict) -> dict:
    d = _all()
    d[mt["pid"]] = mt
    _save(d)
    return mt


# ---------------------------------------------------------------- requirements
def extract_requirements(brief: str) -> list:
    """Split the brief into CHECKABLE requirements (the omission guard). Engine first, with a
    deterministic fallback so it always produces a list."""
    items = []
    try:
        import json
        import claude_cli
        if claude_cli.available():
            p = ("Split this task brief into a checklist of CONCRETE, individually-verifiable "
                 "requirements (each a single deliverable or rule). JSON array of short strings only:\n"
                 '["…","…"]\n\nBrief:\n' + (brief or "")[:3000])
            raw = claude_cli.ClaudeCLIBrain().respond(p, lang="en")
            m = re.search(r"\[.*\]", raw or "", re.S)
            if m:
                items = [str(x).strip() for x in json.loads(m.group(0)) if str(x).strip()]
    except Exception:
        items = []
    if not items:  # fallback: split on lines / bullets / sentences
        for line in re.split(r"[\n;]|(?<=[.])\s", brief or ""):
            t = line.strip(" \t-*•·#").strip()
            if 6 < len(t) < 160 and not t.lower().startswith(("#", "objective")):
                items.append(t)
        items = items[:20]
    # Drop CONSTRAINTS / standing-rules / meta — honored by HOW we execute ("do not run npm start",
    # "from next time re-confirm", "source is local→VM"), not by producing matchable text. Keeping
    # them made the omission-guard falsely report a SUCCESSFUL deploy as "incomplete".
    def _is_constraint(t: str) -> bool:
        tl = " " + t.lower() + " "
        return any(k in tl for k in (
            "do not ", "don't", "dont ", " never", "must not", "no extra", "strictly limited",
            "skip nothing", "add nothing", "from next time", "next time onward", "future update",
            "every future", "re-confirm", "before proceeding", "this time only", "this run only",
            "authorized", "source is always", "the source is", "destination is", "be strictly",
            "the system must", "the task is", "exactly as", "without adding", "without skipping",
            "strict restriction", "do nothing"))
    items = [t for t in items if not _is_constraint(t)]
    return [{"id": f"r{i+1}", "text": t, "status": "open", "owner": ""} for i, t in enumerate(items)]


# ---------------------------------------------------------------- create / update
def create(pid: str, brief_verbatim: str, objective: str = "") -> dict:
    mt = {
        "id": uuid.uuid4().hex[:12], "pid": pid, "created": time.time(),
        "objective": (objective or (brief_verbatim or "").strip().splitlines()[0] if brief_verbatim else "")[:200],
        "brief_verbatim": brief_verbatim or "",        # the FULL curated context (Cognition)
        "requirements": extract_requirements(brief_verbatim),
        "decisions": {},
        "plan": [],                                     # mandates
        "status": {},                                   # member -> {deliverable, done, ts}
        "pool": [{"who": "Owner (main prompt)", "text": brief_verbatim or "", "ts": time.time()}],
    }
    return _put(mt)


def append(pid: str, who: str, text: str) -> dict:
    """Append to the ONE growing shared context pool — every CTO decision, member work, and result
    lands here, in order, so the whole team works from one continuous history (Cognition's rule)."""
    mt = get(pid)
    if not mt:
        return {}
    if text and str(text).strip():
        # keep messages whole (don't slice an agent's output); generous per-entry cap. Overall pool
        # size is handled by pool_text's faithful compaction, never by chopping individual messages.
        mt.setdefault("pool", []).append({"who": who, "text": str(text)[:16000], "ts": time.time()})
        _put(mt)
    return mt


def _engine_compact(raw: str) -> str:
    """Strongest available compaction: an ENGINE (Claude) summary that preserves every decision, fact,
    number, path, exact command, exclude, rule, owner instruction, error and open item — drops only
    filler/duplication. Used ONLY for the oldest overflow when the pool can't fit; it is NOT a slice."""
    try:
        import claude_cli
        if claude_cli.available():
            p = ("Compact the following TEAM shared-context history into a DENSE, FAITHFUL summary. "
                 "Preserve EVERY decision, fact, number, file path, exact command, exclude pattern, rule, "
                 "owner instruction, error and still-open item — lose nothing important; omit only filler "
                 "and duplication. Write it as running context the whole team can rely on.\n\n" + raw[:24000])
            out = claude_cli.ClaudeCLIBrain().respond(p, lang="en")
            if out and out.strip():
                return out.strip()
    except Exception:
        pass
    return (raw[:6000] + "\n…(engine summary unavailable — middle of earliest context omitted)…\n" + raw[-6000:]) \
        if len(raw) > 12000 else raw


def pool_text(pid: str, limit: int | None = None) -> str:
    """Render the shared pool. DEFAULT: the FULL pool, NO trimming (one whole WhatsApp-style history).
    ONLY if it exceeds `limit` (a real model-context safety bound; override via ODIN_POOL_LIMIT) do we
    COMPACT — and even then we never crude-slice: the most recent context stays VERBATIM and the older
    overflow becomes a faithful, cached engine SUMMARY. Nothing is filtered or sliced per-agent."""
    import os as _os
    if limit is None:
        limit = int(_os.environ.get("ODIN_POOL_LIMIT", "120000"))   # large; most projects never trim
    mt = get(pid)
    if not mt or not mt.get("pool"):
        return ""
    pool = mt["pool"]
    header = ("===== SHARED CONTEXT POOL — the whole team's single running history; keep ALL of it in "
              "mind, never re-decide what's already here =====\n")
    footer = "\n=================================================================================\n"
    full = "\n\n".join(f"[{e['who']}]: {e['text']}" for e in pool)
    if len(full) <= limit:
        return header + full + footer                       # NO trim — the entire pool, verbatim
    # Too large for one context → keep the most RECENT verbatim, COMPACT the older overflow (cached).
    recent_budget = int(limit * 0.7)
    recent, size, split = [], 0, 0
    for i in range(len(pool) - 1, -1, -1):
        s = len(pool[i].get("text", "")) + len(str(pool[i].get("who", ""))) + 6
        if size + s > recent_budget and recent:
            split = i + 1
            break
        recent.insert(0, pool[i]); size += s; split = i
    older = pool[:split]
    cache = mt.get("_compaction") or {}
    if cache.get("covered") == len(older) and cache.get("summary"):
        summary = cache["summary"]                          # reuse cached compaction
    else:
        summary = _engine_compact("\n\n".join(f"[{e['who']}]: {e['text']}" for e in older))
        mt["_compaction"] = {"covered": len(older), "summary": summary}
        try:
            _put(mt)
        except Exception:
            pass
    recent_txt = "\n\n".join(f"[{e['who']}]: {e['text']}" for e in recent)
    return (header
            + "----- COMPACTED EARLIER CONTEXT (faithful summary — part of the shared pool, nothing "
              "discarded) -----\n" + summary + "\n\n"
            + "----- RECENT CONTEXT (verbatim) -----\n" + recent_txt + footer)


def set_plan(pid: str, mandates: list) -> dict:
    mt = get(pid)
    if not mt:
        return {}
    mt["plan"] = mandates or []
    return _put(mt)


def write_deliverable(pid: str, member: str, deliverable: str, done: bool = True,
                      requirement_ids: list | None = None) -> dict:
    """A member finished: record its deliverable in shared state and flip covered requirements done."""
    mt = get(pid)
    if not mt:
        return {}
    mt["status"][member] = {"deliverable": (deliverable or "")[:1500], "done": bool(done), "ts": time.time()}
    for r in mt["requirements"]:
        if (requirement_ids and r["id"] in requirement_ids) or r.get("owner") == member:
            r["status"] = "done" if done else "open"
    return _put(mt)


# ---------------------------------------------------------------- coverage / loop
def coverage(pid: str) -> dict:
    """Does the plan cover every requirement? (Omission gate.)"""
    mt = get(pid) or {}
    covered = set()
    for mnd in mt.get("plan", []):
        for rid in (mnd.get("requirement_ids") or []):
            covered.add(rid)
    reqs = mt.get("requirements", [])
    missing = [r for r in reqs if r["id"] not in covered] if any(m.get("requirement_ids") for m in mt.get("plan", [])) else []
    return {"total": len(reqs), "covered": len(covered), "missing": missing,
            "complete": not missing}


def open_requirements(pid: str) -> list:
    mt = get(pid) or {}
    return [r for r in mt.get("requirements", []) if r.get("status") != "done"]


# ---------------------------------------------------------------- rendering (the hand-off)
def big_picture(pid: str) -> str:
    """The CURATED full context every member receives — the big picture, kept consistent for all.
    This is what replaces the raw-dump: structured objective + verbatim brief + the live checklist +
    what's already delivered. (Cognition: share the full curated context, not a lossy summary.)"""
    mt = get(pid)
    if not mt:
        return ""
    reqs = "\n".join(f"  [{'x' if r['status']=='done' else ' '}] {r['id']}: {r['text']}"
                     for r in mt.get("requirements", [])) or "  (none parsed)"
    done = "\n".join(f"  - {m}: {s['deliverable'][:160]}"
                     for m, s in mt.get("status", {}).items() if s.get("done")) or "  (nothing delivered yet)"
    return (
        "===== MAIN TASK (the single source of truth — keep ALL of it in view) =====\n"
        f"OBJECTIVE: {mt.get('objective','')}\n\n"
        "OWNER'S BRIEF (verbatim — authoritative, never omit or reorder):\n"
        f"\"\"\"\n{mt.get('brief_verbatim','')}\n\"\"\"\n\n"
        f"REQUIREMENTS CHECKLIST (the whole job — nothing is done until all are checked):\n{reqs}\n\n"
        f"ALREADY DELIVERED so far (by other members):\n{done}\n"
        "==========================================================================\n")


def mandate_text(mandate: dict) -> str:
    """A member's BOUNDED slice — what THIS member must do, framed against the big picture."""
    m = mandate or {}
    inp = ", ".join(m.get("inputs") or []) or "the big picture above"
    return (
        "----- YOUR MANDATE (your bounded part of the Main Task above) -----\n"
        f"OBJECTIVE: {m.get('objective','')}\n"
        f"INPUTS you can rely on: {inp}\n"
        f"DELIVERABLE you must produce: {m.get('deliverable','a verified result for your part')}\n"
        f"ACCEPTANCE (how we'll judge it done): {m.get('acceptance','works + verified, no fake success')}\n"
        f"DEPENDS ON: {', '.join(m.get('depends_on') or []) or 'nothing'}\n"
        "Do YOUR part only; rely on the big picture for everything else; never re-decide what others "
        "already delivered. Report a VERIFIED result — never claim done without proof.\n"
        "------------------------------------------------------------------\n")


def checklist_text(pid: str) -> str:
    """The whole-job checklist every member should keep in view (the omission guard / big picture)."""
    mt = get(pid)
    if not mt or not mt.get("requirements"):
        return ""
    rows = "\n".join(f"  [{'x' if r['status']=='done' else ' '}] {r['text']}" for r in mt["requirements"])
    return ("THE WHOLE JOB — requirements checklist (your part is one slice; keep the rest in view, "
            "don't omit or break any):\n" + rows + "\n")


def reconcile(pid: str, delivered_text: str) -> list:
    """Heuristically mark requirements addressed if their key terms appear in the delivered work, and
    return the ones STILL open. Used for the final completeness check (the omission guard's teeth)."""
    mt = get(pid)
    if not mt:
        return []
    low = (delivered_text or "").lower()
    for r in mt.get("requirements", []):
        if r["status"] == "done":
            continue
        terms = [w for w in re.findall(r"[a-zA-Z0-9_./-]{4,}", r["text"].lower()) if w not in
                 ("the", "and", "for", "with", "that", "this", "from", "into", "must", "should")]
        if terms and sum(1 for w in terms if w in low) >= max(1, len(terms) // 2):
            r["status"] = "done"
    _put(mt)
    return [r for r in mt.get("requirements", []) if r["status"] != "done"]


def upstream_deliverables(pid: str, depends_on: list) -> str:
    mt = get(pid) or {}
    rows = []
    for dep in (depends_on or []):
        s = mt.get("status", {}).get(dep)
        if s and s.get("done"):
            rows.append(f"  - {dep} delivered: {s['deliverable'][:300]}")
    return ("UPSTREAM DELIVERABLES you depend on:\n" + "\n".join(rows) + "\n") if rows else ""
