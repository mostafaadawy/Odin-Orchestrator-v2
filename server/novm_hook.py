#!/usr/bin/env python3
"""PreToolUse hook (F-32c, owner rule 2026-10-11: VM access must FAIL SAFE).
Active only when the run was NOT clearly asked for VM work (env ODIN_NO_VM=1, set by the orchestrator).
Blocks any Bash command that would reach the VM or Azure: ssh/scp/sftp/sshpass/rsync to a remote, az CLI,
the VM's address, or Odin's own VM helpers. The agent is told to propose the VM step for the owner's approval.
Decisions are appended to workspace/history/novm-hook.jsonl."""
import sys, os, json, re, time, pathlib
VM_RX = [r"\bssh\b", r"\bscp\b", r"\bsftp\b", r"\bsshpass\b", r"\brsync\b[^|;&]*\S+:\S*", r"(^|[\s;&|(])az\s",
         r"\b52\.180\.154\.225\b", r"\bdjango-vm\b", r"\b(infra_rotate|deploy_ssh|_ensure_vm_access|vm_password)\b"]
_RX = [re.compile(p, re.I) for p in VM_RX]
def main():
    if os.environ.get("ODIN_NO_VM") != "1":
        sys.exit(0)
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    if data.get("tool_name") != "Bash":
        sys.exit(0)
    cmd = (data.get("tool_input") or {}).get("command", "") or ""
    hit = next((p.pattern for p in _RX if p.search(cmd)), None)
    if not hit:
        sys.exit(0)
    try:
        root = pathlib.Path(os.environ.get("ODIN_ROOT") or pathlib.Path(__file__).resolve().parent.parent)
        (root / "workspace" / "history").mkdir(parents=True, exist_ok=True)
        with open(root / "workspace" / "history" / "novm-hook.jsonl", "a") as f:
            f.write(json.dumps({"ts": time.time(), "actor": os.environ.get("ODIN_ACTOR_PID", ""),
                                "decision": "block", "rule": hit, "cmd": cmd[:300]}) + "\n")
    except Exception:
        pass
    print("[Odin VM rule] BLOCKED: this run was not clearly asked to work on the VM, so it has no VM access. "
          "Do NOT retry or work around this. If a VM step is really needed, PROPOSE it (as a proposal block) "
          "for the owner's approval.", file=sys.stderr)
    sys.exit(2)
if __name__ == "__main__":
    main()
