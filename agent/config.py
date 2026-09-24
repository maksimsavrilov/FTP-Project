from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    project_root: Path

    openrouter_api_key: str

    architect_model: str
    programmer_model: str
    tester_model: str

    requests_per_minute: int

    architect_max_tokens: int
    programmer_max_tokens: int
    tester_max_tokens: int

    max_iterations: int
    max_attempts: int


def load_settings() -> Settings:
    load_dotenv()

    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY environment variable is required."
        )

    architect_model = os.getenv(
        "ARCHITECT_MODEL",
        "openrouter/free",
    )

    return Settings(
        project_root=Path(
            os.getenv("PROJECT_ROOT", ".")
        ).resolve(),

        openrouter_api_key=api_key,

        architect_model=architect_model,

        programmer_model=os.getenv(
            "PROGRAMMER_MODEL",
            architect_model,
        ),

        tester_model=os.getenv(
            "TESTER_MODEL",
            architect_model,
        ),

        requests_per_minute=int(
            os.getenv(
                "OPENROUTER_REQUESTS_PER_MINUTE",
                "10",
            )
        ),

        architect_max_tokens=int(
            os.getenv(
                "ARCHITECT_MAX_TOKENS",
                "4096",
            )
        ),

        programmer_max_tokens=int(
            os.getenv(
                "PROGRAMMER_MAX_TOKENS",
                "8192",
            )
        ),

        tester_max_tokens=int(
            os.getenv(
                "TESTER_MAX_TOKENS",
                "4096",
            )
        ),

        max_iterations=int(
            os.getenv(
                "AGENT_MAX_ITERATIONS",
                "20",
            )
        ),

        max_attempts=int(
            os.getenv(
                "AGENT_MAX_ATTEMPTS",
                "3",
            )
        ),
    )


settings = load_settings()