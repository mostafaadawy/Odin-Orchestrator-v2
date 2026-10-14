# Specialized Agent Team

The CTO Brain coordinates six specialized agents. Each file defines a role's mission,
scope, triggers, hand-offs, and the rules it must honor. The orchestrator decides when to
activate each agent and is accountable for the combined result.

| Agent | File | Activated when… |
|-------|------|-----------------|
| Frontend | `frontend.agent.md` | UI, components, styling, web/mobile client |
| Backend | `backend.agent.md` | APIs, services, business logic, integrations |
| DevOps & Cloud | `devops-cloud.agent.md` | Azure, VM, deploy, SSL, config, networking, CI/CD |
| Security & Compliance | `security-compliance.agent.md` | PII/PHI/payments, auth, audit, compliance |
| QA & Testing | `qa-testing.agent.md` | tests, regression risk, release readiness |
| Database | `database.agent.md` | schema, migrations, queries, data modeling |

**Veto rule:** Security & Compliance can block any change touching sensitive data.
All agents must read `workspace/shared/directions/core-rules.md` before acting and operate behind the approval gate.
