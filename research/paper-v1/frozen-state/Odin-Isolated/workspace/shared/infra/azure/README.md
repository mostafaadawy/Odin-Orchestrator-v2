# Azure VM Connection Framework

**Status:** framework ready · **awaiting owner-provided access details** before any connection.

Since no dedicated Azure MCP connector exists, the orchestrator interacts with the VM through
the **sandboxed shell over key-based SSH**, and **every command is approval-gated**.

## How access will work (once you provide details)
1. You give: VM host/IP (or DNS), SSH user the orchestrator may use, OS, and how the SSH key
   is supplied. **Do not paste private keys into chat** — see "Secrets" below.
2. I record a non-secret connection profile in `connection.profile.json` (host, user, port — no keys).
3. The DevOps agent proposes the first read-only command (e.g. `uname -a`, `df -h`) as an
   approval request so you can see exactly what runs.
4. Only after your approval does anything execute against the VM.

## Secrets — never in chat or history
- Private keys / passwords are NOT stored in this repo and NOT pasted in chat.
- Preferred: key already present in your environment / SSH agent; or a path you control.
- The audit log records *that* a command ran and its purpose — never the credentials.

## Respecting your posture
- Closed ports and IP allowlist are honored. No exposure change without a dedicated approval.
- Your existing synchronization method is respected and augmented, never replaced.

## What I need from you to activate Phase 5
- VM host/IP or DNS name and SSH port
- The SSH username the orchestrator may use (least-privilege preferred)
- OS + distro (e.g. Ubuntu 22.04)
- How the SSH key is made available to the shell (agent, mounted path, etc.)
- Confirmation of your current sync/deploy method to respect
