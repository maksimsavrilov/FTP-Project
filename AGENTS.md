# Project Instructions

## Architecture
- Master is the control plane.
- Worker Nodes are execution nodes.
- Master stores desired state in PostgreSQL.
- Worker Agents never communicate directly with each other.
- All Master ↔ Agent communication uses REST/HTTP.
- Auth as independent microservice

## Technology
- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- pydantic

## Development Rules
- Use "dsl" service from docker-compose.yml to work with workspace.dsl file. Check if service is already running at first.
- Use "plesk" service from docker-compose.yml to check references to Plesk Panel functions, files, CLI utilities and other entities.
    - CLI utilities located at /usr/local/psa/bin and /usr/local/psa/admin/sbin
- For local changes use the Git workflow:
    - Create branch and switch into it
    - Apply changes
    - Request user to review and approve the changes
    - Add changed files to stage
    - Create commit with short informative message
    - Merge branch into main
    - Delete branch