FTP Project is a learning/pet project to create a destributed Web/DB hosting managment system using CLI2API and desired state concept

The CLI commands set is inspired by the one in Plesk panel
(the contents of $PLESK_DIR/bin and $PLESK_DIR/admin/sbin directories or 
https://docs.plesk.com/en-US/obsidian/cli-linux/using-command-line-utilities.40984/ )
Except commands of nodes management


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


The Master is responsible for:
* Registering worker nodes;
* Detecting available resources;
* Accounting for their capacity;
* Scheduling;
* Creating/deleting/modifying services;
* Storing desired state;
* Issuing commands to agents;
* Monitoring the state of worker nodes.

The Worker Agent is responsible for:
* Executing Master commands;
* Installing services;
* Configuration changes;
* Starting/stopping services;
* Creating virtual hosts;
* Creating a database;
* Retrieving the state of the local machine;
* Sending status/health back to the Master.

Workflow example:
CLI

            hosting site create example.com
                        │
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


Worker node resource is abstract

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



C4 Views (Structurizr)

Context

        Admin
        │
        ▼
        Hosting Control System
        │
        ├── Worker Nodes
        ├── DNS
        └── Internet

Container

        Node Agent
        │
        ├── Web Provider
        │     ├── nginx
        │     └── Apache
        │
        └── DB Provider
                ├── MySQL
                └── PostgreSQL

Deployment

                Master VM
              ┌────────────┐
              │ API        │
              │ Scheduler  │
              │ DB         │
              └─────┬──────┘
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
       Worker 1  Worker 2  Worker 3

Sequence

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


Context info for users <-> FTP project interaction

Admin user
* Worker Nodes management/monitoring
* Users management
* Resellers management
* Resources management/monitoring
* Service plans (resources limits hierarchy) management
* Subscriptions management
* Services management

Reseller
* Users management
* Subscriptions management
* Service plans for users management
* Services management

Site users
* Web-hosting management
* DB management
* DNS management
* mail subsystems management