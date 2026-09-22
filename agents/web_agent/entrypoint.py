"""Production ASGI entrypoint for the isolated Web Agent service."""

import os

from .app import create_app


app = create_app(master_token=os.environ.get("MASTER_AGENT_TOKEN", ""))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "agents.web_agent.entrypoint:app",
        host=os.environ.get("WEB_AGENT_HOST", "0.0.0.0"),
        port=int(os.environ.get("WEB_AGENT_PORT", "8002")),
        log_level=os.environ.get("WEB_AGENT_LOG_LEVEL", "info"),
    )
