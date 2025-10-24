# System Design: Aristotle-I Agentic System

**Author:** Debabrata Das  
**Last Updated:** 2025-10-24  
**Status:** Draft  
**Location:** `DESIGN.md`

## Revision History
- 2025-10-24 — Expanded architecture, security, testing, rollout, metrics, alternatives, and operational playbook.

## Executive Summary
Aristotle\-I is a multi\-agent, Human\-in\-the\-Loop (HITL) autonomous software engineering assistant. It integrates with Jira, GitHub, and SonarQube and leverages multiple LLMs to automate planning, code generation, review, and documentation while preserving human oversight. This document describes system goals, architecture, data and security models, operational procedures, testing and rollout plans, monitoring, and alternatives.

## Goals
- Automate repetitive SDLC tasks while preserving human control.
- Increase developer productivity and consistency.
- Improve code quality using automated reviews and policy enforcement.
- Produce standardized, traceable documentation for audited changes.

## Non\-Goals
- Replace human architects or project managers.
- Provision cloud infrastructure, run CI/CD pipelines, or perform deployments.
- Fully autonomous, unsupervised production commits.

## Terminology
- Agent: A software component that performs a discrete responsibility (Planner, Developer, Reviewer, Assembler).
- HITL: Human\-in\-the\-Loop — explicit points where a human reviews and approves.
- LLM Service: Abstraction endpoint that routes prompts to one or more LLM providers.
- MAX_REBUILD_ATTEMPTS: System threshold to escalate human attention when automated loops fail.

## Use Cases
1. New Jira issue triggers plan creation; human reviews and approves plan; code is generated and iteratively reviewed.
2. Existing PR needs automated augmentation and documentation generation.
3. Codebase-wide refactor suggested by system with human approval and staged execution.

## Architecture Overview

```mermaid
graph TD
  subgraph Human
    HD[Human Developer]
    User[End User/PM]
  end

  subgraph External
    Jira[Jira]
    GitHub[GitHub]
    Sonar[SonarQube]
  end

  subgraph Core
    Planner(Planner Agent)
    Developer(Developer Agent)
    Reviewer(Reviewer Agent)
    Assembler(Assembler Agent)
    LLM(LLM Service)
    DB[(MongoDB)]
    KB[(Knowledge Base \(.md files\))]
  end

  User -->|Creates Issue| Jira
  Jira -->|Task Ingestion| Planner
  Planner -->|Plan| HD
  HD -->|Approve/Feedback| Planner
  Planner -->|Approved Plan| Developer
  Developer -->|Code Changes| GitHub
  Developer -->|Request Review| Reviewer
  Reviewer -->|Static Analysis| Sonar
  Reviewer -->|Consult| KB
  Reviewer -->|Persist Report| DB
  Reviewer -- Fail --> Developer
  Reviewer -- Pass --> Assembler
  Assembler -->|Docs| KB
  HD -->|Final Approval| GitHub
  LLM <-->|Used by| Planner & Developer & Reviewer & Assembler
```

## Component Breakdown
- Planner Agent: Creates decomposed, testable tasks and acceptance criteria. Produces plan artifacts for UI review.
- Developer Agent: Generates and modifies code, tests, and changelogs. Produces commits/PRs to `GitHub`.
- Reviewer Agent: Runs automated code review using LLM reasoning, rules engines, and SonarQube signals. Produces review reports and remediation suggestions.
- Assembler Agent: Consolidates design notes, documentation, and changelogs into standardized Markdown artifacts stored in the Knowledge Base.
- LLM Service: Provider-agnostic prompt orchestration, response sanitization (e.g., `json_repair`), and rate / cost controls.
- Database (MongoDB): Stores plans, review reports, audit logs, and system state.
- UI (React): HITL console for plan review, code review, feedback, and approvals.

## Data Model (high level)
- Task
  - id, jira_id, status, created_by, assigned_agent, plan_id
- Plan
  - id, task_id, steps[], estimated_time, approvals[]
- ChangeSet / Patch
  - id, files_changed[], diff, tests_added[]
- ReviewReport
  - id, changeset_id, score, issues[], sonar_summary
- AuditEvent
  - id, type, actor, timestamp, payload

## Interfaces & APIs
- Jira Connector: Ingests webhooks; maps issue fields to Task model.
- GitHub Connector: Create branches, PRs, comments; minimal PAT scope (repo:status, repo:pull).
- SonarQube Connector: Fetch static analysis results; influence Reviewer scoring.
- LLM Service API: Prompt templates, request throttling, provider fallback.

API contract examples (conceptual):
- POST /api/v1/tasks — create task (from Jira)
- GET /api/v1/tasks/{id}/plan — retrieve generated plan
- POST /api/v1/tasks/{id}/plan/approve — human approval
- POST /api/v1/changesets/{id}/approve — final approval / push

## Security
- Secrets: No plaintext secrets in repos. Use environment variables for local development and a secrets manager (Vault, AWS Secrets Manager, etc.) in production.
- GitHub PAT: Least privileges; use short lived tokens where possible.
- LLM access: Rate limits, usage quotas, and prompt logging; redact PII before logging.
- Input Sanitization: Sanitize and validate all external inputs (Jira, PR descriptions); apply prompt injection mitigation.
- Audit & Tamper Evidence: Immutable audit logs for plan approvals and final commits persisted to MongoDB and optionally exported to an SIEM.
- RBAC: UI roles for Reviewer, Developer, Admin; operations gated by role checks.

## Reliability, Resilience & Scalability
- Stateless Agents: Agents are mostly stateless; state persisted in DB to allow horizontal scaling.
- Retry & Backoff: Exponential backoff for transient LLM/provider and GitHub errors.
- Circuit Breaker: Disable automated commit flows on repeated failures and alert humans.
- Worker Pool: Reviewer processes files in parallel; tune pool size based on CPU & rate limits.
- Graceful Degradation: If LLM provider fails, switch to fallback and notify humans.

## Testing Strategy
- Unit Tests: Core business logic, prompt templates, response parsing, connectors.
- Integration Tests: GitHub and Jira mocks; SonarQube integration through test instances.
- End\-to\-End Tests: Simulate complete workflow from Jira ingestion to final approval in a staging environment.
- Security Tests: Static Application Security Testing (SAST), dependency scanning, and secret scanning.
- CI: `pip` and `npm` tasks for Python and front\-end; run tests in PRs and block merges on failures.

## Monitoring & Observability
- Metrics:
  - Task throughput, mean time to approval, average review cycles, LLM usage and cost, failure rates.
- Logs:
  - Structured logs (JSON), request traces, LLM prompt/response hashes (not raw content unless redacted).
- Tracing:
  - Distributed tracing for agent workflows to measure latency across components.
- Dashboards & Alerts:
  - UI dashboard for ongoing tasks, alerts for MAX_REBUILD_ATTEMPTS exceeded, provider outages, and anomalous cost spikes.

## Operational Playbook
- On failed review loop > MAX_REBUILD_ATTEMPTS: Notify on-call, pause pipeline for task, show detailed diff and reviewer reports.
- On LLM provider outage: Switch to fallback provider; if none available, enter manual mode and notify team.
- Incident Response: Runbook for credential compromise, data breach, and malicious plan detection.

## Rollout & Migration Plan
1. Alpha: Internal-only, limited teams, no automatic commits (human must merge).
2. Beta: Wider engineering teams, allow automated PR creation, still require human merges.
3. Controlled Production: Allow selective automatic merges for low-risk changes (docs, tests) with feature flags.
4. Full Production: Expand scope incrementally and continuously monitor.

## Metrics & Success Criteria
- 20\% reduction in developer time on routine tasks within 3 months.
- Mean cycles per task \< 2 for typical features.
- Review false\-positive rate \< 5\% compared to human reviewers.
- No critical vulnerabilities introduced by automated changes.

## Privacy & Compliance
- PII: Detect and redact PII from prompts/responses and persisted items.
- Retention: Define retention policy for audit logs and LLM transcripts.
- Compliance: Ensure data transmission complies with organizational policies and regional regulations (GDPR, etc.).

## Alternatives Considered
- Fully Autonomous System: Rejected due to safety and accountability concerns.
- Monolithic Agent: Rejected for maintainability and testability reasons.
- Human-Only Review: Too slow and not scalable for high-volume repetitive tasks.

## Risks & Mitigations
- Risk: LLM hallucinations cause incorrect code. Mitigation: enforce tests, static analysis, and human approvals.
- Risk: Prompt injection via Jira. Mitigation: sanitize inputs and require human plan approvals.
- Risk: Cost overruns from LLM usage. Mitigation: cost monitoring, provider throttling, and caching.

## Open Questions
- Optimal granularity for Planner steps (task size tradeoffs).
- Best signal mix for Reviewer scoring (LLM judgment vs. Sonar metrics).
- Versioning strategy for prompt templates and LLM model pinning.

## Appendix
- Prompt Governance: store prompt templates in the Knowledge Base with version metadata.
- Environment: Use `.env` for local dev, secrets manager for production.
- CI/CD: Linting and tests run in PR pipeline; policy checks block merges.
