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
         │     │
         │     └── Website
         │             │
         │             └── Web Service
         │
         └── other Services
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

### Web service
```text
WebService
├── id
├── website_id
├── node_id
├── status
├── provider
├── php_version
├── document_root
├── desired_state
├── actual_state
├── created_at
└── updated_at
```

## Relations
```text
Domain 1 ─── 0..1 Website
Website 1 ─── 1 WebService
WebService N ─── 1 WorkerNode
```