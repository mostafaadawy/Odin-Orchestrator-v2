"""
Self-healing deploy agent — deterministic HANDS (workspace/shared/infra/deploy.sh) + an AI BRAIN.

Strategy (learned from real faults, encoded here):
  1. Run the pipeline. It returns a REAL exit code.
  2. On a real failure, do a CONCERN-SPECIFIC analysis: probe exactly the area that failed
     (Prisma/migration vs build vs ports vs service vs disk) — not a generic dump. The probe set
     EXPANDS round by round, the way we learned to dig deeper each attempt.
  3. Check the LEARNED-FAULTS memory first: a fault solved once is recognized and fixed instantly.
  4. Otherwise ask the engine for the root cause + ONE safe fix; apply it; RE-RUN to verify.
  5. Loop up to MAX_ROUNDS (10). Stop early ONLY for a human rule (destructive / missing info).
  6. Record an honest FAILURE with the real reason if still failing after the cap.

CARDINAL RULE (enforced in code, not prose): success is returned ONLY on a verified exit-0.
"""
from __future__ import annotations

import json
import re

import store
import deploy_runner

try:
    import operations
except Exception:
    operations = None

MAX_ROUNDS = 10
_FAULTS_FILE = "deploy_faults.json"      # learned faults: [{sig, reason, fix, ts}]

# Fixes matching this are DESTRUCTIVE — never auto-run; surfaced to the owner instead.
_UNSAFE = re.compile(
    r"migrate\s+reset|--force|drop\s+(database|table|schema)|truncate|delete\s+from|"
    r"rm\s+-rf\s+/|prisma\s+db\s+push|reset\s+--hard|DROP\s+", re.I)


# ---------------------------------------------------------------- engine + json
def _engine(prompt: str) -> str:
    try:
        import claude_cli
        if claude_cli.available():
            return claude_cli.ClaudeCLIBrain().respond(prompt, lang="en")
    except Exception:
        pass
    return ""


def _json(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text or "", re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except Exception:
        return None


# ---------------------------------------------------------------- learned faults
def _learned() -> list:
    return store.read_json(_FAULTS_FILE, [])


def _signature(err: str) -> str:
    """A short, stable fingerprint of a failure so we can recognise it again."""
    for pat in (r"P\d{4}", r"error TS\d+", r"E[A-Z]{4,}", r"code\s+\d+"):
        m = re.search(pat, err)
        if m:
            return m.group(0)
    for line in err.splitlines():
        if re.search(r"error|failed|cannot|denied|exists|refused", line, re.I):
            return line.strip()[:70]
    return (err.strip().splitlines() or ["unknown"])[-1][:70]


def _match_learned(sig: str) -> dict | None:
    for f in _learned():
        if f.get("sig") == sig and f.get("fix"):
            return f
    return None


def _record_learned(sig: str, reason: str, fix: str) -> None:
    faults = [f for f in _learned() if f.get("sig") != sig]
    faults.append({"sig": sig, "reason": reason, "fix": fix, "ts": store.now()})
    store.write_json(_FAULTS_FILE, faults[-100:])


# ---------------------------------------------------------------- concern probes
def _tail(oid: str | None, n: int = 60) -> str:
    if not (oid and operations):
        return ""
    op = operations.get(oid) or {}
    return "\n".join(l.get("line", "") for l in op.get("log", [])[-n:])


def _gather(err: str, vmdir: str = "/home/mostafa/RBO-Staging/b") -> str:
    """Run CONCERN-SPECIFIC probes on the VM — only what's relevant to THIS failure."""
    import deploy_ssh
    low = err.lower()
    probes = []
    if "prisma" in low or re.search(r"P\d{4}", err):
        probes.append(("migrate status", f"cd {vmdir} && npx prisma migrate status 2>&1 | tail -25"))
    if "tsc" in low or "error ts" in low or "nest build" in low or "npm run build" in low:
        probes.append(("build error tail", f"cd {vmdir} && tail -40 /tmp/odin_build.log 2>/dev/null"))
    if "eaddrinuse" in low or "port" in low or "address already in use" in low:
        probes.append(("listening ports", "ss -ltnp 2>/dev/null | head -25"))
    if any(k in low for k in ("did not respond", "503", "service", "journal", "exited")):
        probes.append(("service log", "journalctl -u bendcore-staging -n 40 --no-pager 2>/dev/null"))
    if "permission" in low or "eacces" in low or "denied" in low:
        probes.append(("perms", f"ls -la {vmdir} | head -20; whoami"))
    probes.append(("disk/mem", "df -h / | tail -1; free -h 2>/dev/null | head -2"))
    out = []
    for name, cmd in probes:
        r = deploy_ssh.ssh_exec(cmd)
        out.append(f"## {name}\n{(r.get('out') or r.get('err') or r.get('error') or '')[:800]}")
    return "\n".join(out)


def diagnose(error_text: str) -> dict | None:
    prompt = (
        "You are a senior DevOps engineer fixing a failed deploy to a Linux VM (user `mostafa`; "
        "NestJS/Prisma backend + Next.js frontend). Below is the REAL failing log plus targeted "
        "probes. Find the ROOT CAUSE and give ONE shell command to run ON THE VM as mostafa that "
        "fixes the actual cause.\n"
        "RULES: never lose data (no migrate reset, drop, --force, db push). If the only real fix is "
        "destructive OR info is missing, set needs_owner=true and leave fix empty. Be specific to "
        "the actual error.\n\n"
        f"--- failing log + probes ---\n{error_text[-5000:]}\n--- end ---\n\n"
        'Reply ONLY JSON: {"reason":"<root cause>","fix":"<one VM shell command or empty>",'
        '"needs_owner":<true|false>}')
    return _json(_engine(prompt))


# ---------------------------------------------------------------- main loop
def run(oid: str | None = None, on_log=None, max_rounds: int = MAX_ROUNDS, args: list | None = None) -> dict:
    """args is passed straight to the pipeline, e.g. ['frontend'] to deploy ONLY the frontend."""
    on_log = on_log or (lambda *_: None)

    def log(m: str):
        on_log(m)
        if oid and operations:
            operations.log(oid, m)

    pending = None        # {sig, reason, fix} applied last round — recorded if the next run passes
    last_fix = None
    for rnd in range(1, max_rounds + 1):
        if rnd > 1:
            log(f"🔁 Re-running to VERIFY the fix (attempt {rnd}/{max_rounds})…")
        res = deploy_runner.run_script(oid=oid, on_log=on_log, args=args)

        if res.get("ok"):                                   # the ONLY success path
            if pending:                                     # the fix worked → remember it forever
                _record_learned(pending["sig"], pending["reason"], pending["fix"])
                log(f"📚 Learned this fix for next time [{pending['sig']}].")
            return {"ok": True, "rounds": rnd}
        if res.get("stopped"):
            return {"ok": False, "stopped": True, "rounds": rnd}

        # COMMIT POINT: the deploy already rebooted the VM (reset/build succeeded; only the
        # post-reboot verify failed). Do NOT re-run the whole pipeline — that would reboot and
        # re-reset again. Stop and report so the owner checks the site. (This is the fix for the
        # reboot/reset loop; it does NOT weaken the retry protocol, which only retries PRE-reboot.)
        if res.get("rebooted"):
            return {"ok": False, "rounds": rnd, "needs_owner": True, "rebooted": True,
                    "reason": "Deploy applied and the VM rebooted, but the post-reboot health check "
                              "didn't return 200 in time. NOT re-running (that would reboot/reset again). "
                              "Check the site/log; re-run only if you decide to."}

        log(f"❌ Attempt {rnd} failed (exit {res.get('rc')}). Running concern-specific analysis…")
        err = _tail(oid) + "\n\n=== targeted probes ===\n" + _gather(_tail(oid))
        sig = _signature(err)

        known = _match_learned(sig)
        if known and not _UNSAFE.search(known["fix"]):
            reason, fix = known.get("reason", "known fault"), known["fix"]
            log(f"📚 Recognised a known fault [{sig}]: {reason}. Applying the learned fix.")
        else:
            d = diagnose(err)
            if not d:
                return {"ok": False, "rounds": rnd, "reason": "deploy failed; engine gave no diagnosis"}
            reason, fix = (d.get("reason") or "unknown").strip(), (d.get("fix") or "").strip()
            log(f"🧠 Root cause: {reason}")
            if d.get("needs_owner") or not fix:
                return {"ok": False, "rounds": rnd, "needs_owner": True, "reason": reason, "proposed_fix": fix}
            if _UNSAFE.search(fix):
                log(f"⛔ Fix is destructive — needs your approval: {fix}")
                return {"ok": False, "rounds": rnd, "needs_owner": True, "destructive": True,
                        "reason": reason, "proposed_fix": fix}

        if fix == last_fix:
            log("⚠️ Same fix didn't help — stopping to avoid a loop.")
            return {"ok": False, "rounds": rnd, "reason": reason, "proposed_fix": fix, "stuck": True}
        last_fix = fix
        log(f"🔧 Applying on the VM (as mostafa): {fix}")
        import deploy_ssh
        r = deploy_ssh.ssh_exec(fix)
        ok = bool(r.get("ok"))
        log(f"   ↳ {'✅ applied' if ok else '❌ fix failed'}: {(r.get('out') or r.get('err') or r.get('error') or '')[:300]}")
        if not ok:
            return {"ok": False, "rounds": rnd, "reason": reason, "proposed_fix": fix, "fix_failed": True}
        pending = {"sig": sig, "reason": reason, "fix": fix}      # verify on the next loop

    return {"ok": False, "rounds": max_rounds, "reason": f"still failing after {max_rounds} attempts"}
