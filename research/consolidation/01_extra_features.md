# Extra features found in Odin (beyond the 11 known ones). Read-only discovery, 2026-10-06

Each feature below lists where it lives in the code, plus one question: should the paper include it? It is a question, not a verdict.

1. **Truth gate.** Any agent message that claims "done" is checked against real evidence (exit codes, tool results), and fake completions are rejected. Lives in `server/audit.py`. Is it part of feature 11 (Audit layer), or its own feature?
2. **Approval gate plus engine-level read-only hook.**
   - Agents run read-only and only propose changes. The project CTO bundles the proposals into ONE approval request.
   - A Claude Code PreToolUse hook blocks writes, installs, migrations, deploys and VM control.
   - Lives in `server/approvals.py` and `server/readonly_hook.py`.
3. **Scoped memory organisation.** Scopes are nested company → project → member. Each scope has its own chat pool, and rolled-up summaries feed upward. Lives in `server/scopes.py`.
4. **Main Task object.** Every prompt becomes ONE persistent shared-state object that the whole run references. Lives in `server/main_task.py`.
5. **Intelligence-first intent routing.** The owner's actual message drives the work, and the project brief acts only as guardrails. Lives in `server/intent.py`.
6. **Per-scope model choice.**
   - A model can be picked per company, per project or per member (cheap local or paid), and the most specific choice wins.
   - Ollama is the offline fallback.
   - Lives in `server/models_config.py` and `server/brain_handler.py`.
7. **Operations record.** Every long task (deploy, sync) is one record that the UI can watch and stop. Lives in `server/operations.py` and `server/deploy_runner.py`.
8. **Self-healing deploy agent.** Deterministic "hands" (`deploy.sh`) are paired with an AI "brain" that diagnoses real failures. Lives in `server/deploy_agent.py`. Is it part of feature 10 (Smart CI/CD)?
9. **Project scheduler.** It runs daily, interval and one-off tasks, with catch-up of missed runs and a periodic approval gate. Lives in `server/scheduler.py`.
10. **SOC blueprint.**
    - It turns ANY project into a full security team.
    - 12 security agents cover hunting, UEBA, intel fusion, prediction, inventory, recovery and quota abuse.
    - Lives in `server/soc_blueprint.py`, `server/soc_*.py` and `workspace/agents/*security*`.
11. **VM Security Sentinel.** It reads the VM sensor facts and gives a red or green daily status. Lives in `server/security_sentinel.py` and the `vm-sentinel` project.
12. **Generic UI contract.** One server-driven contract is used by desktop, web and mobile, so the clients only map data. Lives in `server/ui_api.py`.
13. **Reporting engine.** It produces styled md, docx, pdf and pptx reports, with branding. Lives in `server/report_engine.py`.
14. **Live activity bus.** It drives heartbeat avatars and the agent flow rail (Frontend → Backend → DevOps). Lives in `server/activity.py`.
15. **Capabilities registry.** The CTO knows what is already connected and what it can help connect. Lives in `server/capabilities.py`.
16. **Auth.**
    - The web and mobile apps use hashed passwords, with 2FA and email verification.
    - Anchor management uses a login plus a one-time confirmation code shown on the desktop.
    - Lives in `server/auth.py` and `server/anchor_manage.py`.
17. **Third-party simulator and webhook receiver.** A test harness for the anchor contract. Lives in `server/sim_server.py`, `server/third_party.py`, `server/webhook_receiver.py` and `workspace/anchor-layer/`.
18. **Cache-vs-no-cache run timer.** It measures each task run from start to finish. Lives in `server/run_timer.py`.
19. **Bilingual voice.** English and Arabic speech-to-text and text-to-speech, offline (Kokoro and Coqui XTTS), with Azure TTS as an option. Lives in `voice/backend/*` and `server/app.py`. Is it part of the listed Whisper/TTS item?
20. **WhatsApp-clone mobile mode.** The whole app becomes a chat list of company and project CTO "groups". Lives in `odin_app/lib/screens/whatsapp.dart`. Is this the same as feature 4 (live sync), or a separate UI feature?
21. **Owner's end-to-end test harness.** Real-flow tests, SOC tests and the phase-7 lifecycle tests. Lives in `workspace/shared/testing/*`.

Context for the paper (not a feature): `workspace/docs/RUFLO-COMPARISON.md` (2026-06-21) compares Odin with Ruflo, formerly claude-flow. It records "reliability concerns" in its §8 and an explicit "NOT a swarm" decision (ADR-005 in `orchestrator/dispatcher.py`).
