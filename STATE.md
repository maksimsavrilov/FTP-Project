# Project State

## Current State

- Phase: Implementation
- Repository: `FTP-Project`
- Repo URL `https://github.com/maksimsavrilov/FTP-Project.git`
- Last verified commit: `78cd5a229caf93e99626e956c9e52c18e57fd320`
- Current focus: Master, Auth Service, Agents and reconciliation boundaries
- Status: Production Compose stack is running and the user-facing authentication foundation is implemented, including access-token validation, introspection, and CLI user sessions

---

## Architecture Invariants

These decisions are established and must not be changed without explicit
architecture review.

- Master is the control plane, single orchestration entry point and the source of desired state.
- Worker Nodes are the execution plane.
- Master communicates with Worker Agents via REST/HTTP.
- Communication between services uses REST APIs.
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
- CLI commands must use the REST API rather than directly accessing service internals.
- UI is a wrapper over the CLI.
- Master and Agents use Python/FastAPI.
- PostgreSQL is the Master state database.
- Changes must preserve the existing architecture documented in Structurizr.

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
- Canonical domain model expanded with Administrator, Reseller, Customer,
  identity references, resource entitlement inheritance, lifecycle separation,
  Master/Agent ownership, and Plesk reference classification.
- Domain model roadmap aligned with the current implementation state and kept
  separate from the canonical Structurizr C4 model.

### Completed Steps

- Master application services for node operations, placement, and reconciliation reports implemented and verified.
- Master API schemas and handlers for node reads, heartbeats, reconciliation-state reads and actual-state reports implemented and verified.
- ServicePlan persistence model, repository, lifecycle application service, and API create/read boundary implemented and verified.
- Master Authentication Client implemented with response validation, bounded timeout/retries, request ID propagation, and API dependency error mapping.
- Master composition root implemented and verified; it wires the production SQLAlchemy session factory and Authentication Client into the existing Master API and FastAPI adapter.
- First Master business resource implemented: User persistence, transactional lifecycle service, and API create/read boundary with request validation and response serialization.
- Subscription persistence, transactional lifecycle service, and API create/read boundary implemented with owner validation, request validation, and response serialization.
- Domain persistence, transactional lifecycle service, and API create/read boundary implemented with subscription validation, request validation, and response serialization.
- Service persistence, transactional creation with node placement and desired state, and API aggregate create/read boundary implemented and verified.
- Website persistence, transactional lifecycle service, and API create/read boundary implemented with domain validation.
- WebService typed configuration persistence, atomic creation on the common Service lifecycle, and API create/read boundary implemented and verified.
- DnsService typed resource persistence, atomic creation on the common Service lifecycle, and API create/read boundary implemented and verified.
- MailService typed resource persistence, atomic creation on the common Service lifecycle, and API create/read boundary implemented and verified.
- MailDomain persistence model, repository, transactional lifecycle service, and API create/read boundary implemented and verified.
- MailAccount persistence model, repository, transactional lifecycle service, and API create/read boundary implemented and verified.
- DatabaseService persistence model, repository, transactional lifecycle service, and API create/read boundary implemented and verified.
- DatabaseUser persistence model, repository, transactional lifecycle service, and API create/read boundary implemented and verified.
- DatabaseService and DatabaseUser Master API resource boundaries documented in `docs/master-api.md`.
- DatabaseService and DatabaseUser API documentation reviewed against the Master
  handlers, application services, shared API contract, and existing tests.
- Remaining Master API resource documentation reviewed against the Master
  handlers, application services, and existing tests; request and response
  boundaries are aligned.
- Master API authorization and error mapping reviewed against the shared
  contracts and existing tests; correlation mismatches and malformed
  authorization decisions now map to dependency errors.
- Master persistence slice for Account roles, external identity references,
  and effective subscription resource entitlements implemented and verified.
- Master application and API boundaries for Account roles, identity references,
  and effective subscription entitlements implemented and verified; routes,
  authorization mapping, composition, and API documentation are aligned.
- Authentication Service now validates login-issued user access tokens through
  ZITADEL introspection before evaluating Master authorization scopes; standard
  Bearer token type, user identity and numeric expiry are handled.
- Minimal FastAPI adapter for the reviewed Master API boundaries implemented
  and verified, including request correlation, bearer credential propagation,
  JSON validation, response mapping, and documented resource routes.
- Standard `make test` command added for running the complete test suite.
- Master production ASGI entrypoint and container Dockerfile added; runtime
  configuration invokes the composition root through `DATABASE_URL` and
  `AUTH_SERVICE_URL`.
- Authentication Service `/v1/authorize` implemented as a separate FastAPI
  container backed by ZITADEL token introspection, with request correlation,
  scope authorization, and contract-aligned error responses.
- Authentication Service user login flow implemented with ZITADEL authorization
  redirect, callback code exchange, state propagation, and CLI access-token
  response contract.
- CLI user session flow implemented with login-state validation, Bearer token
  validation, and local session persistence.
- Authenticated CLI-to-Master HTTP client boundary implemented for JSON business
  resource reads and creates, including Bearer propagation, request IDs, and
  structured API/transport errors.
- First CLI business command implemented: `user create` loads the persisted user
  session and creates a Master user through `MasterClient`.
- CLI login command implemented: it starts the existing Authentication Service
  flow, completes the callback, and persists the resulting user session.
- Authenticated CLI MailAccount creation command implemented:
  `mail-account create` uses the persisted session and Master API.
- Authenticated CLI MailAccount read command implemented:
  `mail-account get` uses the persisted session and Master API.
- Authenticated CLI MailService creation command implemented:
  `mail-service create` uses the persisted session and Master API.
- Authenticated CLI MailService read command implemented:
  `mail-service get` uses the persisted session and Master API.
- Authenticated CLI DatabaseService creation command implemented:
  `database-service create` uses the persisted session and Master API.
- Authenticated CLI DatabaseService read command implemented:
  `database-service get` uses the persisted session and Master API.
- Authenticated CLI DatabaseUser creation command implemented:
  `database-user create` uses the persisted session and Master API.
- Authenticated CLI DatabaseUser read command implemented:
  `database-user get` uses the persisted session and Master API.
- Authenticated CLI WebService creation command implemented:
  `web-service create` uses the persisted session and Master API.
- Authenticated CLI WebService read command implemented:
  `web-service get` uses the persisted session and Master API.
- Authenticated CLI DnsService creation command implemented:
  `dns-service create` uses the persisted session and Master API.
- Authenticated CLI DnsService read command implemented:
  `dns-service get` uses the persisted session and Master API.
- First CLI read command implemented: `user get` loads the persisted session
  and reads a Master user through `MasterClient`.
- Authenticated CLI Account commands implemented: `account get` and
  `account create` use the persisted session and Master API.
- Authenticated CLI subscription entitlement commands implemented:
  `subscription entitlement list`, `get`, and `create` use the persisted
  session and Master API.
- Authenticated CLI IdentityReference read command implemented:
  `identity-reference get` uses the persisted session and Master API.
- Authenticated CLI IdentityReference create command implemented:
  `identity-reference create` uses the persisted session and Master API.
- Authenticated CLI ServicePlan creation command implemented:
  `service-plan create` uses the persisted session and Master API, including
  status, resource limits, and object limits.
- Authenticated CLI ServicePlan read command implemented:
  `service-plan get` uses the persisted session and Master API.
- Authenticated CLI Service read command implemented:
  `service get` uses the persisted session and Master API.
- Authenticated CLI Service creation command implemented:
  `service create` uses the persisted session and Master API.
- Authenticated CLI Service reconciliation-state read command implemented:
  `service state get` uses the persisted session and Master API.
- Authenticated CLI service actual-state report command implemented:
  `service state report` uses the persisted session and Master API.
- Hosting CLI command registration now reuses one helper for standalone and
  nested resource reads.
- Authenticated CLI Domain creation command implemented:
  `domain create` uses the persisted session and Master API.
- Authenticated CLI Website creation command implemented:
  `website create` uses the persisted session and Master API.
- Authenticated CLI Website read command implemented:
  `website get` uses the persisted session and Master API.
- Authenticated CLI MailDomain creation command implemented:
  `mail-domain create` uses the persisted session and Master API.
- Authenticated CLI MailDomain read command implemented:
  `mail-domain get` uses the persisted session and Master API.
- Authenticated CLI Subscription create command implemented:
  `subscription create` uses the persisted session and Master API.
- Authenticated CLI Subscription read command implemented:
  `subscription get` uses the persisted session and Master API.
- Authenticated CLI Worker Node read command implemented:
  `node get` uses the persisted session and Master API.
- Authenticated CLI Worker Node listing command implemented:
  `node list` uses the persisted session and Master API with status and
  capability filters.
- Authenticated CLI Worker Node heartbeat command implemented:
  `node heartbeat` uses the persisted session and Master API.
- Master service added to `docker-compose.prod.yml` with production build settings,
  port exposure, and required database and authentication service URLs.
- PostgreSQL and ZITADEL services added to `docker-compose.prod.yml`; Master now
  connects to the PostgreSQL and ZITADEL containers, with separate Master and
  ZITADEL databases initialized in PostgreSQL.
- Development and production compose configurations separated; production
  excludes the DSL and Plesk services.
- Production Authentication Service credentials are now required through
  `ZITADEL_CLIENT_ID` and `ZITADEL_CLIENT_SECRET`; `.env.example` and the
  production authorization setup instructions were added, and Compose
  rendering with non-empty credentials was verified.
- Production Compose stack started successfully with PostgreSQL, ZITADEL,
  Authentication Service and Master; live endpoints and the ZITADEL
  Management API were checked.
- Authenticated Worker Agent-to-Master HTTP client path implemented for
  WebService actual-state reporting, reusing the established Master client
  transport and error handling.
- Worker Node registration lifecycle implemented: bootstrap-authenticated,
  idempotent registration returns a stable node identity and node-specific
  credential; authenticated heartbeats update liveness, stale nodes become
  `OFFLINE`, and `DISABLED` nodes cannot be revived.
- Authenticated Web Agent desired-state HTTP endpoint implemented for `WEB`
  services, including assignment/version/configuration validation and
  idempotent process-local acceptance of repeated versions.
- Web Agent registration over REST/HTTP: submit its configured hostname,
  capabilities, capacity, and bootstrap credential.
- Web Agent authenticated heartbeat operation added
- Production Web Agent lifespan wired to reconciliation path.
- Web Agent reconciliation is service-scoped: each service now has its own
  managed Nginx configuration and make STOPPED/DELETED desired lifecycle
  states remove only that service's configuration.
- Defined the host-side runtime boundary for Web Agent Nginx operations in
  `docs/implementation-boundaries.md` and the Structurizr deployment model;
  the runtime is now shown as a service-scoped REST/HTTP interface outside the
  Web Agent container, with validation, publish/remove, reload, and status
  responsibilities separated from the Agent.

---

## Implementation Plan


### Steps

1. Define the Web Agent-to-host-service runtime interface in
   `docs/implementation-boundaries.md` and the Structurizr Agent/deployment
   model. Specify an explicit REST/HTTP contract for per-service configuration
   publication/removal, validation, reload and observed status, and show the
   Nginx runtime and its lifecycle manager outside the Web Agent container.
2. Implement the Worker Node host-side runtime endpoint, separate from the
   Agent container, to own Nginx configuration files and invoke the host's
   validation, reload and inspection utilities. Keep operations scoped to one
   service and return observed status/configuration or explicit errors.
3. Replace direct filesystem, `nginx` and `systemctl` operations in
   `agents/web_agent/providers.py` with a client for that runtime interface;
   wire its endpoint in the production deployment. Populate the reported
   actual configuration and health from the runtime observation rather than
   echoing desired configuration, and verify failures are surfaced.
4. Remove the user-session `service state report` CLI command from
   `src/ftp_project/cli/commands/hosting.py` and
   `src/ftp_project/cli/handlers.py`, updating its CLI tests and documentation.
   Preserve `service state get`; actual-state writes remain restricted to the
   Worker Node owning the current assignment.


### Current Step

Implement the Worker Node host-side runtime endpoint, separate from the
Agent container, to own Nginx configuration files and invoke the host's
validation, reload and inspection utilities. Keep operations scoped to one
service and return observed status/configuration or explicit errors.

### Plan Status

IN_PROGRESS

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
- If required libraries are missing from the environment, stop and ask the
  user to install them; continue only after the user confirms installation.

---

## Change Policy

After completing a task:

1. Update `Completed Steps`.
2. Remove resolved items from `Known Issues`.
3. Update `Current Step` to the next item in `Implementation Plan`.
4. Update `Last verified commit`.
5. Commit the state together with the corresponding project changes.

Do not use this file as a changelog.

Historical information belongs in Git history.

## Last Architect Review

Status: findings

Review: Master remains the owner of node identity, placement, desired state
and persisted actual state. Agent registration/heartbeat and actual-state
report authentication use the node-specific credential; Master checks that
the reporter owns the current assignment. Registration views now show
Agent-initiated REST/HTTP registration, and no Agent-to-Agent communication
or automatic failover was found. The current plan's service-scoped Nginx
configuration behavior is implemented; provider tests also cover top-level
configuration validation before reload and readiness checks. However, that
implementation executes `nginx` and `systemctl` subprocesses and writes under
`/etc/nginx` in the Agent's own container. The production Agent image is
Python-only and Compose provides no host runtime interface or mounted host
configuration. Putting the Nginx service runtime in the Agent would violate
`AGENTS.md`; executing `systemctl` from the Agent violates this document's
rule that Agents neither contain nor manage system-service lifecycle. The
explicit runtime interface required
by `docs/implementation-boundaries.md` is not yet specified or implemented,
and the Structurizr deployment relation currently says the Nginx runtime is
"Managed by" the Agent rather than showing that boundary.

Further inconsistencies: `WebAgentDesiredStateStore.report_actual_state`
reports the accepted desired configuration as actual even when provider
application failed, so Master does not receive the observed configuration.
The CLI still exposes `service state report` using a user session; Master
rejects this credential, but the command contradicts the Agent-only
actual-state write contract. Master composition and application services do
not implement the documented outbound Agent Client or send persisted desired
state to the assigned Agent, so the current code is not an end-to-end Master
reconciliation flow. Heartbeats still report zero CPU, memory and disk usage
rather than observations. Review result: the previous Nginx validation step
cannot be considered complete architecturally until host operations go
through an explicit external runtime interface; replace the plan with the
bounded runtime-boundary and report-ownership iteration. Do not install
Nginx/systemd into the Agent container or let the Agent own host service
lifecycle. The Last Test Result establishes the service-scoped unit behavior,
not production host-runtime integration or the full Master-to-Agent flow.

## Last Test Result

Status: PASS

Commands executed:
- `make test -s` → PASS: 104 tests ran, all passed (`104 passed, 1 warning in 1.93s`).
- `ruff check .` → FAIL: repository-wide lint/style issues remain in pre-existing files (notably `tests/test_master_persistence.py`), but they are unrelated to the current Web Agent step and do not indicate a regression in the requested behavior.

Classification:
- `make test`: PASS; the canonical suite passes in the current environment.
- `ruff`: Existing repository lint issue outside the current step, not a defect in the Web Agent implementation.

Summary: The current implementation satisfies the requested step. Each Web service now gets its own managed Nginx config file, `STOPPED`/`DELETED` desired states remove only that service’s configuration, and the reconciliation flow remains idempotent while allowing multiple services to reconcile independently.
