# Master REST API Resource Schemas and Handler Boundaries

This document defines the first Master REST API contract. It covers client-to-
Master business resources and Master-to-Agent state reports. It does not define
FastAPI implementation details, database models, scheduling policy, or provider
configuration schemas.

## Common HTTP rules

- All endpoints use the `/v1` prefix and JSON bodies.
- Request and response fields use `snake_case`.
- Resource identifiers are opaque strings.
- Timestamps are RFC 3339 UTC strings.
- Clients send `Authorization: Bearer <credential>` and may send
  `X-Request-ID`; Master returns the request ID in errors.
- Successful mutation responses return the created or updated resource. No
  mutation is considered successful until its Master transaction commits.
- Errors use the shared `ApiError` schema from `docs/api-contracts.md`.
- Unknown response fields are forward-compatible additions.

## Resource schemas

The following schemas describe the stable API representation. Fields marked
`object` are JSON objects whose provider-specific contents are validated by the
owning service boundary, not by the transport handler.

### User

```json
{
  "id": "user-123",
  "status": "ACTIVE",
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z"
}
```

Required fields: `id`, `status`, `created_at`, `updated_at`.

### ServicePlan

```json
{
  "id": "plan-123",
  "name": "small",
  "status": "ACTIVE",
  "resource_limits": {"cpu": 2, "memory": 2048, "disk": 20000},
  "object_limits": {},
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z"
}
```

Required fields: `id`, `name`, `status`, `resource_limits`, `object_limits`,
`created_at`, `updated_at`.

### Subscription

```json
{
  "id": "subscription-123",
  "user_id": "user-123",
  "plan_id": "plan-123",
  "status": "ACTIVE",
  "created_at": "2026-01-01T00:00:00Z",
  "expires_at": null
}
```

Required fields: `id`, `user_id`, `plan_id`, `status`, `created_at`.
`expires_at` is optional.

### IdentityReference

```json
{"id": "identity-123", "provider": "zitadel", "subject_id": "user-123"}
```

Identity references are immutable Master records for external subjects. The
`provider` and `subject_id` pair is unique.

### Account

```json
{
  "id": "account-123", "role": "CUSTOMER", "status": "ACTIVE",
  "identity_reference_id": "identity-123", "parent_account_id": null,
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z"
}
```

An Account owns a Master role and optional hierarchy links. Identity and parent
references must exist before the account is created.

### ResourceEntitlement

```json
{
  "id": "entitlement-123", "subscription_id": "subscription-123",
  "resource_name": "disk", "limit": 100, "usage": 0,
  "reservation": 0, "source": "PLAN"
}
```

Resource entitlements are effective subscription limits calculated and stored
by Master. `subscription_id` and `resource_name` are unique together.

### Domain

```json
{
  "id": "domain-123",
  "subscription_id": "subscription-123",
  "name": "example.test",
  "status": "PENDING",
  "created_at": "2026-01-01T00:00:00Z"
}
```

Required fields: `id`, `subscription_id`, `name`, `status`, `created_at`.

### Website

```json
{
  "id": "website-123",
  "domain_id": "domain-123",
  "status": "PENDING",
  "document_root": "/srv/www/example",
  "created_at": "2026-01-01T00:00:00Z"
}
```

Required fields: `id`, `domain_id`, `status`, `document_root`, `created_at`.

### MailDomain

```json
{
  "id": "mail-domain-123",
  "domain_id": "domain-123",
  "status": "PENDING",
  "created_at": "2026-01-01T00:00:00Z"
}
```

Required fields: `id`, `domain_id`, `status`, `created_at`. A MailDomain can
only be created for a domain belonging to the supplied subscription.

### MailAccount

```json
{
  "id": "mail-account-123",
  "mail_domain_id": "mail-domain-123",
  "address": "postmaster@example.com",
  "status": "PENDING",
  "created_at": "2026-01-01T00:00:00Z"
}
```

Required fields: `id`, `mail_domain_id`, `address`, `status`, `created_at`. A
MailAccount can only be created for an existing MailDomain.

### WebService

The WebService response contains the common service aggregate and its
service-specific configuration:

```json
{
  "id": "service-123",
  "subscription_id": "subscription-123",
  "type": "WEB",
  "website_id": "website-123",
  "web_server": "nginx",
  "php_version": "8.3",
  "document_root": "/srv/www/example"
}
```

The common `assignment` and `desired_state` fields from the service aggregate
are also returned.

### DnsService and MailService

Both resources return the common service aggregate, including `assignment` and
`desired_state`. Their provider-specific configuration is stored in
`desired_state.configuration` and is returned unchanged by the corresponding
read endpoint.

`DnsService` creation requires `subscription_id`, `domain_id`, `allocation`,
`lifecycle_state`, and `configuration`.

`MailService` creation requires `subscription_id`, `domain_id`, `allocation`,
`lifecycle_state`, and `configuration`.

### Service

```json
{
  "id": "service-123",
  "subscription_id": "subscription-123",
  "type": "WEB",
  "status": "RUNNING",
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z"
}
```

Required fields: `id`, `subscription_id`, `type`, `status`, `created_at`,
`updated_at`. `type` is one of `WEB`, `DNS`, `MAIL`, or `DATABASE`.

### DatabaseService

The DatabaseService response contains the common service aggregate and its
database-specific configuration:

```json
{
  "id": "service-123",
  "subscription_id": "subscription-123",
  "type": "DATABASE",
  "status": "PROVISIONING",
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z",
  "assignment": {
    "id": "assignment-123",
    "worker_node_id": "node-123",
    "status": "ASSIGNED"
  },
  "desired_state": {
    "version": 1,
    "lifecycle_state": "PROVISIONING",
    "configuration": {
      "database_type": "postgresql",
      "database_name": "app_db"
    },
    "updated_at": "2026-01-01T00:00:00Z"
  },
  "database_type": "postgresql",
  "database_name": "app_db"
}
```

The common service, assignment, and desired-state fields are required as
described by `Service`, `ServiceAssignment`, and `DesiredState`. The
DatabaseService-specific fields `database_type` and `database_name` are also
required.

### DatabaseUser

```json
{
  "id": "database-user-123",
  "database_service_id": "service-123",
  "username": "app_user",
  "status": "PENDING",
  "privileges": {"read": true, "write": true}
}
```

All fields are returned. `privileges` is an object owned by the database
service boundary and defaults to `{}`.

### WorkerNode

```json
{
  "id": "node-123",
  "hostname": "worker-1.example.test",
  "status": "ONLINE",
  "capabilities": {"web": true},
  "capacity": {"cpu": 8, "memory": 8192, "disk": 100000},
  "usage": {"cpu": 2, "memory": 3500, "disk": 5000},
  "last_heartbeat_at": "2026-01-01T00:10:00Z",
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:10:00Z"
}
```

Required fields: `id`, `hostname`, `status`, `capabilities`, `capacity`,
`usage`, `created_at`, `updated_at`. `last_heartbeat_at` is optional.

### ServiceAssignment

```json
{
  "id": "assignment-123",
  "service_id": "service-123",
  "worker_node_id": "node-123",
  "status": "ASSIGNED",
  "assigned_at": "2026-01-01T00:00:00Z",
  "released_at": null
}
```

Required fields: `id`, `service_id`, `worker_node_id`, `status`, `assigned_at`.
`released_at` is present for released assignments.

### DesiredState

```json
{
  "service_id": "service-123",
  "version": 2,
  "lifecycle_state": "RUNNING",
  "configuration": {"web_server": "nginx"},
  "updated_at": "2026-01-01T00:00:00Z"
}
```

All fields are required. `version` is monotonically increasing per service.

### ActualState

```json
{
  "service_id": "service-123",
  "assignment_id": "assignment-123",
  "version": 2,
  "status": "RUNNING",
  "configuration": {"web_server": "nginx"},
  "health": {"ready": true},
  "observed_at": "2026-01-01T00:10:00Z"
}
```

All fields are required. `assignment_id` identifies the assignment against
which Master validates the report; `version` is the desired-state version
represented by the observation.

## Endpoint boundaries

### Client-facing business endpoints

Creation request fields are validated by the handler as follows:

- `User`: optional `status`, default `ACTIVE`.
- `ServicePlan`: required `name`; optional `status` (default `ACTIVE`),
  `resource_limits` (default `{}`), and `object_limits` (default `{}`).
- `Subscription`: required `user_id` and `plan_id`; optional `status` (default
  `ACTIVE`) and nullable `expires_at`.
- `Domain`: required `subscription_id` and `name`; optional `status` (default
  `PENDING`).
- `Website`: required `domain_id` and `document_root`; optional `status`
  (default `PENDING`).
- `MailDomain`: required `subscription_id` and `domain_id`; optional `status`
  (default `PENDING`).
- `MailAccount`: required `mail_domain_id` and `address`; optional `status`
  (default `PENDING`).
- `Service`: required `subscription_id`, `type`, `allocation`,
  `lifecycle_state`, and `configuration`.
- `WebService`: required `subscription_id`, `website_id`, `allocation`,
  `lifecycle_state`, `web_server`, `php_version`, and `document_root`.
- `DnsService` and `MailService`: required `subscription_id`, `domain_id`,
  `allocation`, `lifecycle_state`, and `configuration`.
- `DatabaseService`: required `subscription_id`, `allocation`,
  `lifecycle_state`, `database_type`, and `database_name`.
- `DatabaseUser`: required `database_service_id` and `username`; optional
  `status` (default `PENDING`) and `privileges` (default `{}`).

All required string fields must be non-empty strings, and all `object` fields
must be JSON objects. Successful resource creation returns `201`.

| Method | Path | Request | Response | Owning application operation |
| --- | --- | --- | --- | --- |
| `GET` | `/v1/users/{user_id}` | none | `User` | load user |
| `POST` | `/v1/users` | user creation request | `User` | create user |
| `GET` | `/v1/service-plans/{plan_id}` | none | `ServicePlan` | load plan |
| `POST` | `/v1/service-plans` | plan creation request | `ServicePlan` | create plan |
| `GET` | `/v1/subscriptions/{subscription_id}` | none | `Subscription` | load subscription |
| `POST` | `/v1/subscriptions` | subscription creation request | `Subscription` | create subscription |
| `GET` | `/v1/identity-references/{identity_reference_id}` | none | `IdentityReference` | load identity reference |
| `POST` | `/v1/identity-references` | identity reference creation request | `IdentityReference` | create identity reference |
| `GET` | `/v1/accounts/{account_id}` | none | `Account` | load account |
| `POST` | `/v1/accounts` | account creation request | `Account` | create account |
| `GET` | `/v1/subscriptions/{subscription_id}/entitlements` | none | list of `ResourceEntitlement` | list effective entitlements |
| `GET` | `/v1/subscriptions/{subscription_id}/entitlements/{resource_name}` | none | `ResourceEntitlement` | load one entitlement |
| `POST` | `/v1/subscriptions/{subscription_id}/entitlements` | entitlement creation request | `ResourceEntitlement` | create effective entitlement |
| `GET` | `/v1/domains/{domain_id}` | none | `Domain` | load domain |
| `POST` | `/v1/domains` | domain creation request | `Domain` | create domain |
| `GET` | `/v1/websites/{website_id}` | none | `Website` | load website |
| `POST` | `/v1/websites` | website creation request | `Website` | create website |
| `GET` | `/v1/mail-domains/{mail_domain_id}` | none | `MailDomain` | load mail domain |
| `POST` | `/v1/mail-domains` | mail domain creation request | `MailDomain` | create mail domain |
| `GET` | `/v1/mail-accounts/{mail_account_id}` | none | `MailAccount` | load mail account |
| `POST` | `/v1/mail-accounts` | mail account creation request | `MailAccount` | create mail account |
| `GET` | `/v1/services/{service_id}` | none | service aggregate view | load service |
| `POST` | `/v1/services` | service creation request | service aggregate view | create and place service |
| `GET` | `/v1/web-services/{service_id}` | none | `WebService` | load web service |
| `POST` | `/v1/web-services` | WebService creation request | `WebService` | create, configure, and place web service |
| `GET` | `/v1/database-services/{service_id}` | none | `DatabaseService` | load database service |
| `POST` | `/v1/database-services` | DatabaseService creation request | `DatabaseService` | create, configure, and place database service |
| `GET` | `/v1/database-users/{database_user_id}` | none | `DatabaseUser` | load database user |
| `POST` | `/v1/database-users` | DatabaseUser creation request | `DatabaseUser` | create database user |
| `GET` | `/v1/nodes` | status/capability filters | `{"items": WorkerNode[]}` | list nodes |
| `GET` | `/v1/nodes/{node_id}` | none | `WorkerNode` | load node |
| `GET` | `/v1/services/{service_id}/state` | none | desired/actual state view | load reconciliation state |

The initial service creation request contains `subscription_id`, `type`,
`allocation`, `lifecycle_state`, and `configuration`. Master validates the
subscription and service type, applies authorization, persists the service,
selects a node through scheduling, and commits the service, assignment, and
first desired-state version atomically. The response includes the resulting
service, assignment, and desired state; actual state may be absent until an
Agent reports it.

DatabaseService creation contains `subscription_id`, `allocation`,
`lifecycle_state`, `database_type`, and `database_name`. Master validates the
subscription, places the common `DATABASE` service, and commits its assignment,
desired state, and typed database configuration atomically. DatabaseUser
creation contains `database_service_id`, `username`, and optional `status` and
`privileges`; Master requires the referenced DatabaseService to exist before
committing the user. Both resources support read-after-create through their
corresponding `GET` endpoints and return `201` for successful creation.

### Node and Agent report endpoints

| Method | Path | Request | Response | Transaction |
| --- | --- | --- | --- | --- |
| `POST` | `/v1/nodes/{node_id}/heartbeat` | status, usage, heartbeat timestamp | `WorkerNode` | heartbeat update |
| `POST` | `/v1/services/{service_id}/actual-state` | `assignment_id`, `version`, `status`, `configuration`, `health`, `observed_at` | `{"accepted": boolean}` | assignment validation and stale-version check |

These endpoints are called by authenticated Worker Agents. A heartbeat updates
only the identified node. An actual-state report is accepted only for the
current `ServiceAssignment`; an older version or older observation is ignored
idempotently and does not overwrite newer state. The `service_id` for the
report is supplied by the URL, not repeated in the request body.

`GET /v1/services/{service_id}/state` returns an object with nullable
`desired`, `assignment`, and `actual` members. `desired` and `actual` contain
the fields defined above; `assignment` contains the `ServiceAssignment`
fields. The `actual.assignment_id` in this response is the current assignment
identifier used to validate the observation.

## Handler boundary

Every handler follows this sequence:

1. Parse the HTTP request into an API schema and validate required fields.
2. Establish or propagate `X-Request-ID`.
3. Call the Master Authentication Client with the resource and action. The
   credential is never passed to an application service or repository.
4. Pass typed command data and the authenticated principal to one Master
   application service.
5. Let the application service own business rules and the transaction. It may
   call repositories, scheduler, or Agent Client through their interfaces; the
   handler never issues SQL or performs placement.
6. Map the returned result to an API schema and return the documented status.
7. Map domain conflicts, missing resources, validation failures, and dependency
   failures to `ApiError` without exposing database or provider details.

The handler layer owns HTTP concerns only: routing, serialization, request
identification, authentication-client invocation, status-code mapping, and
response headers. It does not own lifecycle transitions, capacity checks,
assignment replacement, desired-state version allocation, stale-report logic,
or retries.

## Status and error mapping

| Condition | HTTP status | Error code |
| --- | --- | --- |
| Malformed JSON or invalid field | `400` | `INVALID_REQUEST` |
| Missing or invalid credential | `401` | `AUTHENTICATION_FAILED` |
| Authenticated principal lacks scope | `403` | `AUTHORIZATION_DENIED` |
| Resource does not exist | `404` | `NOT_FOUND` |
| State or capacity rule prevents operation | `409` | `CONFLICT` |
| Dependency or Agent transport failure | `503` | `DEPENDENCY_UNAVAILABLE` |

The handler must preserve the shared `request_id` and return no credentials,
raw SQL errors, provider secrets, or internal stack traces.

## Explicit non-goals

- No FastAPI router, Pydantic model module, or database migration is created by
  this contract step.
- No automatic failover or rescheduling policy is defined.
- No provider-specific configuration schema is standardized here.
- No Agent-to-Agent endpoint is allowed.
