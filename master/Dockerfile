FROM python:3.14-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev --no-install-project

COPY master ./master

EXPOSE 8000

CMD ["uv", "run", "--no-dev", "uvicorn", "master.entrypoint:app", "--host", "0.0.0.0", "--port", "8000"]
