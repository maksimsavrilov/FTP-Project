# Implementation Boundaries

This document translates the validated architecture and domain model into implementation ownership. It does not change the architecture.

## Service ownership

| Boundary | Owns | Does not own |
| --- | --- | --- |
| Master | REST API, users, plans, subscriptions, services, nodes, scheduling, `ServiceAssignment`, desired state, reconciliation orchestration, and PostgreSQL persistence | Provider-specific configuration, local service processes, worker-to-worker communication, automatic failover |
| Authentication Service | Authentication and authorization decisions, credentials, tokens, and service/client identity | Hosting domain entities, service placement, desired or actual state |
| Web/DNS/Mail/DB Agent | One service family on one Worker Node; request authentication, desired-state validation, local reconciliation, provider adapters, actual state and health reporting | Global scheduling, `ServiceAssignment` persistence, user/subscription ownership, direct communication with another Agent |
| PostgreSQL | Durable Master state, including domain entities, Worker Nodes, assignments, desired state, and observed actual state | Provider runtime state as an independent source of truth |

Each Agent has its own deployable REST service and local provider adapter. Agents do not share a database with each other and do not call each other.

## Agent ↔ Runtime boundary

- Agents must never contain or manage the lifecycle of the system services they orchestrate.
- Agents communicate with managed services through an explicit runtime interface.

### Web Agent ↔ host Nginx runtime

The Web Agent does not invoke `nginx`, `systemctl`, or direct filesystem writes for host-managed runtime state. It calls a host-side runtime service over REST/HTTP and treats that service as the authority for config publication, validation, reload, and status observation.

The runtime is scoped to a single managed service and exposes service-level operations instead of a single global config object. The Web Agent only owns request validation and reconciliation flow; the host runtime owns configuration files, `nginx` validation, daemon reloads, and observed runtime state.

#### Explicit REST/HTTP contract

- `PUT /v1/services/{service_id}/config`
  - Publishes or replaces the active config for one service version.
  - Request body: `{ "desired_version": "...", "lifecycle": "STARTED|STOPPED|DELETED", "configuration": { ... } }`
  - Response: `200 OK` or `201 Created` with `{ "service_id": "...", "desired_version": "...", "status": "APPLIED|REJECTED", "observed_configuration": { ... } }`
- `DELETE /v1/services/{service_id}/config`
  - Removes the generated config for a service when it is stopped or deleted.
  - Response: `200 OK` with `{ "service_id": "...", "status": "REMOVED" }` or an explicit error payload.
- `POST /v1/services/{service_id}/validate`
  - Validates the supplied config without persisting it.
  - Response: `200 OK` with `{ "valid": true, "errors": [] }` or `422`/`400` with details if validation fails.
- `POST /v1/services/{service_id}/reload`
  - Triggers a config reload and daemon reload only after validation passes.
  - Response: `200 OK` with `{ "service_id": "...", "reload_status": "OK|FAILED", "details": "..." }`
- `GET /v1/services/{service_id}/status`
  - Returns observed service status, current runtime configuration, validation timestamp, reload outcome, and health.
  - Response: `{ "service_id": "...", "status": "RUNNING|STOPPED|ERROR", "observed_configuration": { ... }, "last_reload": "...", "health": "...", "errors": [] }`

All operations are per service, idempotent for the same desired version, and return explicit errors for invalid config, missing service state, or runtime failures. The Web Agent records the runtime-observed configuration and health as the actual state it reports back to Master rather than echoing the desired config without validation.

## Master persistence boundary

The Master owns the SQLAlchemy models, repositories, transactions, and lifecycle transitions for:

- `User`, `ServicePlan`, `Subscription`, `Domain`, and service-specific domain entities.
- `WorkerNode`, including stable identity, registration credentials, capabilities,
  capacity, health, status, and heartbeat timestamps.
- `ServiceAssignment`, linking a `Service` to its selected `WorkerNode`.
- `DesiredState`, with a monotonically increasing version per service.
- `ActualState`, with the latest version, status, configuration, health, and observation time.

A placement transaction creates or updates `ServiceAssignment` and the corresponding `DesiredState` together. The assignment identifies the target Agent endpoint through its Worker Node; it is not stored inside a service as a direct node owner.

Repositories are the only persistence access used by Master application components. API handlers and Agents do not access PostgreSQL directly.

## HTTP boundaries

### Client to Master

The CLI and future UI call the Master REST API for business operations. The Master validates the request, applies domain rules, persists the desired result, and returns the resource or operation status.

Worker Agents register through `POST /v1/nodes/register` with the bootstrap
credential. Master returns the stable node ID and node-specific credential;
repeated registration for the same hostname returns the same identity and
credential. Bootstrap credentials are not used for heartbeat or other node
communication.

### Master to Authentication Service

The Master delegates authentication and authorization checks to the independent Authentication Service. The Auth Service returns an identity and authorization decision; it does not mutate hosting state.

### Master to Agent

The Master Agent Client sends an authenticated desired-state operation to the Agent selected by `ServiceAssignment`. The request contains:

- service identity and service type;
- assignment identity and target version;
- provider-neutral desired web configuration;
- desired lifecycle state.

The Agent accepts only the service types it owns and treats the desired-state version as an idempotency key. Its provider adapter translates the desired web configuration into local provider configuration and applies it. The response acknowledges acceptance or rejection and includes the latest known actual state when available.

### Agent to Master

An Agent reports actual state, reconciliation result, health, and heartbeat to
Master over REST/HTTP using its node-specific credential. Master validates the
credential and node identity before accepting a heartbeat. A heartbeat sets
the node `ONLINE`; timeout reconciliation sets it `OFFLINE`, while a
`DISABLED` node remains disabled. Master validates actual-state reports against
the current assignment and persists them as `ActualState`.

## Reconciliation flow

1. A Master business operation creates or changes a service.
2. Master persists the service and its desired lifecycle/configuration.
3. Scheduler selects a Worker Node using capabilities and available resources.
4. Master persists or updates `ServiceAssignment` and increments the `DesiredState` version in one transaction.
5. Reconciliation Manager reads the assignment and desired state, then sends them through Agent Client to the owning Agent.
6. The Agent validates the request, compares desired state with local actual state, and applies only the required provider changes.
7. The Agent reports the result and observed actual state to Master.
8. Master persists `ActualState` and derives the service status from the reconciliation result; it does not silently create a new assignment or fail over.
9. Reconciliation retries delivery of the same version after transient transport failure. A later desired version supersedes an older one.

The Agent may reconcile again after a restart or periodic trigger. The result must converge on the accepted desired version and remain idempotent.

## Minimal implementation slices

1. Shared API schemas and authentication client contracts.
2. Master persistence models and repositories for the domain model, nodes, assignments, desired state, and actual state.
3. Master service APIs, scheduler, Agent Client, and reconciliation orchestration.
4. One vertical Agent implementation, starting with Web Agent and one provider adapter.
5. The remaining DNS, Mail, and DB Agents using the same boundary and versioning rules.

## Explicit non-goals

- No automatic failover or rescheduling policy is defined here.
- No cross-Agent orchestration or shared Agent database is allowed.
- No provider implementation, CLI command expansion, deployment automation, or UI is defined here.
- No change to the canonical C4 model or business-domain model is required by this step.
