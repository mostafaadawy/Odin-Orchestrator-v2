"""
Deterministic deploy runner — does exactly what the owner's fast hand-script does, in code, and
reports every step into a single Operation the UI can WATCH and STOP.

Channels (the owner's rule, enforced here):
  • Control plane (root) is used for ONE thing only: refresh the VM firewall to the current IP.
  • EVERYTHING else (rsync, migrate, build, reboot) runs over SSH as user `mostafa` with the
    PASSWORD from workspace/shared/oth/.cred — via deploy_ssh. No app command ever runs as root.

NO AI in the execution path → fast and identical every time (≈ minutes, like the owner's script).
The runner checks the operation's STOP flag between every step, so the owner can halt it at any
point and it stops cleanly instead of looping forever.

Config (data/deploy/<pid>.json):
{
  "host": "52.180.154.225", "user": "mostafa", "reboot": true,
  "targets": [
    {"name":"backend", "local":".../RBO-Staging/b", "vm":"/home/mostafa/RBO-Staging/b",
     "excludes":[".env*","node_modules/**", ...],
     "migration":"reset",          # reset (destructive) | new (additive, keeps data) | none
     "commands":["npm run build"]} , ... ]
}
"""
from __future__ import annotations

import os
import json
import shlex
import time
import threading
import subprocess
import pathlib

import store

try:
    import operations
except Exception:                  # operations is optional for a bare run
    operations = None

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "workspace" / "shared" / "infra" / "deploy.sh"


def run_script(oid: str | None = None, on_log=None, stop_check=None, args: list | None = None) -> dict:
    """Run the PROVEN deploy exactly as the terminal does — workspace/shared/infra/deploy.sh — streaming every
    line into the operation log + chat. This is the single source of truth: the app's Deploy button
    and the terminal run the identical script, so what works in one works in the other.
    Returns {ok, stopped, rc}."""
    on_log = on_log or (lambda *_: None)
    if not SCRIPT.exists():
        msg = f"deploy script not found at {SCRIPT}"
        on_log("❌ " + msg)
        return {"ok": False, "error": msg, "rc": -1}
    cmd = ["bash", str(SCRIPT)] + list(args or [])
    try:
        proc = subprocess.Popen(cmd, cwd=str(ROOT), stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, bufsize=1)
    except Exception as e:
        on_log(f"❌ could not start deploy script: {e}")
        return {"ok": False, "error": str(e), "rc": -1}
    flag = {"stopped": False}

    def _want_stop():
        return bool((oid and operations and operations.stop_requested(oid)) or (stop_check and stop_check()))

    # WATCHDOG: poll the Stop flag once a second INDEPENDENTLY of stdout, so Stop is responsive even
    # while the script is blocked on a long silent step (e.g. an SSH timeout) producing no output.
    def _watch():
        while proc.poll() is None:
            if _want_stop():
                flag["stopped"] = True
                on_log("⏹ Stopping — terminating the running step…")
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                return
            time.sleep(1)
    threading.Thread(target=_watch, daemon=True).start()

    import re as _re
    # Each REAL pipeline action prints a live "    ✓ <thing>" / "    ✗ <thing> FAILED" line. Turn
    # those into operation STEPS so the UI's step indicators reflect ACTUAL actions + outcomes,
    # not an abstract plan count. (Source of truth = what really ran.)
    _step_re = _re.compile(r"^\s*([✓✗])\s+(.*\S)")
    rebooted = False
    try:
        for line in proc.stdout:                       # stream live, line by line
            line = line.rstrip("\n")
            if "__ODIN_REBOOTED__" in line:
                rebooted = True                        # commit point reached — do not re-run after this
                continue                               # don't show the internal marker
            on_log(line)
            if oid and operations:
                operations.log(oid, line)
                m = _step_re.match(line)
                if m:
                    ok = (m.group(1) == "✓")
                    name = _re.sub(r"\s*\((exit|see)[^)]*\)", "", m.group(2))[:80]
                    try:
                        operations.step(oid, name, ok, m.group(2)[:200])
                    except Exception:
                        pass
            if _want_stop():                            # also stop promptly on a fresh line
                flag["stopped"] = True
                try:
                    proc.terminate()
                except Exception:
                    pass
                break
    finally:
        try:
            rc = proc.wait(timeout=30)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
            rc = -9
    stopped = flag["stopped"]
    return {"ok": (rc == 0) and not stopped, "stopped": stopped, "rc": rc, "rebooted": rebooted}

# Files that must NEVER be synced even if the owner forgets them (secrets the .env* glob misses).
HARD_EXCLUDES = [".env*", ".backup-env", "*.copy", "*.bak", "*.tmp", "*.pem", "*.key",
                 "config/google-oauth-client.json"]


def _cfg_path(pid: str) -> pathlib.Path:
    # a project's deploy config lives INSIDE its own workspace folder (structured), not the flat data/deploy/
    d = ROOT / "workspace" / "projects" / pid
    d.mkdir(parents=True, exist_ok=True)
    return d / "deploy" / "deploy-config.json"


def get_config(pid: str) -> dict:
    p = _cfg_path(pid)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_config(pid: str, cfg: dict) -> dict:
    _cfg_path(pid).write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return cfg


def ai_decide_deploy(brief: str) -> dict | None:
    """The AI BRAIN of the hybrid: reason a structured deploy DECISION from the brief — it adapts to
    the method/targets the owner asks (incl. a sandbox/test path or frontend-only). Returns
    {targets:[{name,local,vm,migration,build}], reboot, excludes_extra} or None. The method is fixed
    to the SAFE one (SSH as mostafa + migrate deploy) so the decision can't choose a broken channel."""
    try:
        import json
        import re as _re
        import claude_cli
        if not claude_cli.available():
            return None
        p = ("You are a senior DevOps engineer. From the deploy brief, DECIDE the exact deploy plan and "
             "return JSON ONLY. Always over SSH as user mostafa; migrations via `prisma migrate deploy` "
             "(never the control plane, never `migrate dev`). Use the owner's EXACT target paths this run "
             "(including any sandbox/test path). Include only the targets the owner asked for (e.g. "
             "frontend-only ⇒ just frontend). migration ∈ none|new|reset (reset only if explicitly "
             "authorized).\n"
             "ALSO extract, FROM THE BRIEF (do not invent): the FULL exclude list the owner specified "
             "(every pattern, including unusual ones like *.mp5), the verify PORT, and the migration "
             "intent — and report them back so the brief's specifics actually drive the deploy.\n"
             '{"targets":[{"name":"frontend","local":"/abs/local","vm":"/abs/vm","migration":"none",'
             '"build":"rm -rf .next && npm run build"}],"reboot":false,'
             '"excludes":["*.mp5","..."],"verify_port":"4013","migration_intent":"migrate deploy"}\n\n'
             f"Brief:\n{brief[:3000]}")
        raw = claude_cli.ClaudeCLIBrain().respond(p, lang="en")
        ai_decide_deploy.last = (raw or "(empty)")[:400]   # diagnosis: why a decision did/didn't form
        if not raw:
            ai_decide_deploy.last = "engine returned empty"
            return None
        cleaned = _re.sub(r"```[a-zA-Z]*", "", raw)          # tolerate ```json fences
        m = _re.search(r"\{.*\}", cleaned, _re.S)
        if not m:
            ai_decide_deploy.last = "no JSON object in engine reply: " + raw[:200]
            return None
        try:
            return json.loads(m.group(0))
        except Exception as e:
            ai_decide_deploy.last = f"JSON parse failed ({e}): {m.group(0)[:200]}"
            return None
    except Exception as e:
        ai_decide_deploy.last = f"exception: {e}"
        return None


def write_decision_config(decision: dict) -> str:
    """Turn the AI's decision into a deploy config the PROVEN script executes. Returns its path."""
    d = decision or {}
    lines = []
    for t in d.get("targets", []):
        n = str(t.get("name") or "").lower()
        if n not in ("backend", "frontend"):
            continue
        U = n.upper()
        if t.get("local"):
            lines.append(f'CFG_{U}_LOCAL="{t["local"]}"')
        if t.get("vm"):
            lines.append(f'CFG_{U}_VM="{t["vm"]}"')
        lines.append(f'CFG_{U}_MIG="{t.get("migration", "none")}"')
        if t.get("build"):
            lines.append(f'CFG_{U}_BUILD="{t["build"]}"')
    lines.append(f'CFG_REBOOT={1 if d.get("reboot") else 0}')
    ex = (d.get("excludes") or d.get("excludes_extra") or [])   # honor the brief's exact exclude list
    if ex:
        lines.append("CFG_EXTRA_EXCLUDES=( " + " ".join(f'"{e}"' for e in ex) + " )")
    # keep generated deploy config INSIDE the workspace (never ROOT/data — that created a root-stray)
    out = ROOT / "workspace" / "shared" / "infra" / "_ai_decision_config.sh"
    out.parent.mkdir(parents=True, exist_ok=True)
    path = str(out)
    pathlib.Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        import workspace_mw
        workspace_mw.sync_row(path)   # keep odin_core_iso in lockstep
    except Exception:
        pass
    return path


def _project_sources(pid: str) -> list:
    """The local folders the owner ACTUALLY selected for this project (Browse) — sources + mappings
    + localPath, de-duplicated. This is the source of truth for where the code lives, NOT the brief."""
    try:
        import projects  # type: ignore
        p = projects.get_project(pid) or {}
    except Exception:
        return []
    cand = list(p.get("sources") or [])
    cand += [m.get("local") for m in (p.get("mappings") or []) if m.get("local")]
    if p.get("localPath"):
        cand.append(p["localPath"])
    seen, out = set(), []
    for s in cand:
        if s and s not in seen:
            seen.add(s); out.append(s)
    return out


def _bad_local(path: str) -> bool:
    """A local path is unusable if it's empty, a leftover placeholder, or not a real directory."""
    if not path:
        return True
    if "<" in path or ">" in path or "UNRESOLVED" in path:
        return True
    try:
        return not os.path.isdir(os.path.expanduser(path))
    except Exception:
        return True


def _match_source(name: str, sources: list) -> str | None:
    name = (name or "").lower()
    for s in sources:                                   # folder whose name contains the role (organics-frontend → frontend)
        if name and name in os.path.basename(str(s).rstrip("/")).lower():
            return s
    return None


def _resolve_locals(pid: str, decision: dict):
    """Repair each target's local path from the folders the owner SELECTED — overriding any
    placeholder/missing path that leaked in from the brief. Returns (decision, unresolved_names)."""
    d = decision or {}
    sources = _project_sources(pid)
    unresolved = []
    for t in d.get("targets", []):
        if _bad_local(t.get("local")):
            name = str(t.get("name", "")).lower()
            match = _match_source(name, sources) or (sources[0] if len(sources) == 1 else None)
            if match:
                t["local"] = match
            else:
                unresolved.append(name or "target")
    return d, unresolved


def run_decision(pid: str, decision: dict, oid: str | None = None, on_log=None) -> dict:
    """Execute the AI's decision DETERMINISTICALLY (reliable + self-healing + audited). Runs only the
    decided targets. If a harness already locked ODIN_DEPLOY_CONFIG (e.g. a sandbox), that lock wins —
    so a test can keep execution isolated regardless of the decision."""
    import os
    import deploy_agent
    # USE THE FOLDERS THE OWNER SELECTED (Browse), not whatever the brief said. If a folder still
    # can't be resolved, STOP and ASK — never proceed with a guessed/placeholder path.
    decision, unresolved = _resolve_locals(pid, decision)
    if unresolved:
        question = ("I can't find the local folder(s) for: " + ", ".join(unresolved) +
                    ". Give me the correct path(s) and I'll continue from here.")
        needs = [{"key": f"local_{n}", "label": f"Local folder for {n}",
                  "placeholder": "/Users/you/Desktop/...", "role": n} for n in unresolved]
        if on_log:
            on_log("⛔ " + question)
        if oid and operations:
            operations.set_meta(oid, "decision", decision)   # so a resume can re-run with the same plan
            operations.set_meta(oid, "resume", "deploy_decision")
            operations.ask(oid, question, needs)             # STOP + ASK in the shared pool, with fields
        return {"ok": False, "stopped": False, "needs_owner": True,
                "reason": "local folder(s) not found", "ask": question, "needs": needs, "missing": unresolved}
    names = {str(t.get("name", "")).lower() for t in (decision or {}).get("targets", [])} & {"frontend", "backend"}
    args = ["frontend"] if names == {"frontend"} else (["backend"] if names == {"backend"} else [])
    locked = "ODIN_DEPLOY_CONFIG" in os.environ          # a harness (sandbox) lock takes precedence
    if not locked:
        os.environ["ODIN_DEPLOY_CONFIG"] = write_decision_config(decision)
    try:
        return deploy_agent.run(oid=oid, on_log=on_log, args=args)
    finally:
        if not locked:
            os.environ.pop("ODIN_DEPLOY_CONFIG", None)


def config_from_prompt(prompt: str) -> dict | None:
    """Extract the DEPLOY targets a prompt describes (so we can verify a prompt reproduces the
    working config). Returns {'targets':[{name, vm, build}]} or None if the engine is unavailable."""
    try:
        import json
        import re as _re
        import claude_cli
        if not claude_cli.available():
            return None
        p = ("From this deploy request, extract each app to deploy as JSON ONLY: its name "
             "(frontend or backend), its VM destination path, and its build command.\n"
             '{"targets":[{"name":"frontend","vm":"/home/mostafa/RBO-Staging/f","build":"npm run build"}]}\n\n'
             f"Request:\n{prompt}")
        raw = claude_cli.ClaudeCLIBrain().respond(p, lang="en")
        m = _re.search(r"\{.*\}", raw or "", _re.S)
        return json.loads(m.group(0)) if m else None
    except Exception:
        return None


def _migration_cmd(mode: str) -> str | None:
    """The owner's migration step, made SMART/safe by mode."""
    if mode == "reset":   # destructive — wipes + reseeds (must be explicitly chosen each run)
        return ("rm -rf prisma/migrations && npx prisma generate && "
                "npx prisma migrate reset --force && npx prisma migrate dev --name ini")
    if mode == "new":     # additive, NON-interactive production command — never resets, never prompts
        return "npx prisma generate && npx prisma migrate deploy"
    return None           # none → don't touch the DB


def _emit(oid, on_log, line: str, also_step: tuple | None = None):
    """Write one line to BOTH the operation log (the UI watches this) and the chat on_log."""
    if on_log:
        try:
            on_log(line)
        except Exception:
            pass
    if oid and operations:
        operations.log(oid, line)
        if also_step:
            operations.step(oid, *also_step)


def _stopped(oid) -> bool:
    return bool(oid and operations and operations.stop_requested(oid))


def _rsync(target: dict, on_log, oid) -> dict:
    """Sync one target local → VM over SSH as mostafa (password channel, deploy_ssh)."""
    import deploy_ssh
    excludes = list(dict.fromkeys((target.get("excludes") or []) + HARD_EXCLUDES))
    _emit(oid, on_log, f"$ rsync {target['name']} → VM:{target['vm']} (excludes: {len(excludes)}, as mostafa)")
    r = deploy_ssh.rsync_push(target["local"], target["vm"], excludes=excludes, delete=False)
    body = (r.get("out") or "") + (("\n" + r["err"]) if r.get("err") else "") + (r.get("error") or "")
    _emit(oid, on_log, (body or "(no rsync output)")[-1500:])
    ok = bool(r.get("ok"))
    # CONFIRM THE OVERWRITE TOOK (content-level): after pushing, prove the VM is byte-for-byte identical to
    # local. rsync --checksum --dry-run lists any file whose CONTENT still differs; an empty list = the
    # update genuinely overwrote every changed file (not just added missing ones). This is the deterministic
    # guard for the 'files not updated on the VM' bug — a successful push that didn't actually overwrite is
    # now caught here instead of silently shipping stale code.
    if ok:
        try:
            v = deploy_ssh.verify_sync(target["local"], target["vm"], excludes=excludes)
            if v.get("ok"):
                _emit(oid, on_log, f"✓ sync verified — VM content matches local exactly ({target['name']}).")
            else:
                ok = False
                _emit(oid, on_log, f"✗ SYNC NOT FULLY APPLIED — {v.get('count', '?')} file(s) still stale on the "
                                   f"VM after push: {', '.join(v.get('pending', [])[:8])}. The update did not "
                                   "overwrite everything (content-level mismatch).")
        except Exception as _ve:
            _emit(oid, on_log, f"(sync-verify skipped: {_ve})")
    return {"step": f"sync:{target['name']}", "ok": ok, "ran_as": r.get("ran_as")}


def run_deploy(pid: str, cfg: dict | None = None, refresh_firewall: bool = True,
               on_log=None, oid: str | None = None) -> dict:
    """Execute the deploy deterministically. Returns {ok, stopped, steps:[...]}.
    Streams into the Operation `oid` (live log + stop checks) and the chat `on_log`."""
    on_log = on_log or (lambda *_: None)
    cfg = cfg or get_config(pid)
    if not cfg or not cfg.get("targets"):
        msg = "No deploy config. Set targets (local/vm/excludes/commands) first."
        _emit(oid, on_log, "❌ " + msg)
        return {"ok": False, "steps": [], "error": msg}

    user = cfg.get("user") or "mostafa"
    steps: list = []

    # 1) make the VM reachable — the ONLY control-plane (root) action: firewall → current IP.
    if refresh_firewall and not _stopped(oid):
        try:
            import deploy_ssh
            rot = deploy_ssh.refresh_firewall()
            ok = bool(rot.get("ok"))
            steps.append({"step": "firewall", "ok": ok, "ip": rot.get("ip")})
            _emit(oid, on_log, f"🔌 firewall → {rot.get('ip','?')} ({'ok' if ok else 'partial'})",
                  also_step=("firewall (control plane)", ok, f"ip {rot.get('ip','?')}"))
        except Exception as e:
            steps.append({"step": "firewall", "ok": False, "error": str(e)})
            _emit(oid, on_log, f"⚠️ firewall refresh: {e}", also_step=("firewall (control plane)", False, str(e)))

    import deploy_ssh
    # 2) + 3) per target: sync, then run its commands ON the VM as mostafa (password channel).
    for t in cfg["targets"]:
        if _stopped(oid):
            break
        rs = _rsync(t, on_log, oid)
        steps.append(rs)
        if oid and operations:
            operations.step(oid, rs["step"], rs["ok"], f"ran_as {rs.get('ran_as')}")
        if _stopped(oid):
            break

        # ordered command list for this target (migration first if set, then commands)
        cmds = []
        mig = _migration_cmd(t.get("migration", "none"))
        if mig:
            cmds.append(mig)
        cmds += list(t.get("commands") or [])
        if not cmds:
            continue
        script = "set -e\n" + "\n".join(cmds)
        _emit(oid, on_log, f"$ (vm, as {user}) {t['name']}: {'; '.join(cmds)[:140]}")
        try:
            r = deploy_ssh.ssh_exec(script, cwd=t["vm"])     # AS mostafa, password — no root-owned files
            ok = bool(r.get("ok"))
            body = (r.get("out") or "") + (("\n" + r["err"]) if r.get("err") else "") + (r.get("error") or "")
            _emit(oid, on_log, (body or "(no output)")[-1500:], also_step=(f"cmds:{t['name']}", ok, body[:300]))
            steps.append({"step": f"cmds:{t['name']}", "ok": ok, "ran_as": r.get("ran_as")})
        except Exception as e:
            _emit(oid, on_log, f"❌ vm command error: {e}", also_step=(f"cmds:{t['name']}", False, str(e)))
            steps.append({"step": f"cmds:{t['name']}", "ok": False, "error": str(e)})

    stopped = _stopped(oid)
    # 4) reboot as mostafa (sudo -S with the password, handled inside deploy_ssh) — only if not stopped.
    if cfg.get("reboot") and not stopped:
        try:
            deploy_ssh.ssh_exec("sudo reboot")
            steps.append({"step": "reboot", "ok": True})
            _emit(oid, on_log, "🔄 sudo reboot issued (as mostafa)", also_step=("reboot", True, ""))
        except Exception as e:
            steps.append({"step": "reboot", "ok": False, "error": str(e)})
            _emit(oid, on_log, f"⚠️ reboot: {e}", also_step=("reboot", False, str(e)))

    ok = all(s.get("ok", False) for s in steps if not s.get("step", "").startswith("firewall"))
    return {"ok": ok and not stopped, "stopped": stopped, "steps": steps}
