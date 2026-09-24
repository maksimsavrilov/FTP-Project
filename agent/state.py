from __future__ import annotations

from pathlib import Path


class StateFile:
    def __init__(self, repository: "Repository") -> None:
        self.repository = repository
        self.path = Path("STATE.md")

    def read(self) -> str:
        if not self.repository.exists(str(self.path)):
            return ""

        return self.repository.read(str(self.path))

    def write(self, content: str) -> None:
        self.repository.write(str(self.path), content)

    def update(
        self,
        *,
        iteration: int,
        status: str,
        action: str = "",
        summary: str = "",
    ) -> None:
        content = f"""# Agent State

## Workflow

- iteration: {iteration}
- status: {status}
- current_action: {action or "none"}

## Summary

{summary}
"""

        self.write(content)