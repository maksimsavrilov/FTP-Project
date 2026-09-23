from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    project_root: Path
    openrouter_api_key: str
    architect_model: str


def load_settings() -> Settings:
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY environment variable is required."
        )

    return Settings(
        project_root=Path(
            os.getenv("PROJECT_ROOT", ".")
        ).resolve(),
        openrouter_api_key=api_key,
        architect_model=os.getenv(
            "ARCHITECT_MODEL",
            "qwen/qwen3.8-27b:free",
        ),
    )


settings = load_settings()