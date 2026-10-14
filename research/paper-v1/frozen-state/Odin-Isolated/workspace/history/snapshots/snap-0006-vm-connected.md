# Snapshot: snap-0006-vm-connected
**Created:** 2026-06-22 · **By:** CTO Brain
**Reason:** First REAL Azure VM connection verified.

## State
- VM: django-vm / RG DJANGO-PROJECT / centralus. Status = connected.
- Method: az vm run-command (Azure agent, root) — no SSH/key/IP needed. infra_az.py + /infra/connect-test.
- Verified: listed /home/mostafa (organics, bendcore + other projects).
- Engine: Claude CLI with terminal access (Bash) for self-solving infra tasks; approval gate guards changes.

## Next
- IP rotation (needs NSG + SSH-rule names) for scp path.
- .env-safe deploy (scp code to ~/organics, ~/Bendcore excluding .env; rebuild via az run-command).
- Wire VM commands into the cockpit (natural language).
