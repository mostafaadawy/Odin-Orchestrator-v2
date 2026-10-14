"""
Claude CLI engine — the REAL brain of Odin (Claude Code working on the project folder).

This is the core per the owner's design: Odin wraps and elevates Claude CLI, it does not
replace it. The dispatcher routes here so answers come from Claude Code actually reading the
project — not from a generic local LLM.

Requires the `claude` CLI (Claude Code) installed and authenticated on the machine.
Read-only tools are allowed here (Read/Glob/Grep) so it can inspect the project to answer;
anything that writes/changes still goes through Odin's approval gate elsewhere.
"""
import os
import json
import shutil
import subprocess
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent  # Odin-Orchestrator/
_HERE = pathlib.Path(__file__).resolve().parent           # server/
_RO_HOOK = _HERE / "readonly_hook.py"
_RO_SETTINGS = _HERE / ".readonly-settings.json"          # generated once, points at the hook


def available() -> bool:
    return shutil.which("claude") is not None


def _readonly_settings_file() -> str:
    """Write (once) a Claude Code settings file that registers the PreToolUse Bash guard hook,
    and return its path. Used to ENFORCE read-only at the engine level."""
    try:
        cfg = {
            "hooks": {
                "PreToolUse": [
                    {"matcher": "Bash",
                     "hooks": [{"type": "command",
                                "command": f"{shutil.which('python3') or 'python3'} {str(_RO_HOOK)}"}]}
                ]
            }
        }
        _RO_SETTINGS.write_text(json.dumps(cfg))
        return str(_RO_SETTINGS)
    except Exception:
        return ""


_SCOPE_HOOK = _HERE / "scope_hook.py"


def _scope_settings_file(readonly: bool) -> str:
    """P2 — register the owner-scope PreToolUse hook (Write/Edit/MultiEdit/NotebookEdit/Bash) for agent runs.
    In read-only runs it is combined with the read-only Bash guard. Returns '' when ODIN_SCOPE_HOOK=off."""
    if os.environ.get("ODIN_SCOPE_HOOK", "enforce").lower() == "off":
        return _readonly_settings_file() if readonly else ""
    py = shutil.which("python3") or "python3"
    pre = [{"matcher": "Write|Edit|MultiEdit|NotebookEdit|Bash",
            "hooks": [{"type": "command", "command": f"{py} {str(_SCOPE_HOOK)}"}]}]
    if readonly:
        pre.insert(0, {"matcher": "Bash", "hooks": [{"type": "command", "command": f"{py} {str(_RO_HOOK)}"}]})
    f = _HERE / (".scope-settings-ro.json" if readonly else ".scope-settings.json")
    try:
        f.write_text(json.dumps({"hooks": {"PreToolUse": pre}}))
        return str(f)
    except Exception:
        return ""


def _actor_for(cwd: str | None) -> str:
    """The project that OWNS a working folder: workspace/projects/<pid>/… or a project's localPath."""
    if not cwd:
        return ""
    import os as _o
    c = _o.path.realpath(_o.path.expanduser(cwd))
    pr = _o.path.realpath(str(ROOT / "workspace" / "projects")) + "/"
    if c.startswith(pr):
        return c[len(pr):].split("/")[0]
    try:
        import projects as _pj
        for p in _pj.list_projects() or []:
            lp = p.get("localPath") or ""
            if lp and (c == _o.path.realpath(lp) or c.startswith(_o.path.realpath(lp).rstrip("/") + "/")):
                return p.get("id", "")
    except Exception:
        pass
    return ""


def _model_flags(model: str | None) -> list:
    """Pass `--model` to the CLI ONLY for an explicit Claude model (alias haiku/sonnet/opus or a full
    claude-* id). The sentinel 'claude-cli'/'claude'/empty means 'use the CLI default model' (no flag),
    so PRODUCTION — which never sets an explicit model — is completely unchanged. The TEST loop sets a
    fast model (e.g. haiku) for the evaluative QA/review gates to avoid 10-minute waits; the full
    process and every rule still run, just faster."""
    if model and model not in ("claude-cli", "claude") and (
            model in ("haiku", "sonnet", "opus") or model.startswith("claude-")):
        return ["--model", model]
    return []


def _tool_flags(readonly: bool) -> list:
    """Engine tool flags. READ-ONLY mode removes the file-writing tools entirely and adds the Bash
    guard hook, so an agent physically cannot modify files or run state-changing/VM commands until
    the owner approves. Non-readonly keeps the normal toolset."""
    # WRITE-ENABLED build agents MUST have the file-creation tools (Write/Edit/MultiEdit). Without them
    # an agent told to "build the app" can only shell through Bash and ends up NARRATING instead of
    # writing source files (the '0 files on disk' bug). READ-ONLY mode still strips them.
    tools = os.environ.get("ODIN_CLAUDE_TOOLS", "Read,Glob,Grep,Bash,Write,Edit,MultiEdit")
    if readonly:
        flags = ["--allowedTools", "Read,Glob,Grep,Bash",
                 "--disallowedTools", "AskUserQuestion,Write,Edit,NotebookEdit,MultiEdit"]
        sf = _scope_settings_file(True)
        if sf:
            flags += ["--settings", sf]
        return flags
    return ["--allowedTools", tools, "--disallowedTools", "AskUserQuestion"]


class ClaudeCLIBrain:
    """respond(text, lang) — same interface as OllamaBrain, but powered by Claude Code."""

    def respond(self, text: str, lang: str = "en", model: str | None = None) -> str:
        if not available():
            raise RuntimeError("`claude` CLI not found on PATH (install Claude Code).")

        prompt = text
        if str(lang).lower().startswith("ar"):
            prompt = "أجب باللهجة المصرية وباختصار.\n\n" + text

        # Terminal access so the engine can run CLIs (az, ssh, ls…) and SOLVE problems itself.
        # Default includes Bash; set ODIN_CLAUDE_TOOLS="Read,Glob,Grep" to force read-only.
        # The dispatcher's approval gate still intercepts explicitly destructive requests first.
        tools = os.environ.get("ODIN_CLAUDE_TOOLS", "Read,Glob,Grep,Bash")
        cmd = [
            "claude", "-p", prompt,
            "--output-format", "json",
            "--allowedTools", tools,
            "--disallowedTools", "AskUserQuestion",  # headless: never block on a question
        ] + _model_flags(model)
        timeout = int(os.environ.get("ODIN_CLAUDE_TIMEOUT", "600"))
        try:
            p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return "Claude CLI took too long and was stopped. Try a more specific question."
        except Exception as e:
            raise RuntimeError(f"Failed to run claude CLI: {e}") from e

        out = (p.stdout or "").strip()
        if not out:
            return (p.stderr or "Claude CLI returned no output.").strip()
        try:
            data = json.loads(out)
            return (data.get("result") or "").strip() or out
        except json.JSONDecodeError:
            return out


    def respond_with_session(self, text: str, lang: str = "en", session_id: str | None = None) -> dict:
        """Like respond(), but keeps conversation memory via a Claude Code session.
        Returns {"reply": str, "session_id": str|None}."""
        if not available():
            raise RuntimeError("`claude` CLI not found on PATH (install Claude Code).")
        prompt = text
        if str(lang).lower().startswith("ar"):
            prompt = "أجب باللهجة المصرية وباختصار.\n\n" + text
        tools = os.environ.get("ODIN_CLAUDE_TOOLS", "Read,Glob,Grep,Bash")
        cmd = ["claude", "-p", prompt, "--output-format", "json", "--allowedTools", tools,
               "--disallowedTools", "AskUserQuestion"]
        if session_id:
            cmd += ["--resume", session_id]
        timeout = int(os.environ.get("ODIN_CLAUDE_TIMEOUT", "600"))
        try:
            p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"reply": "Claude CLI took too long and was stopped.", "session_id": session_id}
        except Exception as e:
            raise RuntimeError(f"Failed to run claude CLI: {e}") from e
        out = (p.stdout or "").strip()
        if not out:
            return {"reply": (p.stderr or "Claude CLI returned no output.").strip(), "session_id": session_id}
        try:
            data = json.loads(out)
            return {"reply": (data.get("result") or "").strip() or out,
                    "session_id": data.get("session_id") or session_id}
        except json.JSONDecodeError:
            return {"reply": out, "session_id": session_id}


    def stream_session(self, text: str, lang: str = "en", session_id: str | None = None,
                       cwd: str | None = None, readonly: bool = False, model: str | None = None):
        """Generator that STREAMS Claude Code's work live (no blocking, no timeout-stop):
        yields dicts:
          {"kind":"status","icon":..,"text":..}   a live step (running a command, reading…)
          {"kind":"text","t":..}                    a chunk of the answer as it's produced
          {"kind":"session","id":..}                the Claude session id (for memory)
          {"kind":"final","text":..,"session_id":..} end of turn
        Uses `--output-format stream-json` so each tool call / message is surfaced live."""
        if not available():
            yield {"kind": "final", "text": "`claude` CLI not found on PATH.", "session_id": session_id}
            return
        prompt = text
        if str(lang).lower().startswith("ar"):
            prompt = "أجب باللهجة المصرية وباختصار.\n\n" + text
        cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose"] + _tool_flags(readonly) + _model_flags(model)
        # SPEED: make the agent runner HERMETIC. With no --mcp-config passed, claude would otherwise spawn
        # EVERY global MCP server on startup (the user's personal connectors) on every single agent call —
        # that was the ~90s of total silence before any output. The agents do their real work via
        # Read/Write/Bash/Grep in the project folder, not those servers, so we load none unless explicitly
        # asked. Set ODIN_AGENT_MCP=1 to restore loading the global MCP config.
        if os.environ.get("ODIN_AGENT_MCP", "0") != "1":
            cmd += ["--strict-mcp-config"]
        # When working ON a specific project, run with cwd = that project's folder so even relative
        # commands (npm create, mkdir, git init) land THERE — not in the Odin app's repo. Keep the
        # Odin repo accessible (for CLAUDE.md rules / registry) via --add-dir.
        run_cwd = str(ROOT)
        if cwd:
            import os as _os
            cwd = _os.path.expanduser(cwd)
            try:
                _os.makedirs(cwd, exist_ok=True)
                run_cwd = cwd
                cmd += ["--add-dir", str(ROOT)]
                # A multi-folder project (e.g. a frontend-sandbox + backend-sandbox side by side) means a
                # member's deliverable may live in a SIBLING folder of its cwd. Grant write access to the
                # cwd's PARENT so e.g. Frontend can actually build in the frontend folder the brief names —
                # otherwise it physically cannot write there and the deliverable never lands on disk.
                _parent = _os.path.dirname(cwd.rstrip("/"))
                if _parent and _parent not in (str(ROOT), "/", _os.path.expanduser("~")):
                    cmd += ["--add-dir", _parent]
            except Exception:
                run_cwd = str(ROOT)
        if session_id:
            cmd += ["--resume", session_id]
        # P2 — owner-scope write rule: tell the hook WHO is writing and WHERE its own folder is.
        _env = dict(os.environ)
        _actor = _actor_for(run_cwd if run_cwd != str(ROOT) else None)
        _env.update({"ODIN_ROOT": str(ROOT), "ODIN_ACTOR_PID": _actor,
                     "ODIN_ACTOR_WORKDIR": run_cwd if run_cwd != str(ROOT) else ""})
        if not readonly:
            _sf = _scope_settings_file(False)
            if _sf and _actor:
                cmd += ["--settings", _sf]

        icons = {"Bash": "⚙️", "Read": "📖", "Grep": "🔎", "Glob": "🔎", "Edit": "✏️", "Write": "✏️"}

        def brief(name, inp):
            inp = inp or {}
            if name == "Bash":
                c = (inp.get("command") or "").strip().replace("\n", " ")
                return ("⚙️ " + (c[:70] + ("…" if len(c) > 70 else ""))) if c else "running a command"
            if name in ("Read", "Edit", "Write"):
                return (icons.get(name, "📄") + " " + str(inp.get("file_path") or inp.get("path") or name))
            if name in ("Grep", "Glob"):
                return "🔎 " + str(inp.get("pattern") or name)
            return "🔧 " + name

        proc = subprocess.Popen(cmd, cwd=run_cwd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, bufsize=1, env=_env)
        final_text, parts, new_sid = "", [], session_id
        # FAILURE PROTOCOL (in the engine): a long step is EXPECTED — but it must prove it's alive, and a
        # genuinely STUCK call must be detected, not hang silently. A blocking `for line in proc.stdout`
        # gave NEITHER (one quiet tool call = zero events = the watchdog wrongly saw a stall). So we read
        # the stream on a background thread and pump a queue: every `hb` seconds of silence we emit a
        # HEARTBEAT status (upstream turns it into activity.beat → "working", not stalled); and after
        # `idle` seconds with NO output at all we treat the call as STUCK → terminate + report, so the
        # step fails FAST and LOCALIZED (the audit loop can retry) instead of hanging.
        import threading as _th, queue as _q, time as _tm
        _idle = int(os.environ.get("ODIN_CLAUDE_IDLE", "420"))      # no output at all this long = stuck
        _hb = int(os.environ.get("ODIN_CLAUDE_HEARTBEAT", "15"))    # emit a liveness beat this often
        _lines: "_q.Queue" = _q.Queue()

        def _reader():
            try:
                for ln in proc.stdout:
                    _lines.put(("line", ln))
            except Exception as _re:
                _lines.put(("err", str(_re)))
            finally:
                _lines.put(("eof", None))

        _rt = _th.Thread(target=_reader, daemon=True)
        _rt.start()
        # STANDARD FIX for the subprocess deadlock: stderr is PIPEd, so it MUST be drained continuously.
        # claude --verbose + MCP servers write a lot to stderr; if nobody reads it the ~64KB OS pipe
        # buffer fills, the child BLOCKS on write(stderr) and therefore stops writing stdout too — which
        # looked exactly like "the agent went silent / produced nothing". Drain it on its own thread and
        # keep the tail for a real diagnosis (and to report the actual error if a call dies).
        _err_buf: list = []

        _dbg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                 "workspace", "logs", "engine_stderr_live.log")
        try:
            with open(_dbg_path, "a") as _df:
                _df.write(f"\n\n===== {_tm.strftime('%H:%M:%S')} NEW ENGINE CALL (cwd={run_cwd}) cmd[-1 trunc]="
                          f"{(cmd[2][:80] if len(cmd) > 2 else '')!r} =====\n")
        except Exception:
            pass

        def _errdrain():
            try:
                for eln in proc.stderr:
                    _err_buf.append(eln)
                    if len(_err_buf) > 800:
                        del _err_buf[:400]
                    try:
                        with open(_dbg_path, "a") as _df:   # LIVE: so we can SEE what claude is doing now
                            _df.write(eln)
                    except Exception:
                        pass
            except Exception:
                pass

        _et = _th.Thread(target=_errdrain, daemon=True)
        _et.start()

        def _errtail(n=20):
            return "".join(_err_buf[-n:]).strip()[-700:]

        _last_out = _tm.time()
        _last_hb = _tm.time()
        _t_start = _tm.time()
        _last_tool = _tm.time()   # PROGRESS ANCHOR: reset on every real tool call
        # PROGRESS GUARD (not a total-time cap). The idle-timeout catches a call with NO output at all; but
        # an agent that NARRATES (streams text without doing real work) never goes idle. So instead of a
        # blunt total-duration guillotine (which also killed agents doing genuine long work — deep scans,
        # VM reads — the "killed as too heavy" bug), we track time since the last REAL TOOL CALL. Any tool_use
        # or tool_result resets it, so a working agent runs to completion; only pure narration with zero tool
        # activity for this window is terminated as a runaway. Standard "make progress or die" semantics.
        _maxwall = int(os.environ.get("ODIN_CLAUDE_MAXWALL", "900"))   # max seconds with NO tool progress; 0 = disabled
        try:
            while True:
                if _maxwall and (_tm.time() - _last_tool) > _maxwall:
                    yield {"kind": "status", "icon": "⛔",
                           "text": f"engine made NO tool progress for {_maxwall}s — terminating this attempt "
                                   "(narrating runaway; genuine tool work keeps it alive indefinitely; the step will retry)"}
                    try: proc.terminate()
                    except Exception: pass
                    break
                try:
                    _kind, _payload = _lines.get(timeout=2)
                except _q.Empty:
                    _now = _tm.time()
                    if _now - _last_hb >= _hb:                       # liveness beat during quiet work
                        _last_hb = _now
                        yield {"kind": "status", "icon": "⏳",
                               "text": f"still working… ({int(_now - _last_out)}s since last output)"}
                    if _now - _last_out >= _idle:                    # genuinely stuck → stop, don't hang
                        _tail = _errtail()
                        yield {"kind": "status", "icon": "⛔",
                               "text": (f"engine idle >{_idle}s with no output — terminating this attempt as stuck"
                                        + (f" | last stderr: {_tail}" if _tail else " | (stderr empty)"))}
                        try: proc.terminate()
                        except Exception: pass
                        break
                    continue
                if _kind == "eof":
                    break
                if _kind == "err":
                    yield {"kind": "status", "icon": "⚠️", "text": f"engine: {_payload}"}
                    continue
                _last_out = _tm.time()
                line = (_payload or "").strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                t = ev.get("type")
                if t == "system" and ev.get("session_id"):
                    new_sid = ev["session_id"]
                    yield {"kind": "session", "id": new_sid}
                elif t == "assistant":
                    for c in (ev.get("message", {}) or {}).get("content", []):
                        if c.get("type") == "text" and c.get("text"):
                            parts.append(c["text"])
                            yield {"kind": "text", "t": c["text"]}
                        elif c.get("type") == "tool_use":
                            _last_tool = _tm.time()   # real tool call = progress; keep the agent alive
                            b = brief(c.get("name", "tool"), c.get("input"))
                            yield {"kind": "status", "icon": b[:2].strip() or "🔧", "text": b}
                elif t == "user":
                    # tool RESULTS (command output, build pass/fail) — so the user isn't blind.
                    for c in (ev.get("message", {}) or {}).get("content", []):
                        if isinstance(c, dict) and c.get("type") == "tool_result":
                            _last_tool = _tm.time()   # tool output arriving = progress
                            out = c.get("content")
                            if isinstance(out, list):
                                out = " ".join(x.get("text", "") for x in out if isinstance(x, dict))
                            out = (out or "").strip()
                            if out:
                                yield {"kind": "tool_result",
                                       "text": out[:280].replace("\n", " "),
                                       "error": bool(c.get("is_error"))}
                elif t == "result":
                    if ev.get("result"):
                        final_text = ev["result"]
                    if ev.get("session_id"):
                        new_sid = ev["session_id"]
            proc.wait(timeout=10)
        except Exception as e:
            yield {"kind": "status", "icon": "⚠️", "text": f"engine: {e}"}
        finally:
            try:
                proc.terminate()
            except Exception:
                pass
        yield {"kind": "final", "text": (final_text or "".join(parts)).strip(), "session_id": new_sid}


default_handler = ClaudeCLIBrain()
