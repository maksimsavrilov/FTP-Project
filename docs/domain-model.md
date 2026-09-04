# Domain Model

The domain model describes business entities and their relationships. It is intentionally kept outside the C4 software model: these entities re persisted by the Master and are not C4 components.

## Core model

```text
User
└── Subscription
    ├── ServicePlan
    ├── Domain
    │   ├── Website
    │   │   └── WebService
    │   ├── DnsZone
    │   │   └── DnsRecord
    │   └── MailDomain
    │       └── MailAccount
    └── DatabaseService
        └── DatabaseUser

Service
├── WebService
├── DnsService
├── MailService
└── DatabaseService

Service
└── ServiceAssignment
    └── WorkerNode

Service
├── DesiredState
└── ActualState
```

`Service` is the common lifecycle and placement entity. Concrete service types contain service-specific configuration.

`ServiceAssignment` represents placement explicitly; a service does not directly own a Worker Node.

## Lifecycles

### Domain
```text
PENDING
   ↓
ACTIVE
   ↓
SUSPENDED
   ↓
DELETED
```

### Website

```text
PENDING
   ↓
ACTIVE
   ↓
SUSPENDED
   ↓
DELETED
```

### Service

```text
PENDING
   ↓
PROVISIONING
   ↓
RUNNING
   ↓
DEGRADED
   ↓
STOPPED
   ↓
DELETED
```


### Worker Node

```text
PROVISIONING
   ↓
ONLINE
   ↓
DEGRADED
   ↓
OFFLINE
   ↓
DECOMMISSIONED
```

## Entity definitions

### User


```text
 User
   ├── id
   ├── status
   ├── created_at
   └── updated_at
```

### ServicePlan

```text
ServicePlan
   ├── id
   ├── name
   ├── status
   ├── resource_limits
   ├── object_limits
   ├── created_at
   └── updated_at
```

### Subscription

```text
Subscription
   ├── id
   ├── user_id
   ├── plan_id
   ├── status
   ├── created_at
   └── expires_at
```

### Domain
```text
Domain
   ├── id
   ├── subscription_id
   ├── name
   ├── status
   └── created_at
```

### Website
```text
Website
├── id
├── domain_id
├── status
├── document_root
└── created_at
```

PHP version belongs to the WebService configuration because it is a property of the deployed web service, not of the logical Website.

### DnsZone

```text
DnsZone
├── id
├── domain_id
├── status
└── created_at
```

### DnsRecord

```text
DnsRecord
├── id
├── dns_zone_id
├── name
├── type
├── value
└── ttl
```

### MailDomain

```text
MailDomain
├── id
├── domain_id
├── status
└── created_at
```

### MailAccount

```text
MailAccount
├── id
├── mail_domain_id
├── address
├── status
└── created_at
```


### Service
```text
Service
├── id
├── subscription_id
├── type
├── status
├── created_at
└── updated_at
```


`DesiredState` and `ActualState` are separate state representations and are not Service lifecycle fields.

### WebService

```text
WebService
├── service_id
├── website_id
├── web_server
├── php_version
└── document_root
```


### DnsService

```text
DnsService
└── service_id
```

DNS configuration is represented by `DnsZone` and `DnsRecord`.

### MailService

```text
MailService
└── service_id
```

Mail configuration is represented by `MailDomain` and `MailAccount`.

### DatabaseService

```text
DatabaseService
├── service_id
├── database_type
└── database_name
```

### DatabaseUser

```text
DatabaseUser
├── id
├── database_service_id
├── username
├── status
└── privileges
```

### ServiceAssignment

```text
ServiceAssignment
├── id
├── service_id
├── worker_node_id
├── assigned_at
└── status
```

### WorkerNode

```text
WorkerNode
├── id
├── hostname
├── status
├── capabilities
├── cpu_capacity
├── memory_capacity
├── disk_capacity
├── cpu_usage
├── memory_usage
├── disk_usage
└── last_heartbeat_at
```

### DesiredState

```text
DesiredState
├── service_id
├── version
├── configuration
└── updated_at
```

### ActualState

```text
ActualState
├── service_id
├── version
├── status
├── configuration
├── health
└── observed_at
```

## Relationships

```text
User 1 ─── N Subscription
ServicePlan 1 ─── N Subscription

Subscription 1 ─── N Domain
Domain 1 ─── 0..1 Website
Website 1 ─── 1 WebService

Domain 1 ─── 0..1 DnsZone
DnsZone 1 ─── N DnsRecord

Domain 1 ─── 0..1 MailDomain
MailDomain 1 ─── N MailAccount

Subscription 1 ─── N Service
Service 1 ─── 0..1 WebService
Service 1 ─── 0..1 DnsService
Service 1 ─── 0..1 MailService
Service 1 ─── 0..1 DatabaseService

DatabaseService 1 ─── N DatabaseUser

Service 1 ─── N ServiceAssignment
ServiceAssignment N ─── 1 WorkerNode

Service 1 ─── 1 DesiredState
Service 1 ─── 1 ActualState
```
