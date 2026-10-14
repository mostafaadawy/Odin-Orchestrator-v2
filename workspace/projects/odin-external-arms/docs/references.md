# External Arms — code references (the arm points to where each part runs; nothing is moved)
- backend / API       -> server/            (the brain, FastAPI)
- orchestrator brain  -> orchestrator/      (dispatcher.py, semantic_router.py) — routing/dispatch, imported by server via sys.path
- voice backend       -> voice/backend/     (imported by server via sys.path)
- desktop             -> desktop/           (Electron + React)
- web + mobile        -> odin_app/          (Flutter)
- anchor (runtime)    -> server/anchor_remote.py  +  workspace/anchor-layer/  (queue/mirror/sync)

Doctrine: the CTO Brain Operating Manual is workspace/shared/directions/ORCHESTRATOR.md
Shared tooling it USES (not owns): workspace/shared/infra/ (deploy), testing/, workspace/shared/ (directions, config, utils, registry).
PROTECTED: type=arm, cannot be deleted or split.
