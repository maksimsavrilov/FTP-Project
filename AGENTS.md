# Project Instructions

## Architecture
- Master is the control plane.
- Worker Nodes are execution nodes.
- Master stores desired state in PostgreSQL.
- Worker Agents never communicate directly with each other.
- All Master ↔ Agent communication uses REST/HTTP.
- Auth microservice

## Technology
- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- pydantic

## Development Rules
- Use "dsl" service from docker-compose.yml to work with workspace.dsl file. Check if service is already running at first.