# Runbook: Revert to a History Snapshot

**Owner agent:** CTO Brain · **Gate:** APPROVAL REQUIRED (state-changing).

## Concept
Snapshots in `history/snapshots/` are named restore points (`snap-NNNN-<slug>`). Each captures
the orchestrator project state and a manifest of key files at that time. History is the source
of truth for *why* a state existed.

## Steps
1. **Identify** — list snapshots; the owner picks a target (or describes the desired point).
2. **Diff** — show what will change between current state and the target snapshot.
3. **Approval** — raise `APR-NNNN` (category `config-change`) with the diff + rollback (a fresh
   snapshot of the current state is taken first, so the revert is itself reversible).
4. **Restore** — apply the snapshot's files/state.
5. **Verify** — confirm integrity; run relevant checks.
6. **Log** — REVERT entry in history with from/to snapshot IDs.

## Safety
A pre-revert snapshot is ALWAYS taken first, so any revert can itself be undone.
