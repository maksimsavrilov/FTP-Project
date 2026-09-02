User
Subscription
Domain
Website
WebService
WorkerNode

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

### Webservice
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

## Domain model
```text
User
 │
 └── Subscription
       │
       ├── Domain
       │    │
       │    ├── Website
       │    │     │
       │    │     └── WebService
       │    │
       │    ├── DnsZone
       │    │     └── DnsRecord
       │    │
       │    └── MailDomain
       │          └── MailAccount
       │
       └── DatabaseService
              └── DatabaseUser


WebService ─────┐
DnsService ─────┤
MailService ────┤──► Service
DatabaseService ┘

Service
   │
   ▼
ServiceAssignment
   │
   ▼
WorkerNode

Service
   ├── DesiredState
   └── ActualState
```

### Subscription (Business/logical user resources container)
```text
Subscription
├── id
├── user_id
├── plan_id
├── status
├── created_at
└── expires_at
```

### Domain (DNS/domain ownership entity)
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
├── php_version
└── created_at
```

### Service
```text
Service
 ├── WebService
 ├── DnsService
 ├── MailService
 └── DatabaseService

 Service
├── id
├── subscription_id
├── type
├── status
├── desired_state
├── created_at
└── updated_at
```

### Web service
```text
WebService
├── service_id
├── website_id
├── web_server
├── php_version
└── document_root
```

### Database service
```text
DatabaseService
├── service_id
├── database_type
├── database_name
└── ...
```

## Relations
```text
Domain 1 ─── 0..1 Website
Website 1 ─── 1 WebService
WebService N ─── 1 WorkerNode
```