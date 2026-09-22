# Domain Model

This document is the canonical business-domain model for the hosting platform.
It is deliberately separate from the Structurizr C4 model. C4 describes
software structure; this document describes business ownership, containment,
lifecycle and the state that Master must control.

The model is Plesk-informed, not Plesk-shaped. `docs/temp_db.sql` is reference
material only and is not a target schema.

## Scope and vocabulary

The platform serves hosting customers through this management hierarchy:

```text
Administrator
└── Reseller (optional)
    └── Customer/User
        └── Subscription
            ├── ServicePlan
            ├── ResourceEntitlement
            ├── Domain
            │   ├── Website ── WebService
            │   ├── DnsZone ── DnsRecord ── DnsService
            │   └── MailDomain ── MailAccount ── MailService
            └── DatabaseService ── DatabaseUser
```

This is a business authorization and ownership hierarchy, not an
object-oriented inheritance hierarchy:

- an Administrator governs the platform;
- a Reseller is an optional delegated operator within assigned limits;
- a Customer/User owns subscriptions and the hosting objects inside them;
- a Subscription is the boundary for a plan, resources, domains and services;
- a Service is a deployable capability belonging to a subscription;
- a WorkerNode is infrastructure and never owns a business object.

An authenticated principal is not automatically a Customer. ZITADEL owns
credentials, sessions, tokens and authentication/authorization decisions. Our
`User` stores the external ZITADEL subject reference and the business profile
and ownership needed by Master.

## Core entities

| Entity | Purpose and main attributes | Ownership and lifecycle | Master state vs worker state |
| --- | --- | --- | --- |
| `Administrator` | Platform operator; `id`, external identity reference, status, audit timestamps | Root management scope; active, suspended, deactivated | Profile, role and scope in Master; credentials and roles in ZITADEL |
| `Reseller` | Delegated operator; `id`, `administrator_id`, profile, status, delegated limits | Owned by the platform; active, suspended, terminated | Delegation and limits in Master; no worker state |
| `User` / `Customer` | Hosting customer; `id`, optional `reseller_id`, external identity reference, profile, status | Owned by Administrator or Reseller; active, suspended, closed | Business profile and ownership in Master; no worker state |
| `ServicePlan` | Reusable offer containing service availability and default limits; `id`, name, status, service features, limits | Managed by Administrator; draft, active, retired | Entire definition in Master; evaluated into subscriptions, never authoritative in an Agent |
| `Subscription` | Customer hosting scope; `id`, `customer_id`, optional `reseller_id`, plan reference, status, dates | Owned by one Customer; pending, active, suspended, expired, terminated | Ownership, plan, effective entitlements and lifecycle in Master |
| `ResourceEntitlement` | Effective quota/limit; resource name, limit, usage, reservation, source | Derived from plan plus delegated/explicit overrides | Limit, reservation and reported usage in Master; local enforcement/measurement on Agents |
| `Domain` | Canonical internet name and subscription boundary; `id`, subscription, normalized name, status | Owned by one Subscription; pending, active, suspended, deleted | Name, ownership and lifecycle in Master; DNS/web/mail effects on Agents |
| `Website` | Logical web site attached to a Domain; `id`, domain, document root, status | At most one primary Website per Domain in this scope | Intent and config in Master; files, virtual host and runtime on Web Agent |
| `DnsZone` / `DnsRecord` | Authoritative DNS data; zone status and record name/type/value/TTL | One managed zone per Domain at most; records contained by the zone | Records and desired zone config in Master; nameserver runtime on DNS Agent |
| `MailDomain` / `MailAccount` | Mail capability and mailbox identities; address/status/quota | One managed MailDomain per Domain at most; accounts contained by it | Mail objects and desired config in Master; mailbox/runtime on Mail Agent |
| `Service` | Common deployable aggregate; `id`, subscription, type, status, timestamps | Owned by one Subscription; pending, provisioning, running, degraded, stopped, deleted | Desired lifecycle/config and placement in Master; provider state on an Agent |
| `WebService` | Web implementation/configuration; server, PHP/runtime and document root | One WebService for a Website in this scope | Typed desired config in Master; web server/filesystem on Web Agent |
| `DnsService` | DNS implementation for managed zones | One service may serve a subscription's DNS objects | Typed desired config in Master; DNS daemon on DNS Agent |
| `MailService` | Mail implementation for managed mail objects | One service may serve a subscription's mail objects | Typed desired config in Master; mail stack on Mail Agent |
| `DatabaseService` | Database instance; engine, database name, subscription and optional domain context | Owned by one Subscription; users are contained by it | Definition and credential references in Master; database instance on DB Agent |
| `DatabaseUser` | Login and privileges for one DatabaseService; no plaintext secret in domain records | Contained by one DatabaseService; active, suspended, revoked | Username/privilege intent in Master; account and secret material on DB Agent |

`Domain`, `Website`, `DnsZone`, `MailDomain`, `MailAccount` and
`DatabaseUser` are business resources, not worker processes. The corresponding
`*Service` is the deployable capability that realizes them.

## Value objects and relationships

These concepts have no independent business identity in the first slice and
should be value objects or owned records:

- `IdentityReference`: provider (`zitadel`) and immutable external subject ID;
  it is not a ZITADEL user record;
- `DomainName`: normalized DNS name plus display form;
- `ResourceLimit`, `ResourceUsage` and `ResourceReservation`: named unit,
  numeric value and optional period;
- `ServiceConfiguration`: type-specific desired configuration validated by the
  owning service domain;
- `Capabilities` and `Capacity`: worker capability names and allocatable
  CPU, memory, disk or service slots;
- `HealthObservation`: timestamped status, health and diagnostic details.

```text
Administrator 1 ─── N Reseller
Administrator 1 ─── N User
Reseller 0..1 ─── N User
User 1 ─── N Subscription
ServicePlan 1 ─── N Subscription
Subscription 1 ─── N Domain
Subscription 1 ─── N Service
Subscription 1 ─── N ResourceEntitlement
Domain 1 ─── 0..1 Website ─── 1 WebService
Domain 1 ─── 0..1 DnsZone ─── N DnsRecord
Domain 1 ─── 0..1 MailDomain ─── N MailAccount
Service 1 ─── 0..1 typed service configuration
DatabaseService 1 ─── N DatabaseUser
Service 1 ─── N ServiceAssignment
ServiceAssignment N ─── 1 WorkerNode
Service 1 ─── 1 DesiredState
Service 1 ─── 0..1 ActualState
```

The current model has one active assignment per Service. Replica and failover
semantics require a future explicit policy and are not implied here.

## Resource inheritance and effective limits

Limits are evaluated from broadest scope to narrowest scope:

```text
Administrator capacity
  → Reseller delegated quota
    → ServicePlan defaults
      → Subscription effective entitlement
        → Domain/service allocation and current usage
```

A narrower scope may reduce an inherited limit but must not exceed its parent
allocation. A subscription may have explicit overrides, but the effective
entitlement remains a Master calculation. Agents receive only the limits
needed to enforce assigned desired state and report usage; they do not grant
quota or resolve ownership.

## Lifecycle and provisioning

Business lifecycle and infrastructure provisioning are separate dimensions.

```text
Subscription: PENDING → ACTIVE → SUSPENDED → EXPIRED/TERMINATED
Domain:       PENDING → ACTIVE → SUSPENDED → DELETED
Service:      PENDING → PROVISIONING → RUNNING → DEGRADED/STOPPED → DELETED
Assignment:   PROPOSED → ACTIVE → REPLACED/REMOVED
WorkerNode:   REGISTERED → ONLINE → OFFLINE → DISABLED/DECOMMISSIONED
```

Worker Node registration and liveness are separate concerns. Registration
creates the stable node identity and returns node-specific credentials;
registration leaves the node `REGISTERED` until a valid heartbeat is
accepted. A valid heartbeat updates `last_heartbeat_at` and sets the node to
`ONLINE`. Master derives `OFFLINE` when the heartbeat timeout is exceeded.
`DISABLED` is an explicit administrative state and cannot be revived by a
heartbeat. Bootstrap credentials are accepted only by registration.

Suspending a customer, subscription or domain changes desired business state;
it does not mean that Master has already stopped a provider process. Master
creates a new desired-state version, and the responsible Agent reconciles it.
`ActualState` reports what was observed and cannot become a new source of
ownership or placement truth.

## Master, Agents and state ownership

| Boundary | Owns | Must not own |
| --- | --- | --- |
| ZITADEL/Auth service | Credentials, login, tokens, external identity and authorization decision | Hosting ownership, plans, domains, quotas or placement |
| Master | Business entities, effective quotas, scheduling, assignments, desired state, actual state and PostgreSQL transactions | Provider-specific process control and direct filesystem/database/mail changes |
| Web Agent | WebService reconciliation and local web runtime/files | Customers, domains as owners, global scheduling, another Agent |
| DNS Agent | DnsService reconciliation and local zones/records | Customer ownership, subscriptions, another Agent |
| Mail Agent | MailService reconciliation and local mail runtime | Customer ownership, subscriptions, another Agent |
| DB Agent | DatabaseService/DatabaseUser reconciliation and local DB runtime | Subscription ownership, global placement, another Agent |
| WorkerNode | Host capacity, capabilities and health reported to Master | Business ownership and desired-state authority |

All Master↔Agent communication is REST/HTTP. Agents never communicate with
each other. A service's physical node can change without changing its domain
owner, subscription or domain relationships.

## Plesk reference classification

The dump is useful for discovering concepts, not for copying tables.

| Plesk reference | Classification for this project |
| --- | --- |
| `clients` with `type`, `parent_id`, `vendor_id` | Signal for Administrator/Reseller/Customer hierarchy; model explicit roles and relationships, not one polymorphic table |
| `Plans`, `Templates`, `PlanItems`, `PlansSubscriptions` | Signal for ServicePlan, plan features and subscription assignment; do not copy plan-item persistence |
| `Limits`, `LimitsReservation`, `disk_usage` | Signal for entitlements, reservations and usage; keep a small typed quota model |
| `domains`, `subdomains`, `domain_aliases` | `Domain` is in scope; subdomains and aliases are future child resources |
| `hosting`, `DomainServices`, `PhpSettings*`, `WebServerSettings*` | WebService configuration reference; provider settings stay in typed WebService config |
| `dns_zone`, `dns_recs`, `dns_recs_t` | DnsZone and DnsRecord are in scope; temporary records are provisioning details |
| `mail`, `mail_aliases`, `mail_redir`, `MailLists` | MailAccount is in scope; aliases, redirects and lists are deferred child resources |
| `data_bases`, `db_users`, `DatabaseServers` | DatabaseService and DatabaseUser are in scope; database server is DB Agent infrastructure |
| `IP_Addresses`, `IpCollections`, `ip_pool` | Future IPAddress/IPAllocation infrastructure concepts; not required for this first slice |
| `ServiceNodes`, `ServiceNode*` | Reference for placement; our WorkerNode and ServiceAssignment have clearer ownership and desired-state semantics |
| `certificates`, `CertificateRepositories`, `secret_keys`, password columns | Technical secrets/certificate material; never core plaintext business data |
| `sessions`, `SessionContexts`, `cp_access`, `smb_*`, `Permissions` | Plesk auth/UI implementation; replaced by ZITADEL plus Master authorization |
| traffic/statistics, `*Stats`, `report*`, `PleskStats` | Observability/reporting data, not source-of-truth domain entities |
| `Parameters`, `*_param`, `Configurations`, `ModuleSettings`, caches | Plesk persistence/configuration mechanics, not domain entities |
| backups, scheduled tasks, notifications, upgrade/history/log tables | Operational features outside the minimal hosting model; defer until required |

The dump gives no reason to introduce Plesk table names, integer IDs, provider
flags or password fields into the Master domain model.

## Implementation status and roadmap

`STATE.md` confirms that the current implementation already has Master-side
models and API/application boundaries for User, ServicePlan, Subscription,
Domain, Website, Mail, Database, WorkerNode, ServiceAssignment, DesiredState
and ActualState. It also confirms the Auth/ZITADEL boundary, separate Agents,
placement in Master and reconciliation semantics. This document is therefore
an architectural contract for the next slices, not a request to rewrite C4 or
add every Plesk feature.

Recommended implementation order:

1. Keep existing Master entities and migration boundaries aligned with the
   ownership/cardinality rules above; document `IdentityReference` explicitly.
2. Add explicit Reseller/Administrator records and authorization scope only
   when the first delegated-management API is implemented.
3. Introduce typed effective-quota calculation and reservation; keep worker
   enforcement/reporting downstream of Master decisions.
4. Implement one end-to-end Web Agent reconciliation path with desired-version
   idempotency and actual-state reporting.
5. Apply the same Agent contract to DNS, Mail and DB without Agent-to-Agent
   calls.
6. Add IP allocation, certificates, aliases/subdomains, backups and reporting
   only as separate domain slices when required.
7. Add the first CLI read command identified by `STATE.md`'s current next
   step, using the existing authenticated `MasterClient` without expanding
   authentication or token validation.

## Explicit non-goals

- No Plesk database migration or compatibility layer.
- No change to the Structurizr C4 model in this document.
- No automatic failover, replica semantics or cross-Agent orchestration.
- No separate ZITADEL User aggregate in the hosting domain.
- No first-slice implementation of every Plesk feature, billing, certificates,
  backups, aliases, subdomains or statistics.
