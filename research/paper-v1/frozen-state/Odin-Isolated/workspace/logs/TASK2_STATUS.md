# TASK2 STATUS — Real Deployment & Diagnosis (Organics) + Agent Scope
STEPS 1-4 DONE & PROVEN (audit=0, 0 regressions, existing projects untouched):
- S1 read+map: services Veeqo/Klaviyo/HubSpot; keys seeded in organics DB runtime_settings (getVeeqoConfig/getKlaviyoConfig/getHubspotConfig); Veeqo bug lead = veeqo-order-sync getOrderLifecyclePollMs/cron.
- S2 preserve: old project backed up (OLD_ORGANICS_PROD_DEPLOY_FULL.json); shared deploy rules intact (dynamic-IP->SSH mostafa->deploy->approved rebase); scripts present.
- S3 new project real-deployment-and-diagnosis-organics-07d7 (full charter); old+stray removed.
- S4 agent scope: agent_scope table + agent_scope_guard (delta-first->default, credential_source, read-only, non-blocking); bindings Fulfillment/Email/HubSpot; agents HubSpot+CloudDebug registered + added to project; dual-scope injection binding-gated in _run_gated; external single-file rule (external_report table + write_external_report enforces one path); PROTECTED_PROJECTS repointed; audit=0.
BACKUPS: *.bak_task2_step4 for workspace_mw.py, workspace_audit.py, api_v2.py, agents_registry.py, projects.py.
REMAINING (execution phase):
- S5 rebuild deployment-project TEST: deploy(no-op, no changed files) + agent-scope tests + real Veeqo scenario + fake Klaviyo/HubSpot (real-close, read-only, report-only).
- S6 produce report to VolatileWorkSpace/AI_DIAGNOSIS_REPORT.md (single file).
- S7 run as owner, iterate to 0 violations/cross/scope incl agent scope.
- S8 real Veeqo diagnosis; final report = ONLY the real issue (overwrite test reports).

STEPS 5-8 DONE (real):
- S5 deploy assertion: rsync dry-run = 0 files to transfer (no modified files) -> NO deploy. Flow OK (dynamic-IP->SSH mostafa), 14 ok/0 fail.
- S6/S8 REAL Veeqo diagnosis (read-only VM+DB): order id=6 PAID; veeqo_order_id=1959471694 set but veeqoShipmentId EMPTY; poller running (lastChecked today, ~1h interval); shippingDecisionEndsAt expired 2026-07-17. Root cause = shipment never resolved / decision-window gate. Single report written to VolatileWorkSpace/AI_DIAGNOSIS_REPORT.md via enforced single-file writer.
- Audit=0; agent scope + external-file rule live; existing projects untouched.

TEST PHASE DONE (live agent-scope, real engine runs): 6/6 pass.
- Fulfillment(Veeqo real)=delta; Email/Klaviyo fake1+fake2=delta; HubSpot fake1+fake2=delta; Analytics(unbound control)=default. All read-only (propose-not-execute).
- Delta exercised live (agents report credential_source=delta); default fallback confirmed for unbound. Audit=0 after test. Final report = single real Veeqo issue only.
TASK COMPLETE.

CAVEAT-1 CLOSED: real production _run_gated (api_v2:983) run live -> Fulfillment reported credential_source=delta, read-only. Audit still 0. Only remaining item is by-design: deploy-on-modify not triggered because organics code is intentionally unmodified here (other chat modifies; then deploy triggers).
ALL REQUIREMENTS MET.
