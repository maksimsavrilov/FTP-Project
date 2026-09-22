FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir fastapi uvicorn

COPY agents ./agents

EXPOSE 8002

ENV WEB_AGENT_HOST=0.0.0.0 \
    WEB_AGENT_PORT=8002 \
    WEB_AGENT_LOG_LEVEL=info

CMD ["python", "-m", "agents.web_agent.entrypoint"]
