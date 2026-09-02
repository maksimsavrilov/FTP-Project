# FTP Project

FTP Project is a learning/pet project to create a distributed Web/DB hosting management system using CLI2API and the desired state concept.

The CLI command set is inspired by the one in the Plesk panel
(the contents of the $PLESK_DIR/bin and $PLESK_DIR/admin/sbin directories or
https://docs.plesk.com/en-US/obsidian/cli-linux/using-command-line-utilities.40984/).
Except for node management commands.

## C4 Diagram

## Overview, C4 context level

```text
                    Master
                 control plane,
                API/CLI Endpoint
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
      Node Agent   Node Agent   Node Agent
          │            │            │
          ▼            ▼            ▼
       nginx        nginx      MySQL/PostgreSQL
       Apache       Apache
```

The Master is responsible for:

- Registering worker nodes
- Detecting available resources
- Accounting for their capacity
- Scheduling
- Creating/deleting/modifying services
- Storing desired state
- Issuing commands to agents
- Monitoring the state of worker nodes

The Worker Agent is responsible for:

- Executing Master commands
- Installing services
- Configuration changes
- Starting/stopping services
- Creating virtual hosts
- Creating a database
- Retrieving the state of the local machine
- Sending status/health back to the Master

## Workflow example

```text
CLI
  │
  │ hosting site create example.com
  ▼
Master API
  │
  ▼
Desired State DB

website:
  id: website-123
  domain: example.com
  document_root: /var/www/example.com
  php_version: "8.4"

web_service:
id: web-service-123
website_id: website-123

placement:
  node_id: None

provider:
  name: nginx

state:
  desired: RUNNING
  actual: PENDING

dns:
zone: example.com
records:
  - name: "@"
    type: A
    value: 203.0.113.10

  │
  ▼
Desired State
  │
  ▼
Scheduler
  │
  ▼
  ├── Master
  │      web_service:
  │        id: web-service-123
  │        placement:
  │          node_id: worker-03
  │        state:
  │          actual: PROVISIONING
  │
  ▼
Worker Agent
  │
  ├── configure DNS
  ├── install nginx
  ├── configure nginx
  ├── configure Apache
  └── create vhost
  │
  ▼
Master
web_service:
    id: web-service-123
    actual: RUNNING
```

## Worker node resource abstraction

```text
                Worker Node
                    │
                    ├── WebProvider
                    │   ├── nginx
                    │   └── apache
                    │
                    ├── DatabaseProvider
                    │   ├── mysql
                    │   └── postgresql
                    │
                    └── ...
```

## C4 Views (Structurizr)

### Context

```text
        Admin
          │
          ▼
  Hosting Control System
          │
          ├── Worker Nodes
          ├── DNS
          └── Internet
```

### Container

```text
        Node Agent
            │
            ├── Web Provider
            │     ├── nginx
            │     └── Apache
            │
            └── DB Provider
                  ├── MySQL
                  └── PostgreSQL
```


### Sequence

```text
        CLI
         │
         │ create website
         ▼
      Master
         │
         │ schedule
         ▼
    Scheduler
         │
         │ assign
         ▼
  Worker Agent
         │
         ├── configure nginx
         ├── configure Apache
         └── create filesystem
         │
         ▼
      Master
         │
         │ status=running
         ▼
        CLI
```

## Context info for users <-> FTP Project interaction

### Admin user

- Worker Nodes management/monitoring
- Users management
- Resellers management
- Resources management/monitoring
- Service plans (resources limits hierarchy) management
- Service plans for resellers management

### Reseller

- Users management
- Subscriptions management
- Service plans for users management

### Site users

- Services management, including:
  - Web-hosting management
  - DB management
  - DNS management
  - Mail subsystems management

CLI is the only interface; all the UI should be implemented as a CLI wrapper.

```text
            Users
              │
              ▼
             CLI
              │
              ▼
       Master Node
              │
              ▼
       Worker Nodes
```

Master is the control plane and desired state source. Worker Nodes are the execution plane.

```text
                    ┌─────────────┐
                    │    Admin    │
                    └──────┬──────┘
                           │
┌─────────────┐            │            ┌─────────────┐
│ Site User   ├────────────┼────────────┤  Reseller   │
└─────────────┘            ▼            └─────────────┘
                    ┌──────────────┐
                    │     CLI      │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ Master Node  │
                    │              │
                    │ Auth         │
                    │ Control      │
                    │ Desired State│
                    │ Scheduler    │
                    └──────┬───────┘
                           │
                     control plane
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
           Worker       Worker       Worker
            Node         Node         Node
```

### Worker Node structure

```text
Worker Node
  │
  ├── Web Agent
  │   ├── nginx
  │   └── Apache
  │
  ├── DNS Agent
  │   └── BIND
  │
  ├── Mail Agent
  │   └── SMTP / IMAP / POP
  │
  └── DB Agent
      ├── MySQL
      └── PostgreSQL
```

## Master <-> Agents communication

```text
Master
  │
  │ desired state / commands
  ▼
Agent
  │
  ▼
Local service
  │
  │ actual state
  ▼
Agent
  │
  ▼
Master
```

### Worker Node registration

```text
Worker Node
    │
    │ 1. bootstrap credential
    ▼
POST /nodes/register
    │
    ▼
  Master
    │
    ├── creates Node ID
    ├── saves capabilities
    └── issues credentials
          │
          ▼
     Node registered
```

### Worker node registration data

node_id
hostname
OS
CPU
RAM
disk
network
agents:
  - web
  - dns
  - mail
  - database
services:
  - nginx
  - apache
  - bind
  - postfix
  - dovecot
  - mysql
  - postgresql


  ### Worker node heartbeat data

- CPU usage
- RAM usage
- disk usage
- service state


## C4 Container level

### Master

```text
Master Node
│
├── FastAPI
│   ├── Auth management
│   ├── Users
│   ├── Resellers
│   ├── Subscriptions
│   ├── Service Plans
│   ├── Resources
│   ├── Nodes
│   └── Scheduling
│
└── PostgreSQL
      │
      ├── State DB
      └── encrypted secrets


Encryption key
      │
      └── external to DB
```

### Worker

```text
Worker Node
│
├── Web Agent  ──► nginx + Apache
├── DNS Agent  ──► BIND
├── Mail Agent ──► SMTP/IMAP/POP
└── DB Agent   ──► MySQL/PostgreSQL
```


### CLI <-> Master <-> Agents communication protocol

```text
Admin ─────┐        
Reseller ──┼───► CLI
Site User ─┘      │
                 REST
                  │
                  ▼
                Master
                  │
                 REST
                  ├──────────► Web Agent
                  ├──────────► DNS Agent
                  ├──────────► Mail Agent
                  └──────────► DB Agent
```

## Bidirectional control + heartbeat

```text
                  Master
                    │
          ┌─────────┴─────────┐
          │                   │
      Commands            Desired State
          │                   │
          ▼                   ▼
       Agent ───────────────► Master
          │                 Actual State
          │
      heartbeat
          │
          ▼
       Master
```


### Subscription model

```text
User
 └── Subscription
      ├── Web Service
      ├── DNS Service
      ├── Mail Service
      └── DB Service
```

### service model

```text
Subscription
│
├── Web ──► Node 01
├── DNS ──► Node 01
├── Mail ──► Node 02
└── DB ──► Node 17
```

### Services are independent and every service agent gets full data from master

```text
Master
  │
  ├── Web desired state
  │      ├── domain
  │      ├── IP
  │      ├── DNS records
  │      └── Users
  │
  ├── Mail desired state
  │      ├── domain
  │      ├── IP
  │      ├── Users
  │      └── mail configuration
  │
  ├── DNS desired state
  │      └── records
  │
  │
  └── DB desired state
        ├── Name
        ├── Type
        └── Users and ACL

```

## Architecture rule

Worker Agents do not interact to each other. All the cross-service dependencies are resolved by Master and are materialized to desired state of specific Agent.


### Scheduler diagram

1. CLI создаёт Service.
2. Master записывает Service в PostgreSQL со статусом pending.
3. Scheduler выбирает подходящую Node по:
    - capability;
    - доступному CPU/RAM/disk;
    - Service Plan limits;
    - уже размещённым сервисам.
4. Master назначает Service Node.
5. Desired state изменяется.
6. Agent получает новое состояние.
7. Agent выполняет reconciliation.
8. Agent возвращает actual state.
9. Master переводит Service в running либо error.

```text
Control loop

        ┌──────────────┐
        │ Desired State│
        └──────┬───────┘
               ▼
          Scheduler
               │
               ▼
        Service Assignment
               │
               ▼
             Agent
               │
               ▼
         Actual State
               │
               ▼
        ┌──────────────┐
        │    Master    │
        └──────┬───────┘
               │
               └────► reconciliation
```


## High availability principles

Master's scope:
- обнаруживает offline;
- обновляет состояние Node;
- помечает затронутые Services как degraded/unavailable;
- уведомляет Admin;
- не переносит и не восстанавливает сервисы автоматически.

```text
Infrastructure HA
       │
       ├── Master
       └── Worker Nodes

Hosting Control System
       │
       └── monitoring + desired state
```


## Node state list (lifecycle with each to each links)

```text
PROVISIONING
ONLINE
DEGRADED
OFFLINE
DECOMMISSIONED
```


## Service lifecycle

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

e.g.
Web Service
  status = DEGRADED
  reason = nginx configuration failed
```

## C4 Container diagram

```text
                    Admin / Reseller / Site User
                                │
                                ▼
                         ┌──────────────┐
                         │     CLI      │
                         └──────┬───────┘
                                │ REST
                                ▼
                    ┌──────────────────────┐
                    │       Master         │
                    │      FastAPI         │
                    │                      │
                    │ Auth                 │
                    │ Users                │
                    │ Resellers            │
                    │ Subscriptions        │
                    │ Service Plans        │
                    │ Resources            │
                    │ Node Management      │
                    │ Scheduler            │
                    │ Reconciliation       │
                    └──────────┬───────────┘
                               │
                          PostgreSQL
                               │
              REST             │             REST
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│ Worker Node  │       │ Worker Node  │       │ Worker Node  │
│              │       │              │       │              │
│ Web Agent    │       │ Web Agent    │       │ DB Agent     │
│ DNS Agent    │       │ DNS Agent    │       │              │
│ Mail Agent   │       │ Mail Agent   │       │ MySQL        │
│              │       │              │       │ PostgreSQL   │
│ nginx        │       │ nginx        │       │              │
│ Apache       │       │ Apache       │       └──────────────┘
│ BIND         │       │ BIND         │
│ SMTP/IMAP    │       │ SMTP/IMAP    │
└──────────────┘       └──────────────┘
```

Следующий шаг — не писать ещё DSL, а правильно разделить Worker Nodes на два уровня:

- Container View — программные части: Web Agent, DNS Agent, Mail Agent, DB Agent.
- Deployment View — физические Worker Nodes, на которых эти агенты размещаются.

Это важное различие C4.

### Deployment view

```text
                    Hosting Control System
                            │
                    ┌───────▼────────┐
                    │   Master Node  │
                    │                │
                    │ FastAPI        │
                    │ PostgreSQL     │
                    └───────┬────────┘
                            │ REST
             ┌──────────────┼──────────────┐
             │              │              │
             ▼              ▼              ▼
       ┌──────────┐   ┌──────────┐   ┌──────────┐
       │ Worker 1 │   │ Worker 2 │   │ Worker 3 │
       │          │   │          │   │          │
       │ Web      │   │ Web      │   │ Database │
       │ DNS      │   │ DNS      │   │ Agent    │
       │ Mail     │   │ Mail     │   │          │
       │          │   │          │   │ MySQL    │
       │ nginx    │   │ nginx    │   │ PostgreSQL│
       │ Apache   │   │ Apache   │   └──────────┘
       │ BIND     │   │ BIND     │
       │ Mail     │   │ Mail     │
       └──────────┘   └──────────┘
```



## C4 Level 3 — Component Diagram для Master Application.

```text
                    ┌─────────────────────┐
                    │      FastAPI        │
                    │    REST API Layer   │
                    └──────────┬──────────┘
                               │
             ┌─────────────────┼─────────────────┐
             ▼                 ▼                 ▼
       Auth Component    User Management    Subscription
                              │                 │
                              │                 ▼
                              │           Service Manager
                              │                 │
             ┌────────────────┼─────────────────┤
             ▼                ▼                 ▼
       Service Plans     Resource Manager    Node Manager
                                                 │
                                                 ▼
                                            Scheduler
                                                 │
                                                 ▼
                                          Reconciliation
                                                 │
                                                 ▼
                                           Agent Client
                                                 │
                                                 │ REST
                    ┌────────────────────────────┼──────────────┐
                    ▼                            ▼              ▼
                 Web Agent                  DNS Agent       Mail Agent
```

Components

API Layer
- REST API
- Authentication / Authorization

Domain
- User Management
- Reseller Management
- Service Plan Management
- Subscription Management
- Service Management
- Resource Management
- Node Management

Control Plane
- Scheduler
- Reconciliation Manager
- Agent Client

Persistence
- Repositories



### Domain as business-entity
```text
User
 └── Subscription
       └── Domain

Domain
├── id
├── name
├── subscription_id
├── status
└── created_at

Domain
  └── Website

Domain
   │
   ▼
Website
   │
   ▼
Web Service
   │
   ▼
Worker Node

```

### web service entity
```text
Web Service
├── id
├── website_id
├── node_id
├── status
├── web_server
├── php_version
├── document_root
└── desired_state

Website
    domain = example.com
    document_root = /var/www/example.com
    php = 8.4

Web Service
    node = worker-03
    provider = nginx
    status = RUNNING
```

### Components relations
```text
Subscription
 └── Domain
      └── Website
           └── WebService

WebService
    │
    └── ServiceAssignment
            │
            └── WorkerNode

Subscription Management
        │
        └── Domain / Website ownership

Service Management
        │
        └── Web Service

Scheduler
        │
        └── Web Service → Worker Node

Reconciliation
        │
        └── Web Service desired state

Repositories
        │
        ├── Domain
        ├── Website
        └── Web Service

Service
 ├── DesiredState
 └── ActualState
```


### CLI enroll example
```text
domain create example.com
    ↓
  Master
    ↓
Subscription
    ↓
Domain

website create example.com
    ↓
Website
    ↓
Web Service
    ↓
Scheduler
    ↓
Worker Node
    ↓
Reconciliation
    ↓
Web Agent
```