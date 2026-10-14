#!/usr/bin/env python3
"""PreToolUse hook for Claude Code — OWNER-SCOPE WRITE RULE for agents (P2). Same mechanism as readonly_hook.py.

Rule (no new rules — it reuses workspace_mw.route, the middleware's own placement logic):
  • agents may READ anywhere (including shared bases);
  • agents WRITE only inside their OWN project folder (workspace/projects/<pid>/… incl. delta files that point
    to shared) or the project's own working folder (localPath), plus OS temp/scratch;
  • a write into the own project but to a NON-canonical slot is REDIRECTED to the slot workspace_mw.route picks;
  • writes to workspace/shared/** go ONLY through the door (server/door_cli.py promote …), never a raw write;
  • writes into ANOTHER project, the Odin repo root, or anywhere else are blocked.
Mode (env ODIN_SCOPE_HOOK): "watch" = never block, only log what WOULD be redirected/blocked; "enforce" = block
(exit 2, with the corrected path / the door command in the message so the agent retries correctly); "off".
Every decision other than plain-allow is appended to workspace/history/scope-hook.jsonl."""
import sys, os, json, re, shlex, time, pathlib

MODE = os.environ.get("ODIN_SCOPE_HOOK", "enforce").lower()
ROOT = pathlib.Path(os.environ.get("ODIN_ROOT") or pathlib.Path(__file__).resolve().parent.parent).resolve()
WS = ROOT / "workspace"
ACTOR = os.environ.get("ODIN_ACTOR_PID", "").strip()
WORKDIR = os.environ.get("ODIN_ACTOR_WORKDIR", "").strip()
TMP_PREFIXES = ["/tmp/", "/private/tmp/", "/var/folders/", "/private/var/folders/", "/var/tmp/", "/dev/"]
if os.environ.get("TMPDIR"):
    TMP_PREFIXES.append(os.path.realpath(os.environ["TMPDIR"]).rstrip("/") + "/")
DOOR = f"python3 {ROOT / 'server' / 'door_cli.py'}"


def _log(rec):
    try:
        (WS / "history").mkdir(parents=True, exist_ok=True)
        with open(WS / "history" / "scope-hook.jsonl", "a") as f:
            f.write(json.dumps({"ts": time.time(), "mode": MODE, "actor": ACTOR, **rec}) + "\n")
    except Exception:
        pass


def _abs(p, cwd):
    p = os.path.expanduser(str(p).strip().strip("'\""))
    if not os.path.isabs(p):
        p = os.path.join(cwd or os.getcwd(), p)
    return os.path.realpath(p)


_HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n.*?\n\s*\2\s*(?:\n|$)", re.S)
_OPS = {"&&", "||", ";", "|", "&", ";;", "(", ")", "\n"}


def _strip_heredocs(cmd):
    """Drop heredoc BODIES (code/text fed on stdin is data, not a write target); keep the command line."""
    return _HEREDOC.sub(lambda m: m.group(0).split("\n", 1)[0] + "\n", cmd)


def _bash_targets(cmd, cwd):
    """Best-effort write targets of a shell command, quote-aware: > / >> redirections, tee, mkdir, touch,
    cp/mv/install dest. Quoted text, fd duplications (2>&1) and heredoc bodies are not targets."""
    out = []
    try:
        lx = shlex.shlex(_strip_heredocs(cmd), posix=True, punctuation_chars=";&|()<>")
        lx.whitespace_split = True
        toks = list(lx)
    except Exception:
        return []
    segs, cur, i = [], [], 0
    while i < len(toks):
        t = toks[i]
        if t in (">", ">>", ">|", "&>", "&>>"):
            nxt = toks[i + 1] if i + 1 < len(toks) else ""
            if nxt.startswith("&"):           # >&2 style duplication
                i += 2; continue
            if nxt and nxt != "/dev/null":
                out.append(nxt)
            i += 2; continue
        if t in (">&", "<", "<<", "<<<", "<&"):
            i += 2; continue
        if set(t) <= set(";&|()") and t:
            segs.append(cur); cur = []; i += 1; continue
        if cur == [] and re.fullmatch(r"\d", t) and i + 1 < len(toks) and toks[i + 1] in (">", ">>", ">&"):
            i += 1; continue                  # leading fd number of 2>file
        if re.fullmatch(r"\d", t) and i + 1 < len(toks) and toks[i + 1] in (">", ">>", ">&"):
            i += 1; continue
        cur.append(t); i += 1
    segs.append(cur)
    for w in segs:
        while w and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", w[0]):   # VAR=x cmd
            w = w[1:]
        if not w:
            continue
        verb = os.path.basename(w[0])
        args = [a for a in w[1:] if not a.startswith("-")]
        if verb == "tee":
            out += args
        elif verb in ("mkdir", "touch"):
            out += args
        elif verb in ("cp", "mv", "install") and len(args) >= 2:
            out.append(args[-1])
    return [_abs(t, cwd) for t in out]


def _decide(path):
    """-> (decision, reason, suggestion)  decision in allow|redirect|block"""
    P = pathlib.Path(path)
    sp = str(P)
    if any(sp.startswith(t) or sp == t.rstrip("/") for t in TMP_PREFIXES):
        return "allow", "temp", None
    if WORKDIR:
        wd = os.path.realpath(WORKDIR)
        own_proj = str((WS / "projects" / ACTOR).resolve()) if ACTOR else None
        if sp.startswith(wd.rstrip("/") + "/") and not (own_proj and sp.startswith(own_proj + "/")):
            return "allow", "own working folder (localPath)", None
    try:
        rel = P.relative_to(WS.resolve())
    except ValueError:
        try:
            P.relative_to(ROOT)
            return "block", "outside your project: the Odin repo/root is not a project folder", str(WS / "projects" / ACTOR / "code" / P.name)
        except ValueError:
            return "block", "outside your project folder", str(WS / "projects" / ACTOR / "code" / P.name)
    parts = rel.parts
    if parts[:1] == ("shared",):
        return "block", "writes to shared go only through the door", f"{DOOR} promote <your file inside your project>"
    if parts[:1] == ("projects",) and len(parts) >= 2:
        if parts[1] != ACTOR:
            return "block", f"cross-project write into '{parts[1]}' (you are '{ACTOR}')", str(WS / "projects" / ACTOR / "code" / P.name)
        sub = "/".join(parts[2:-1]) if len(parts) > 3 else ""
        name = parts[-1]
        try:
            sys.path.insert(0, str(ROOT / "server"))
            import workspace_mw as mw
            final, corrected, note = mw.route("project", ACTOR, sub, name)
        except Exception as e:
            return "allow", f"route unavailable ({e})", None
        if corrected:
            sugg = str(WS / "projects" / ACTOR / final / name) if final else str(WS / "projects" / ACTOR / name)
            return "redirect", f"non-canonical slot ({note})", sugg
        return "allow", "own project, canonical slot", None
    return "block", "outside your project folder (workspace area that belongs to the system)", str(WS / "projects" / ACTOR / "code" / P.name)


def main():
    if MODE == "off" or not ACTOR:
        sys.exit(0)
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    tool = data.get("tool_name", "")
    ti = data.get("tool_input", {}) or {}
    cwd = data.get("cwd") or os.getcwd()
    if tool in ("Write", "Edit", "MultiEdit"):
        targets = [_abs(ti.get("file_path", ""), cwd)] if ti.get("file_path") else []
    elif tool == "NotebookEdit":
        targets = [_abs(ti.get("notebook_path", ""), cwd)] if ti.get("notebook_path") else []
    elif tool == "Bash":
        cmd = ti.get("command", "") or ""
        if "door_cli.py" in cmd:
            # the door is the sanctioned route, but only as the REAL actor, and it does not
            # excuse other raw writes chained in the same command (they are checked below).
            import re as _re
            claimed = set(_re.findall(r"ODIN_ACTOR_PID=[\"']?([A-Za-z0-9_.-]+)", cmd))
            if claimed - {ACTOR}:
                _log({"tool": tool, "target": "door", "decision": "block", "reason": "door used under another actor", "cmd": cmd[:300]})
                if MODE == "enforce":
                    print(f"[Odin scope rule] BLOCK: the door runs only as your own project ({ACTOR}). Remove ODIN_ACTOR_PID overrides.", file=sys.stderr)
                    sys.exit(2)
                sys.exit(0)
            if os.environ.get("ODIN_SCOPE_HOOK_TRACE") == "1":
                _log({"tool": tool, "target": "door", "decision": "allow", "reason": "via door", "cmd": cmd[:300]})
        targets = _bash_targets(cmd, cwd)
        if not targets and os.environ.get("ODIN_SCOPE_HOOK_TRACE") == "1":
            _log({"tool": tool, "target": "", "decision": "allow", "reason": "no write target"})
    else:
        sys.exit(0)
    worst = None
    for t in targets:
        d, why, sugg = _decide(t)
        if d == "allow" and os.environ.get("ODIN_SCOPE_HOOK_TRACE") == "1":
            _log({"tool": tool, "target": t, "decision": "allow", "reason": why})
        if d != "allow":
            _log({"tool": tool, "target": t, "decision": d, "reason": why, "suggest": sugg,
                  "cmd": (ti.get("command", "")[:300] if tool == "Bash" else "")})
            if worst is None or d == "block":
                worst = (d, t, why, sugg)
    if worst and MODE == "enforce":
        d, t, why, sugg = worst
        msg = (f"[Odin scope rule] {d.upper()}: {t} — {why}. "
               + (f"Write it here instead: {sugg}" if d == "redirect" or (sugg and not sugg.startswith("python3")) else f"Use the door: {sugg}"))
        print(msg, file=sys.stderr)
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
