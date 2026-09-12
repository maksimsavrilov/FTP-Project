# Domain Model

This document is the canonical business-domain model for the hosting
platform. It is deliberately separate from the Structurizr/C4 model and from
the PostgreSQL persistence schema. The Plesk dump in `docs/temp_db.sql` is
reference material only; its table names and identifiers are not our domain
model.

## Boundary and terminology

The platform has three distinct kinds of state:

| Boundary | Owns | Does not own |
| --- | --- | --- |
| ZITADEL / Authentication Service | Credentials, tokens, external user identity and authorization decisions | Customers, subscriptions, domains or hosting state |
| Master / business domain | Ownership, commercial scope, plans, quotas, services, placement, desired state and the accepted actual-state observation | Provider processes and local filesystem/service configuration |
| Worker Agent / infrastructure | One service family on one Worker Node, provider adapters and runtime health | Global ownership, scheduling, subscriptions or another Agent |

`IdentityRef` is a value object containing the ZITADEL user ID and, optionally,
the issuer. It is a reference on an application actor, not a copy of a
ZITADEL User. A person may have several business roles, but authentication
and role authorization remain outside this model.

## Business hierarchy

```text
Administrator
└── Reseller*
    └── Customer*
        └── Subscription*
            ├── ServicePlan
            ├── Domain*
            │   ├── Website ── WebService
            │   ├── DnsZone ── DnsService ── DnsRecord*
            │   └── MailDomain ── MailService
            │                         └── MailAccount*
            └── DatabaseService*
                └── DatabaseUser*
```

The `*` means zero or more. Administrator, Reseller and Customer are
specializations of the business actor `Account`; they are not ZITADEL roles.
The initial implementation may expose only Customer/User APIs, but the
ownership rules below are already defined so later APIs do not have to change
the meaning of existing subscriptions.

## Entities and value objects

### Actors and ownership

| Entity | Purpose and main attributes | Relationships and ownership | Lifecycle |
| --- | --- | --- | --- |
| `Account` | Business party; `id`, `identity_ref`, display/contact data, status, timestamps | Owned by Master. `parent_account_id` is optional: Administrator has none, Reseller belongs to an Administrator, Customer belongs to a Reseller or Administrator | `PENDING → ACTIVE → SUSPENDED → DELETED` |
| `Administrator` | Platform operator; unrestricted business scope | Owns resellers and directly managed customers/plans | Same as Account |
| `Reseller` | Delegated provider with an isolated customer scope and quota budget | Owned by an Administrator; owns customers, subscriptions and optionally reseller plans | Same as Account |
| `Customer` | Hosting customer/site user | Owned by one Reseller or Administrator; owns subscriptions | Same as Account |

`Account` is the persistence/generalization concept. The role-specific names
describe invariants and authorization scope; they do not require three
duplicated tables. A customer can have multiple `IdentityRef` values only if
the application explicitly supports delegated users; one primary reference is
enough for the first slice.

### Commercial scope

| Entity | Purpose and main attributes | Relationships and owner | Lifecycle |
| --- | --- | --- | --- |
| `ServicePlan` | Reusable offer: `name`, enabled status, included service capabilities and `ResourceLimitSet` | Created by an Administrator or Reseller. A reseller plan cannot exceed the effective limits inherited from its owner | `DRAFT → ACTIVE → RETIRED` |
| `ResourceLimitSet` | Value object mapping a resource key to a hard limit, optional soft limit and `oversell` policy; examples: disk bytes, traffic bytes, domains, mailboxes, databases | Defined on a plan; not a separately placeable service | Replaced by a new plan revision |
| `Subscription` | Customer's allocation of a plan; `customer_id`, `plan_id`, effective limits snapshot, status, start/end dates | Owned by one Customer and assigned one active plan. It contains domains and services | `PENDING → ACTIVE → SUSPENDED → EXPIRED → TERMINATED` |
| `ResourceUsage` | Master-side measured/reserved usage for quota decisions | Aggregated per Subscription and optionally per Reseller; runtime counters remain Agent observations | Updated while the scope is active |

The effective limit is calculated as:

```text
effective(subscription) =
  min(subscription plan limit,
      customer/reseller parent budget remaining)
```

An explicit subscription override may reduce a limit, never increase the
parent budget. A plan change creates a new effective-limit snapshot; it does
not rewrite historical usage. Reservation and quota validation happen in
Master before a service is provisioned.

### Hosting resources

| Entity | Purpose and main attributes | Relationships and owner | Lifecycle |
| --- | --- | --- | --- |
| `Domain` | Canonical DNS name; normalized name, status, registration/expiry metadata | Owned by one Subscription; is the logical root for web, DNS and mail resources | `PENDING → ACTIVE → SUSPENDED → DELETED` |
| `Website` | Logical web application/site; document-root intent and site settings | Belongs to one Domain; owned transitively by its Subscription | Same as Domain |
| `DnsZone` | Desired authoritative zone for a Domain | At most one primary zone per Domain; owned transitively by Subscription | `PENDING → ACTIVE → SUSPENDED → DELETED` |
| `DnsRecord` | DNS value object/entity: owner zone, name, type, value, TTL | Many records per zone; Master validates uniqueness/type rules | Created/updated/deleted within zone |
| `MailDomain` | Mail enablement and policy for a Domain | At most one per Domain; owns mail accounts | Same as Domain |
| `MailAccount` | Mailbox identity, quota and status | Many per MailDomain; owned transitively by Subscription | `PENDING → ACTIVE → SUSPENDED → DELETED` |
| `DatabaseService` | Logical database instance: engine, name and configuration intent | Belongs to a Subscription; owns database users | Common Service lifecycle |
| `DatabaseUser` | Database login and privileges (secret is not stored in domain records) | Many per DatabaseService; credentials are provisioned through the DB Agent | `PENDING → ACTIVE → REVOKED` |

`Website`, `DnsZone`, `MailDomain` and `DatabaseService` are business
resources. `WebService`, `DnsService` and `MailService` are deployable
service representations, not alternative owners of those resources.

### Common service and infrastructure entities

| Entity | Purpose and main attributes | Master ownership and runtime split | Lifecycle |
| --- | --- | --- | --- |
| `Service` | Common deployable unit: `id`, family, subscription, status and timestamps | Master owns identity/configuration intent; one concrete service subtype stores typed configuration | `PENDING → PROVISIONING → RUNNING → DEGRADED → STOPPED → DELETED` |
| `WebService` | Web provider configuration: web server, PHP/runtime version, document root, TLS intent | Master stores desired typed configuration; Web Agent owns processes/files | Common Service lifecycle |
| `DnsService` | DNS provider configuration and zone publication intent | Master stores desired configuration; DNS Agent owns nameserver/provider runtime | Common Service lifecycle |
| `MailService` | Mail provider configuration and policy intent | Master stores desired configuration; Mail Agent owns MTA/mailbox runtime | Common Service lifecycle |
| `ServiceAssignment` | Explicit placement history: service, worker node, status and effective dates | Master only; it never changes domain ownership | `ASSIGNED → DRAINING → RELEASED` |
| `WorkerNode` | Execution target: hostname, capabilities, schedulable capacity, health and heartbeat | Master inventory/health record; node runtime is outside Master | `PROVISIONING → ONLINE → DEGRADED → OFFLINE → DECOMMISSIONED` |
| `DesiredState` | Versioned provider-neutral intent and lifecycle state | Master source of truth, one current state per Service | Replaced with monotonically increasing versions |
| `ActualState` | Latest accepted Agent observation: version, status, provider configuration and health | Master projection of runtime; Agent remains source of local observation | Updated by reconciliation reports |

One `Service` has at most one active `ServiceAssignment`, exactly one current
`DesiredState`, and at most one current `ActualState`. A Service does not own a
WorkerNode. Replacing placement preserves released assignment history.

### Value objects

`DomainName`, `EmailAddress`, `IdentityRef`, `IPAddress`, `ResourceLimit`,
`ResourceUsage`, `ServiceConfiguration`, `CapabilitySet` and
`LifecycleStatus` have no independent identity outside their owning entity.
Secrets, access tokens and provider credentials are authentication/secret
material, not domain attributes.

## Cardinality and business relationships

```text
Administrator 1 ─── N Reseller
Administrator 1 ─── N Customer
Reseller 1 ─── N Customer
Customer 1 ─── N Subscription
ServicePlan 1 ─── N Subscription
Subscription 1 ─── N Domain
Domain 1 ─── 0..1 Website ─── 1 WebService
Domain 1 ─── 0..1 DnsZone ─── N DnsRecord
Domain 1 ─── 0..1 MailDomain ─── N MailAccount
Subscription 1 ─── N Service
Subscription 1 ─── N DatabaseService ─── N DatabaseUser
Service 1 ─── N ServiceAssignment ─── 1 WorkerNode
Service 1 ─── 1 DesiredState
Service 1 ─── 0..1 ActualState
```

Creating or deleting a Domain does not implicitly create or delete every
service family. The Subscription owns the resources; services can be enabled
independently while the Subscription is active. Suspending an Account or
Subscription produces desired suspended states for its owned services; it
does not delete runtime data.

## Domain-to-component mapping

| Domain responsibility | Master | Worker Agent | Runtime state |
| --- | --- | --- | --- |
| Account, plan, subscription, quota and ownership | Owns persistence and invariants | None | None |
| Domain and logical resource configuration | Owns desired business state | Applies family-specific changes | Agent-local provider state |
| Service lifecycle and desired state | Owns version and transition | Reconciles idempotently | Desired vs actual version |
| Placement and capacity | Selects node and owns `ServiceAssignment` | Accepts only assigned services | Node-local deployment |
| Web / DNS / Mail / DB | Stores typed desired configuration and sends it to the selected Agent | Exactly one family per Agent boundary; reports actual state | Processes, files, zones, mailboxes, database engine/users |
| Authentication and authorization | Calls Auth Service and stores only `IdentityRef` | No identity authority | ZITADEL tokens/credentials |

Agents never call each other and never access PostgreSQL. The physical
location of Web, DNS, Mail and DB services may differ without changing any
relationship above.

## Plesk dump classification

The following classification uses `docs/temp_db.sql` only to validate concepts,
not as a migration plan.

| Plesk reference | Classification for this project | Reason |
| --- | --- | --- |
| `clients` (`type`, `parent_id`, `vendor_id`) | **Part of domain, simplified** | Evidence for Administrator/Reseller/Customer hierarchy; replace Plesk numeric parent links with `Account` ownership |
| `accounts`, `admin_aliases` | **Technical / Auth** | Password/account aliases belong to ZITADEL or authentication infrastructure, not business ownership |
| `PlansSubscriptions`, `PlanItems`, `Templates`, `TmplData` | **Part of domain, normalized** | Source evidence for `ServicePlan` and capabilities; do not copy item class names or template storage |
| `Limits`, `LimitsReservation` | **Part of domain, redesigned** | Supports quota limits and reservations; represent them as typed value objects and Master transactions |
| `Subscriptions` | **Part of domain, redesigned** | Confirms subscription as a distinct allocation; Plesk object polymorphism is not retained |
| `domains`, `subdomains`, `domain_aliases` | **Part of domain, reduced** | Keep canonical Domain and optionally add aliases/subdomains later as child resources |
| `hosting` | **Part of domain, split** | Its intent becomes Website plus typed WebService configuration |
| `DomainServices`, mail/database tables, `db_users` | **Part of domain, split by service family** | Preserve business capabilities, not Plesk coupling or column layout |
| `IP_Addresses`, `ip_pool`, `IpCollections` | **Part of domain only when allocated** | Model allocated `IPAddress`/address pool as infrastructure capacity; do not expose Plesk pools as ownership |
| `ServiceNodes` | **Technical / infrastructure** | Reference for WorkerNode capability and service placement, replaced by `WorkerNode` and `ServiceAssignment` |
| `ScheduledTasks`, `Backups*`, traffic/statistics, caches, upgrade tables, permissions tables, extension tables | **Unneeded for current educational model** | Operational features can be added later without changing core ownership semantics |

## Persistence and lifecycle rules

Master PostgreSQL stores all business entities, typed desired configuration,
ownership, plan snapshots, quota reservations, assignments and accepted
actual-state projections. It does not become a source of truth for provider
processes, files, DNS databases, mail queues or database engine internals.

Every business mutation is transactional in Master. Provisioning is
asynchronous: the transaction commits the desired state and assignment first,
then the responsible Agent reconciles it. Agent reports are accepted only for
the current assignment and a non-stale desired-state version. A failed Agent
operation changes actual/reconciliation state; it must not silently change
ownership, plan limits or placement.

## Explicit non-goals

- This document does not define SQLAlchemy tables, migrations or REST payloads.
- It does not modify the C4/Structurizr model.
- It does not copy Plesk tables, support every Plesk extension, or define billing,
  registrar integration, backups, statistics, failover or a scheduler policy.
