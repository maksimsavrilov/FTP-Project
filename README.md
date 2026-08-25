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

site:
  name: example.com
  type: web
  node: worker-03
  nginx: enabled
  apache: enabled
  php: 8.4

  │
  ▼
Desired State
  │
  ▼
Scheduler
  │
  ▼
Worker Agent
  │
  ├── install nginx
  ├── configure nginx
  ├── configure Apache
  └── create vhost
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
└── State DB (PostgreSQL)
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