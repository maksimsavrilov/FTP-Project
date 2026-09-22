from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Config:
    project_root: str
    openrouter_api_key: str
    model: str
    base_url: str = "https://openrouter.ai/api/v1"

    @classmethod
    def from_environment(cls) -> "Config":
        api_key = os.getenv("OPENROUTER_API_KEY")

        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY environment variable is not set"
            )

        return cls(
            project_root=os.getenv("PROJECT_ROOT", "."),
            openrouter_api_key=api_key,
            model=os.getenv(
                "ARCHITECT_MODEL",
                "qwen/qwen3.8-27b:free",
            ),
        )