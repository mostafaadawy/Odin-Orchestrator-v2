"""
audit.py — the TRUTH GATE for every agent.

The job: never let a fake "done" through. Any agent message that CLAIMS success or completion is
checked against real EVIDENCE (exit codes, tool results, verified checks). If the claim isn't
backed, the audit BLOCKS it and forces a correction — the agent must either produce real evidence
or state honestly what's incomplete. No agent's word is ever accepted as success; only proof is.

This is the same judgement that, given the real data, said "this will fail — stop", made generic
so it sits over ALL agents, not just deploy.
"""
from __future__ import annotations

import re

# language that asserts an outcome happened (vs. describing a plan)
_SUCCESS = re.compile(
    r"\b(done|completed?|finished|deployed|fixed|resolved|works?|working|"
    r"success(ful|fully)?|passed|ready|live|up and running|all set|good to go)\b|✅|🎉",
    re.I)
# uncertainty markers — a "success" wrapped in these is not a real claim of fact
_HEDGE = re.compile(r"\b(should|probably|likely|i think|i believe|assume|expect|might|seems?|appears?)\b", re.I)


def claims_success(text: str) -> bool:
    return bool(_SUCCESS.search(text or ""))


def assess(text: str, evidence_ok=None) -> dict:
    """evidence_ok: True / False / None (no verification available).
    Returns {verified, fake_risk 0..1, flags, verdict, claim}."""
    claim = claims_success(text)
    hedged = bool(_HEDGE.search(text or ""))
    flags, risk = [], 0.0
    if claim and evidence_ok is False:
        risk = 1.0; flags.append("claims success but the real check FAILED")
    elif claim and evidence_ok is None:
        risk = 0.7; flags.append("claims success with NO verifying evidence")
    elif claim and hedged:
        risk = 0.4; flags.append("success claim is hedged/uncertain")
    verified = bool(claim and evidence_ok is True)
    # FAKE only when a check actually FAILED; no-evidence/hedged = UNVERIFIED (unproven, not proven false)
    verdict = ("VERIFIED" if verified else
               "FAKE" if (claim and evidence_ok is False) else
               "UNVERIFIED" if claim else "NO-CLAIM")
    return {"verified": verified, "fake_risk": risk, "flags": flags, "verdict": verdict, "claim": claim}


def gate_success(text: str, evidence_ok) -> tuple[str, dict]:
    """Return the message ONLY if its success claim is backed by evidence; otherwise replace it with
    an honest, non-trusting flag. Wrap ANY agent's final 'done' message with this."""
    a = assess(text, evidence_ok)
    if a["verified"] or not a["claim"]:
        return text, a
    if evidence_ok is False:
        return ("❌ BLOCKED FAKE CLAIM — the agent reported success, but the real check FAILED. "
                "Not trusted. Original: " + (text or ""), a)
    return ("⚠️ UNVERIFIED — success claimed with no proof; treat as NOT done until verified. "
            "Original: " + (text or ""), a)


def correction_prompt(text: str, evidence: str = "") -> str:
    """The instruction handed back to an agent that faked a result — make it self-correct."""
    return (
        "AUDIT: your previous reply CLAIMED success/completion but there is no verified evidence "
        "(exit code / tool result / check) backing it. Intentions and 'should work' are NOT evidence. "
        "Do NOT claim completion. Either run the real verification and show its result, or state "
        "plainly what is still incomplete and why. Reply with the corrected, evidence-based status only.\n\n"
        f"Previous reply:\n{text or ''}\n\nEvidence available:\n{evidence or '(none)'}")


# Danger signatures that can hide INSIDE a run that still exits 0 — the "snake in the food".
# A green deploy that contains any of these is NOT clean; the audit surfaces them.
_DANGER = [
    (r"\bP\d{4}\b", "Prisma migration error"),
    (r"drift detected", "Prisma schema drift"),
    (r"error TS\d+", "TypeScript compile error"),
    (r"\bELIFECYCLE\b", "npm script failed"),
    (r"MODULE_NOT_FOUND|cannot find module", "missing module"),
    (r"ECONNREFUSED|ETIMEDOUT|EADDRINUSE|address already in use", "network/port error"),
    (r"command not found|not installed|: not found", "missing tool/command"),
    (r"timed out|could not connect|connection refused|unexpected end of file", "connection failure"),
    (r"permission denied|\bEACCES\b", "permission error"),
    (r"ENOSPC|no space left", "disk full"),
    (r"out of memory|\bOOM\b|\bKilled\b", "out of memory / killed"),
    (r"\bfatal\b|segmentation fault|core dumped", "fatal/crash"),
    (r"unhandled (promise )?rejection|UnhandledPromiseRejection", "unhandled rejection"),
    # real failure STATUS only — not the word "Failed" inside data/labels (e.g. a Klaviyo metric named
    # "Payment Failed" / "Failed to Deliver SMS" must NOT be flagged as a run failure).
    (r"✗|\bFAIL:|\b\d+\s+failed\b|\b(build|tests?|deploy|deployment|step|command|compile|compilation|"
     r"migration|install)\s+failed\b|\bexit(\s+code)?\s+[1-9]\d*\b", "a step reported FAIL"),
    (r"npm warn deprecated.*(vuln|security)", "security-relevant deprecation"),
]
# Lines that are normal SUCCESS output and must never be mistaken for a snake (e.g. the summary
# "RESULT: 16 ok · 0 warn · 0 fail", which contains the word 'fail' as a zero-count, not a failure).
_BENIGN = re.compile(
    r"tip:|0 vulnerabilities|generated prisma client|up to date|no pending migrations|"
    r"result:|\d+\s*ok\s*·|·\s*\d+\s*fail|0 fail|deploy completed", re.I)


# Faults that are NORMAL, transient states WHILE building from scratch (you see "cannot find module"
# then `npm install` fixes it; a TS error then you fix the code; a port in use then you free it).
# In a BUILD these only count if they survive UNRESOLVED into the FINAL result — not mid-construction.
# (In a DEPLOY/verification run they always count: a green deploy hiding any of these is a real snake.)
_TRANSIENT_LABELS = {
    "missing module", "TypeScript compile error", "missing tool/command",
    "network/port error", "npm script failed", "connection failure",
}


def scan_hidden_faults(text: str, build: bool = False) -> list:
    """Hunt the FULL run output for danger signatures that an exit-0 can hide. Returns the suspicious
    lines. A non-empty result means: do NOT call it clean-green, even if the exit code was 0.

    build=True → this is a from-scratch BUILD, where transient dev errors (module/TS/tool/port) are a
    normal part of constructing and getting fixed; count those ONLY if they appear in the FINAL result
    (the last lines), i.e. still unresolved at the end. Fatal faults are still flagged anywhere."""
    lines = (text or "").splitlines()
    n = len(lines)
    tail_start = max(0, n - 20)   # the "final result" window
    out, seen = [], set()
    for i, line in enumerate(lines):
        if _BENIGN.search(line):
            continue
        for pat, label in _DANGER:
            if re.search(pat, line, re.I):
                # in a build, a transient dev error that was fixed before the end is NOT a failure
                if build and label in _TRANSIENT_LABELS and i < tail_start:
                    break
                key = (label, line.strip()[:160])
                if key not in seen:
                    seen.add(key)
                    out.append({"label": label, "line": line.strip()[:200]})
                break
    return out


# Excludes a deploy MUST honor (secrets + production data). A proposal that uses --delete without
# these, or a placeholder host, is the exact "config not considered" fake that hit us before.
REQUIRED_EXCLUDES = [".env", ".backup-env", "*.pem", "*.key", "public", "uploads", "prisma/migrations"]


def audit_deploy_proposal(text: str) -> list:
    """Catch a deploy/rsync proposal that IGNORES the real config — the confirmed historical bug:
    placeholder host (mostafa@VM), --delete without the secret/data excludes, or running `az` on
    the VM. Returns the list of problems (empty = the proposal respects the config)."""
    t = text or ""
    probs = []
    if re.search(r"@VM[:/]|@<[^>]+>|@VM\b", t):
        probs.append("placeholder host (mostafa@VM) instead of the real VM IP")
    if "--delete" in t:
        missing = [e for e in REQUIRED_EXCLUDES if e not in t]
        if missing:
            probs.append("rsync --delete WITHOUT required secret/data excludes: " + ", ".join(missing))
    if re.search(r"\baz\b.*(run-command|vm\s)", t) and "ssh" in t.lower():
        probs.append("runs `az` over SSH on the VM (az lives on the Mac, not the VM)")
    return probs


# Directives a prompt may request that are CONFIRMED-BROKEN — the pipeline must override them.
_BROKEN_DIRECTIVES = [
    (r"az\s+vm\s+run-command|control\s+plane",
     "requests the Azure control-plane channel (`az` runs on the Mac, not the VM — this gave "
     "'az: command not found'); the working deploy uses SSH as mostafa"),
    (r"migrate\s+dev",
     "requests `prisma migrate dev` (interactive; RESETS on drift — caused the exit-130 hang); "
     "the working deploy uses `prisma migrate deploy`"),
    (r"migrate\s+reset|--force",
     "references destructive `migrate reset` (wipes data) — only on explicit per-run approval"),
]


def audit_prompt(prompt: str) -> list:
    """Flag instructions in a prompt that are confirmed-broken, so we never silently 'reproduce'
    a result by following a method we already proved fails. Returns the list of problems."""
    t = prompt or ""
    return [msg for pat, msg in _BROKEN_DIRECTIVES if re.search(pat, t, re.I)]


def engine_audit(text: str, evidence: str = "") -> dict | None:
    """Second-opinion auditor — asks the engine to rate fake-risk and list the unverified claims.
    Same 'should I trust this is done?' call I make by hand, automated. Returns dict or None."""
    try:
        import json
        import claude_cli
        if not claude_cli.available():
            return None
        prompt = (
            "You are a strict AUDITOR. Given an agent MESSAGE and the available EVIDENCE, decide "
            "whether the message makes any SUCCESS/COMPLETION claim NOT supported by real evidence. "
            "Intentions, plans, and 'should work' are NOT evidence.\n\n"
            f"MESSAGE:\n{text}\n\nEVIDENCE:\n{evidence or '(none)'}\n\n"
            'Reply ONLY JSON: {"fake_risk":0-1,"unverified_claims":["..."],"verdict":"VERIFIED|UNVERIFIED|FAKE"}')
        raw = claude_cli.ClaudeCLIBrain().respond(prompt, lang="en")
        m = re.search(r"\{.*\}", raw or "", re.S)
        return json.loads(m.group(0)) if m else None
    except Exception:
        return None
