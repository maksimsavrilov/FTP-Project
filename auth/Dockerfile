FROM python:3.14-slim

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir fastapi uvicorn
COPY auth ./auth

CMD ["uvicorn", "auth.entrypoint:app", "--host", "0.0.0.0", "--port", "8001"]
