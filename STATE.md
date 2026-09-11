# Project State

## Current State

- Phase: Implementation design
- Repository: `FTP-Project`
- Repo URL `https://github.com/maksimsavrilov/FTP-Project.git`
- Last verified commit: `2168fc73cff8a0c5fcc544510f256c57d961cbe0`
- Current focus: Master, Auth Service, Agents and reconciliation boundaries
- Status: Master persistence slice implemented and verified

---

## Architecture Invariants

These decisions are established and must not be changed without explicit
architecture review.

- Master is the control plane and the source of desired state.
- Worker Nodes are the execution plane.
- Master communicates with Worker Agents via REST/HTTP.
- Worker Agents never communicate directly with each other.
- Worker services have dedicated Agents:
  - Web Agent
  - DNS Agent
  - Mail Agent
  - DB Agent
- Master owns scheduling and service placement.
- Agents reconcile desired state with local actual state.
- Desired State and Actual State are separate representations.
- Service placement is represented by `ServiceAssignment`.
- A Service does not directly own a Worker Node.
- Master monitors Worker Nodes but does not perform automatic failover.
- Infrastructure is responsible for HA/failover.
- Planned cluster size: up to 1000 Worker Nodes.
- CLI is the primary interface.
- UI is a wrapper over the CLI.
- Master and Agents use Python/FastAPI.
- PostgreSQL is the Master state database.

---

## Completed

### Architecture

- Control plane / execution plane model defined.
- Master container architecture defined.
- Worker Agent architecture defined.
- Separate Web, DNS, Mail and DB Agents defined.
- Worker Node deployment model defined.
- Node lifecycle defined.
- Service lifecycle defined.
- Desired State / Actual State model defined.
- ServiceAssignment model defined.
- Scheduler responsibilities defined.
- Reconciliation responsibilities defined.
- Worker Node registration flow defined.
- Worker Node monitoring flow defined.
- User creation flow defined.
- Hosting Plan creation flow defined.
- Subscription creation flow defined.
- Web Service Creation flow validated.
- Master SQLAlchemy models and repositories for WorkerNode, ServiceAssignment, DesiredState and ActualState implemented and validated.
- Persistence repository transaction boundary reviewed against the next Master slice; repositories now flush within caller-owned transactions and lock mutable rows for PostgreSQL concurrency.
- Master placement application-service transaction contract implemented; placement, assignment replacement and desired-state version updates now commit atomically.

### C4 / Structurizr

- System Context view defined.
- Container view defined.
- Production Deployment view defined.
- Master Component view defined.
- Web Agent Component view defined.
- DNS Agent Component view defined.
- Mail Agent Component view defined.
- DB Agent Component view defined.
- Worker Node infrastructure nodes defined.
- Node registration dynamic views defined.
- User Creation dynamic view defined.
- Hosting Plan Creation dynamic view defined.
- Subscription Creation dynamic view defined.
- Service Creation system-level dynamic view defined.
- Service Creation Master component-level dynamic view defined.
- Node Monitoring dynamic view defined.
- Service Creation internal view is included from `views.dsl`.
- Final consistency review of C4, dynamic views and domain model completed.
- Structurizr DSL relationships and dynamic-view scopes validated.
- Implementation boundaries for Master, Auth Service, Worker Agents, persistence and ServiceAssignment reconciliation defined in `docs/implementation-boundaries.md`.
- Master persistence schema and repository boundaries for WorkerNode, ServiceAssignment, DesiredState and ActualState defined in `docs/master-persistence.md`.
- Shared API schemas and the Master-to-Authentication Service client contract defined in `docs/api-contracts.md`.
- Master REST API resource schemas and handler boundaries defined in `docs/master-api.md`.

### Domain Model

- Business domain model separated from C4 model.
- User → Subscription → ServicePlan model defined.
- Domain → Website / DNS / Mail model defined.
- Service hierarchy defined.
- WebService, DnsService, MailService and DatabaseService defined.
- ServiceAssignment defined as explicit placement entity.
- WorkerNode defined with capacity and health information.
- DesiredState and ActualState defined as separate entities.

---

## Known Issues

None identified in the validated architecture scope.

---

## Current Task

Master REST API resource schemas and handler boundaries are defined. The
contract covers client-facing resources, Worker Agent reports, transaction
ownership, authentication, and HTTP error mapping.

---

## Next Step

Define Master application services for the documented REST handlers.

---

## Verification Rules

Before changing architecture:

- Verify the current repository state.
- Treat this file as project execution state, not as historical documentation.
- Treat Structurizr as the canonical C4 architecture model.
- Treat `docs/domain-model.md` as the canonical business-domain model.
- Do not infer architecture from obsolete README diagrams when they conflict
  with the canonical models.
- Validate Structurizr identifiers and dynamic-view scopes.
- Check every included DSL file.
- Keep Agent-to-Agent communication prohibited.
- Keep scheduling and placement in Master.
- Keep reconciliation between desired and actual state explicit.

---

## Change Policy

After completing a task:

1. Update `Completed`.
2. Remove resolved items from `Known Issues`.
3. Update `Current Task`.
4. Define exactly one `Next Step`.
5. Update `Last verified commit`.
6. Commit the state together with the corresponding project changes.

Do not use this file as a changelog.

Historical information belongs in Git history.