"""F-43 — give an agent its FULL rules, not only the first 900 characters of its capability.md.

Setting  agent_rules_mode:
  "full"       (v2 DEFAULT) the prompt gets the 900-character capability excerpt AS BEFORE, plus a rules block with
               every 'Must honor' and 'Custom rules' line from the agent's capability.md, capped at CAP characters.
  "legacy900"  exactly the old behaviour (900-character excerpt only, no rules block) — used for the PAPER v1
               reproduction check so paper v1's measurements can be reproduced exactly (paper protection rule PP-7).
Precedence: environment ODIN_AGENT_RULES_MODE  >  data/agent_rules.json {"mode": ...}  >  "full".

Cap: CAP = 6000 characters for the rules block. Filled in priority order: ALL 'Must honor' lines first, then
'Custom rules' lines; cut only at whole lines. If anything is cut, the block says how many lines were not shown
and a 'rules-truncated' record is appended to workspace/history/audit-log.jsonl (agent, shown, total, cap)."""
import os, re, json, pathlib, datetime

CAP = 6000
MODES = ("full", "legacy900")
ROOT = pathlib.Path(__file__).resolve().parent.parent
SETTINGS = ROOT / "data" / "agent_rules.json"
PLACEHOLDERS = {"- (none yet)", "- (none)"}


def mode() -> str:
    m = os.environ.get("ODIN_AGENT_RULES_MODE", "").strip().lower()
    if m in MODES:
        return m
    try:
        m = str(json.loads(SETTINGS.read_text()).get("mode", "")).lower()
        if m in MODES:
            return m
    except Exception:
        pass
    return "full"


def set_mode(m: str) -> str:
    if m not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps({"mode": m}))
    return m


def extract(text: str) -> dict:
    """All 'Must honor' and 'Custom rules' lines (every occurrence, incl. restored charter/merged sections)."""
    must, custom, sec, seen = [], [], None, set()
    for line in (text or "").splitlines():
        h = re.match(r"^(#+)\s+(.*)$", line)
        if h:
            t = h.group(2).strip().lower()
            sec = "must" if t.startswith("must honor") else ("custom" if t.startswith("custom rules") else None)
            continue
        s = line.rstrip()
        if not sec or not s.strip() or s.strip() in PLACEHOLDERS:
            continue
        key = re.sub(r"^\s*-\s*(RULE:\s*)?", "", s).strip().lower()
        if key in seen:                       # '- RULE: x' duplicates of '- x' and repeats across sections
            continue
        seen.add(key)
        (must if sec == "must" else custom).append(re.sub(r"^(\s*-\s*)RULE:\s*", r"\1", s))
    return {"must_honor": must, "custom_rules": custom}


def block(agent: str, cap_text: str) -> str:
    """The rules block for the prompt ('' in legacy900 mode or when the agent has no rules)."""
    if mode() != "full":
        return ""
    r = extract(cap_text)
    lines = [("must", l) for l in r["must_honor"]] + [("custom", l) for l in r["custom_rules"]]
    if not lines:
        return ""
    out, used, shown = [], 0, 0
    head = {"must": "Must honor:", "custom": "Custom rules:"}
    cur = None
    for kind, l in lines:
        add = ([head[kind]] if kind != cur else []) + [l]
        size = sum(len(x) + 1 for x in add)
        if used + size > CAP:
            break
        out += add; used += size; shown += 1; cur = kind
    total = len(lines)
    text = "### YOUR RULES — you MUST follow every one (from your capability.md):\n" + "\n".join(out)
    if shown < total:
        text += f"\n[… {total - shown} more rule line(s) not shown (cap {CAP} characters) — read your capability.md]"
        try:
            log = ROOT / "workspace" / "history" / "audit-log.jsonl"
            with open(log, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"ts": datetime.datetime.now().isoformat(), "type": "rules-truncated",
                                     "agent": agent, "shown": shown, "total": total, "cap": CAP}) + "\n")
        except Exception:
            pass
    return text
