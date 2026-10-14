# Odin — Testing

The restructured E2E suite. Every test has a **descriptive name** stating exactly what it does, and
every test uses `harness.py` for: smart time limits, automatic CTO-dialog handling, and the post-test
**"clean up or keep as seeding?"** prompt. The shared context pool is always preserved.

## Tests

| File | What it is | Safety |
|------|-----------|--------|
| `real_production_deploy_devops_only.py` | **REAL** production deploy of organics/bendcore to the live Azure VM, DevOps-only (CTO is manager). Uses the owner's exact deploy prompt verbatim. | ⚠️ **DESTRUCTIVE** — wipes prod DB + reboots. Only runs with `ODIN_TEST_PROD_DEPLOY=1`. |
| `readonly_shipping_vq_status.py` | Shipping/Veeqo (VQ) project, Shipping agent only, **no folder required**. Reads status, total orders, channels/vendors. | ✅ read-only |
| `readonly_email_klaviyo_workflows.py` | Email/Klaviyo project, Email agent only (no DevOps). Reads live/draft/total workflows, metrics, lists. | ✅ read-only |
| `sandbox_revealer_multiagent.py` | **"Revealer"** — full multi-agent build → QA → deploy to a **sandbox** (CTO+Frontend+Backend+QA+Shipping+Email). Uses `/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Isolated/_external/Odin Testing/{frontend,backend}-sandbox`. | ✅ sandbox only |

## Run

```bash
# safe ones (read-only + sandbox)
python3 testing/readonly_shipping_vq_status.py
python3 testing/readonly_email_klaviyo_workflows.py
python3 testing/sandbox_revealer_multiagent.py

# the REAL production deploy (only when you truly mean it):
ODIN_TEST_PROD_DEPLOY=1 python3 testing/real_production_deploy_devops_only.py
```

Non-interactive seeding control: `ODIN_TEST_KEEP=1` (always keep data) or `ODIN_TEST_CLEAN=1` (always
clean) skips the prompt.

## Removing the OLD suite

The old `server/e2e_*.py` files are superseded by this folder. No production code imports them. Remove
them on your Mac (the agent sandbox can't delete files on the mounted folder):

```bash
cd /Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Isolated/server && rm -f \
  e2e_ai_capability.py e2e_anchor.py e2e_anchor_all.py e2e_anchor_http.py e2e_anchor_live.py \
  e2e_cache_timing.py e2e_phase1_hard_deploy.py e2e_phase1_shared_context.py e2e_phase1_strong.py \
  e2e_phase2.py e2e_phase2_gate.py e2e_real_deploy.py e2e_smart_configurable_deploy_reask_audit.py \
  e2e_user_test.py && rm -rf __pycache__/e2e_*
```
