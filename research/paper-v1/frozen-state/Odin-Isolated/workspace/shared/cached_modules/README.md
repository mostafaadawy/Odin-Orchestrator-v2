# Pool of Cached Modules (Fast Actions Library)

A senior engineer doesn't start every task from zero — they reach into a library of proven solutions,
pick the closest match, and adapt it. This folder is that library for our AI agents.

## How agents use it (the rule)
When a role agent (DevOps / Frontend / Backend / …) starts a task, AFTER it understands the
requirements it **fetches this pool** — its own role folder **plus `Miscellaneous/`** — reads each
module's **metadata**, and **decides for itself**:
- if a cached module **matches the case** → adapt its inputs/config and **use it** (fast, proven);
- if nothing fits → just work normally.

The CTO does **not** use the pool directly — only the role agents do, per task.

## Structure
```
cached_modules/
  DevOps/          # cloud/VM/deploy/CLI ops
  Frontend/        # frontend build/scaffold helpers
  Backend/         # backend/api/db helpers
  Miscellaneous/   # generic, not tied to one role yet
```

## Metadata (every script has a sidecar `<name>.meta.json`)
```json
{
  "name": "cloud_deploy.sh",
  "role": "DevOps",
  "summary": "one-line what it does",
  "does": ["bullet", "of", "capabilities"],
  "inputs": {"ENV_VAR": "what it means / default"},
  "status": "working | needs-update | not-working",
  "safety": ["the safe defaults it enforces"],
  "provenance": "where it came from (which real task proved it)"
}
```
`status` tells us at a glance what's safe to reuse and what to fix.

## The rule for ADDING modules (keep the pool clean)
Do **not** pre-create scripts to fill the folder. A module is added **only after it proves itself in a
real task** (like our deployment script did). Then it's generalized, named, documented with metadata,
and dropped in. Only proven, valuable modules belong here — never filler.
