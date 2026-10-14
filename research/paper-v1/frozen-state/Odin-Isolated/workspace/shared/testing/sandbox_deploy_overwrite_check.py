"""
sandbox_deploy_overwrite_check.py — Test 5: DEVOPS-AGENT REDEPLOY / OVERWRITE proof on the SANDBOX Azure VM.

DYNAMIC (not fixed commands): a REAL DevOps AGENT performs the redeploy. The harness only (a) sets up a
versioned marker, (b) hands the agent a UNIQUE per-run token, then (c) INDEPENDENTLY reads the file back
off the VM over SSH to confirm the agent's redeploy actually replaced old→new. Because the token is unique
each run and the agent — not the harness — runs the deploy, this FAILS if the agent doesn't really do the
work or if the deploy/overwrite logic breaks (exactly the guarantee the owner asked for: it is not static).

Flow the DevOps agent must perform (its own commands, per its DevOps rules):
    deploy the sandbox folder to the VM → EDIT the marker to the given token → REDEPLOY (rsync --checksum)
    → confirm over SSH the VM now serves the NEW token.
Then the harness re-reads the marker on the VM: PASS only if the VM shows the exact per-run token.

SANDBOX VM PATH ONLY (/home/mostafa/sandbox-revealer) — never the production folders (organics/bendcore/
django). If the VM is unreachable this run, the test is SKIPPED (not failed) so infra never yields a false red.

Run:  python3 testing/sandbox_deploy_overwrite_check.py     (or via the loop with filter 'overwrite')
"""
from __future__ import annotations

import sys
import time
import uuid
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import harness  # noqa: E402
from harness import log  # noqa: E402

SBX = pathlib.Path("/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Isolated/_external/OdinTesting") / "deploy-overwrite-sandbox"
VM_SANDBOX = "/home/mostafa/sandbox-revealer"       # sandbox path on the VM — NEVER production
MARKER = "REDEPLOY_MARKER.txt"


def _vm_reachable() -> bool:
    try:
        import deploy_ssh
        r = deploy_ssh.ssh_exec("echo ok")
        return bool(r.get("ok")) and "ok" in (r.get("out", "") or "")
    except Exception:
        return False


def main() -> int:
    import deploy_ssh
    log("=" * 74)
    log("SANDBOX — DevOps-AGENT REDEPLOY / OVERWRITE proof (agent redeploys; VM must show the NEW token)")
    log("=" * 74)
    SBX.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    v1 = f"v1-{ts}"
    v2 = f"v2-{ts}-{uuid.uuid4().hex[:8]}"           # UNIQUE per-run token the agent must put on the VM
    (SBX / MARKER).write_text(v1 + "\n", encoding="utf-8")
    (SBX / "app.txt").write_text("sandbox redeploy app\n", encoding="utf-8")
    log(f"  local sandbox: {SBX}   (marker starts as {v1})")
    log(f"  VM sandbox path (never production): {VM_SANDBOX}")
    log(f"  per-run token the agent must land on the VM: {v2}")

    # If the VM is unreachable, SKIP (do not fail on infra).
    if not _vm_reachable():
        log("  ⏭  SKIPPED — VM not reachable this run (cannot prove the agent redeploy). Re-run when reachable.")
        harness.SeedingPrompt.run(project_ids=[], passed=True)
        return 0

    # Register a real Test 5 PROJECT (seeds a signature like the other tests) — a DevOps redeploy project.
    import projects, main_task
    proj = projects.create_project(
        name="Deploy Overwrite (redeploy)",
        description=("Test 5 — DevOps redeploy overwrite proof on the sandbox VM. DevOps deploys the sandbox "
                     "folder, changes a marker, redeploys via rsync --checksum, and confirms the VM serves the "
                     "NEW content. Sandbox path only — never production."),
        ptype="deployment", mode="deploy",
        members=[{"name": "DevOps", "role": "DevOps & Cloud", "nature": "technical"}], local_path=str(SBX))
    pid = proj["id"]
    log(f"  ✓ Test 5 project registered: {pid}")

    goal = (
        "SANDBOX REDEPLOY — prove a redeploy OVERWRITES old files with new on the VM (not just adds missing).\n"
        f"The folder {SBX} is a small sandbox app containing {MARKER} (currently '{v1}').\n"
        "Do this yourself with your DevOps tools (SSH as mostafa, rsync --checksum), verifying each command:\n"
        f"  1) Deploy {SBX} to the VM sandbox path {VM_SANDBOX} (rsync --checksum). Never touch production "
        "folders (organics/bendcore/django).\n"
        f"  2) EDIT {SBX}/{MARKER} so its content becomes EXACTLY: {v2}\n"
        f"  3) REDEPLOY {SBX} to {VM_SANDBOX} again (rsync --checksum) so the changed marker overwrites the old.\n"
        f"  4) CONFIRM over SSH that {VM_SANDBOX}/{MARKER} on the VM now shows EXACTLY '{v2}'.\n"
        "Report the real SSH output proving the VM shows the new token.")

    _owner_ans = ("Use your default Azure/SSH credentials from oth/.cred (azvmcred) — I am not providing a "
                  "different key. Sandbox path only. Proceed; you have everything needed.")
    log("\n[run] DevOps AGENT performs deploy → change → redeploy → confirm …")
    res = harness.run_flow_monitored(pid, goal, per_step=600, hard_cap=1800,
                                     owner_answer=_owner_ans, plan_check=False)
    finished = res.get("ok", False)

    # INDEPENDENT verification: re-read the marker off the VM ourselves. PASS only if the agent's redeploy
    # actually landed the unique token on the VM (proves a real overwrite by the agent, not a claim).
    seen = ""
    try:
        g = deploy_ssh.ssh_exec(f"cat {VM_SANDBOX}/{MARKER} 2>/dev/null")
        seen = (g.get("out", "") or "").strip()
    except Exception as e:
        log(f"  ! could not read the VM marker: {e}")
    overwrote = (seen == v2)
    try:
        main_task.append(pid, "DevOps", f"[Test 5 redeploy] VM {MARKER} now shows: '{seen}' (expected '{v2}')")
    except Exception:
        pass

    whos = harness.voices(pid)
    devops_worked = any("devops" in w.lower() for w in whos)
    truthful, snakes = harness.truthfulness(pid)

    log("=" * 60 + "\n  STRONG SCORECARD\n" + "=" * 60)
    s1 = harness.scoreline("AGENT REDEPLOY OVERWROTE OLD → NEW ON THE VM (independent SSH read)",
                           overwrote, f"VM marker='{seen}' expected='{v2}'")
    s2 = harness.scoreline("DEVOPS AGENT ACTUALLY DID THE REDEPLOY (dynamic, not fixed commands)",
                           devops_worked, f"voices={sorted(whos)}")
    s3 = harness.scoreline("TRUTHFUL (no fake success)", truthful, f"snakes={snakes or 'none'}")
    s4 = harness.scoreline("RUN COMPLETED IN TIME", finished, res.get("reason", ""))
    ok = s1 and s2 and s3 and s4

    log("\n" + ("  ✅ DEPLOY-OVERWRITE PASSED — the DevOps AGENT redeployed and the VM really shows the NEW token"
                if ok else "  ❌ DEPLOY-OVERWRITE FAILED — the VM did not end up with the agent's new token"))
    harness.SeedingPrompt.run(project_ids=[pid], passed=ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
