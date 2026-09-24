from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    openrouter_api_key: str
    openrouter_model: str

    # Global request rate limit.
    requests_per_minute: int

    # Maximum number of Programmer/Tester retries for one action.
    max_action_attempts: int

    # Maximum number of Architect iterations.
    max_iterations: int

    repository_root: str

    @classmethod
    def from_env(cls) -> "Config":
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set")

        return cls(
            openrouter_api_key=api_key,
            openrouter_model=os.getenv(
                "OPENROUTER_MODEL",
                "anthropic/claude-sonnet-4.5",
            ),
            requests_per_minute=int(
                os.getenv("OPENROUTER_REQUESTS_PER_MINUTE", "10")
            ),
            max_action_attempts=int(
                os.getenv("AGENT_MAX_ACTION_ATTEMPTS", "3")
            ),
            max_iterations=int(
                os.getenv("AGENT_MAX_ITERATIONS", "20")
            ),
            repository_root=os.getenv(
                "AGENT_REPOSITORY_ROOT",
                ".",
            ),
        )