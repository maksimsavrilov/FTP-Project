# FTP-Project

Distributed hosting control plane with CLI command sed inspired by Plesk Panel.

FTP-Project is an educational backend project for managing hosting services across a distributed set of worker nodes.

The project follows a **control-plane / worker-agent architecture**:

```text
                         ┌──────────────────┐
                         │       CLI        │
                         └────────┬─────────┘
                                  │ REST
                                  ▼
                         ┌──────────────────┐
                         │      Master      │
                         │                  │
                         │ Domain Model     │
                         │ Desired State    │
                         │ Scheduler        │
                         │ Placement        │
                         │ Reconciliation   │
                         └────────┬─────────┘
                                  │
                           REST / versioned
                                  │
                ┌─────────────────┼─────────────────┐
                │                 │                 │
                ▼                 ▼                 ▼
         ┌────────────┐    ┌────────────┐    ┌────────────┐
         │ Web Agent  │    │ DNS Agent  │    │ DB Agent   │
         └─────┬──────┘    └────────────┘    └────────────┘
               │
          ┌────▼─────┐
          │ Provider │
          └────┬─────┘
               │
          ┌────┴─────┐
          ▼          ▼
        Nginx      Apache
```

## Project goals

The project is primarily intended as a practical exploration of:

* distributed system architecture;
* declarative desired state;
* reconciliation loops;
* service placement and scheduling;
* idempotent operations;
* resource management;
* REST-based service communication;
* authentication and authorization;
* provider abstraction;
* automated testing;
* infrastructure-oriented backend development.

The system is intentionally implemented using relatively simple building blocks rather than introducing a large distributed infrastructure stack.

## Current architecture

The system consists of:

### Master

The Master is the control-plane entry point.

It is responsible for:

* authentication and authorization;
* hosting the public REST API;
* managing the domain model;
* storing desired state;
* scheduling services;
* assigning services to worker nodes;
* initiating reconciliation;
* receiving actual state from agents.

### Worker Nodes

Worker nodes provide the execution environment for hosting services.

A worker can run one or more agents.

### Agents

Agents manage a particular type of hosting service on a worker node.

Current/planned agents include:

* Web Agent;
* DNS Agent;
* Mail Agent;
* Database Agent.

Agents do not call other agents directly.

When one service depends on another service, the dependency is represented in the control-plane model and coordinated by the Master.

### Providers

Providers encapsulate implementation-specific behaviour.

For example:

```text
Web Agent
    │
    ▼
WebProvider
    ├── NginxProvider
    └── ApacheProvider
```

The domain model and desired state remain provider-neutral.

This allows the execution implementation to change without coupling the Master to a particular software product.

## Desired state and reconciliation

Services are managed using a desired-state model.

Conceptually:

```text
Desired State
      │
      ▼
   Master
      │
      ▼
Service Assignment
      │
      ▼
    Agent
      │
      ▼
   Provider
      │
      ▼
 Actual State
      │
      └──────────────► Master
```

Agents reconcile the actual state of the worker with the desired state received from the Master.

Operations are designed to be idempotent and version-aware so that stale or duplicated requests do not incorrectly overwrite newer state.

## Example

The CLI is intended to provide commands such as:

```bash
ftp-project login

ftp-project user create alice

ftp-project domain create example.com

ftp-project website create example.com
```

A website creation request eventually becomes a desired state on a worker node:

```text
Master
  │
  ├── Website
  ├── ServiceAssignment
  └── DesiredState
          │
          ▼
      Web Agent
          │
          ▼
      NginxProvider
          │
          ▼
    running website
```

The agent then reports the observed state back to the Master.

## Technology

Current technology choices include:

* Python;
* FastAPI;
* PostgreSQL;
* REST APIs;
* Podman / containers;
* ZITADEL for identity and authentication;
* pytest;
* Structurizr DSL for C4 architecture.

The project is designed to run on Linux.

## Repository structure

```text
.
├── master/                 # Control-plane service
├── agents/                 # Worker agents
├── cli/                    # Command-line interface
├── auth/                   # Authentication/authorization integration
├── tests/                  # Automated tests
│
├── docs/
│   ├── domain-model.md
│   ├── implementation-boundaries.md
│   ├── master-api.md
│   └── master-persistence.md
│
├── structurizr/
│   └── ...                 # C4 architecture model
│
├── STATE.md                # Current development state
├── AGENTS.md               # Instructions for coding agents
└── README.md
```

The repository deliberately separates architectural documentation from implementation documentation.

## Architecture documentation

The following documents are the authoritative sources for different aspects of the system:

| Area                         | Source                              |
| ---------------------------- | ----------------------------------- |
| C4 architecture              | `structurizr/`                      |
| Business domain              | `docs/domain-model.md`              |
| Implementation boundaries    | `docs/implementation-boundaries.md` |
| Master persistence           | `docs/master-persistence.md`        |
| Master API                   | `docs/master-api.md`                |
| Current implementation state | `STATE.md`                          |

`README.md` provides an overview and is not intended to be a second source of truth for the architecture.

## Development

Start the development environment using the project's container configuration.

Then run the relevant services and tests according to the development documentation.

Typical development workflow:

```text
modify code
    │
    ▼
run unit tests
    │
    ▼
run integration tests
    │
    ▼
validate architecture
    │
    ▼
update STATE.md
```

The project uses automated tests to protect both application behaviour and distributed-system semantics.

## Development principles

The project follows several architectural principles:

1. **Master owns desired state.**
2. **Worker agents own local execution.**
3. **Placement is represented by ServiceAssignment.**
4. **Agents do not call other agents directly.**
5. **Desired state is provider-neutral.**
6. **Provider-specific implementation stays inside providers.**
7. **Operations should be idempotent.**
8. **State versions protect against stale updates.**
9. **External infrastructure is responsible for Master/worker availability and failover.**
10. **Architecture is documented separately from implementation details.**

## Project status

The project is under active development.

The current development state and next implementation step are maintained in:

```text
STATE.md
```

For architectural context, start with:

```text
structurizr/
docs/domain-model.md
docs/implementation-boundaries.md
```

## Production authorization

The production stack requires a confidential ZITADEL OAuth client for the
Authentication Service. Create the client in ZITADEL, grant it permission to
introspect tokens, and place its credentials in a local `.env` copied from
`.env.example`:

```sh
cp .env.example .env
```

Set `ZITADEL_CLIENT_ID` and `ZITADEL_CLIENT_SECRET` before starting the
production stack. Compose fails during configuration when either value is
missing, so the Authentication Service cannot silently start without a
configured ZITADEL client.

## License

See `LICENSE` if any ;).
