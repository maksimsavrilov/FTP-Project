from __future__ import annotations

import json
from dataclasses import dataclass

from .llm import OpenRouterLLM
from .repository import Repository
from .state import StateFile


@dataclass
class Action:
    id: str
    description: str
    files: list[str]
    acceptance_criteria: list[str]


@dataclass
class ArchitecturePlan:
    summary: str
    actions: list[Action]


class Architect:
    def __init__(
        self,
        llm: OpenRouterLLM,
        repository: Repository,
    ) -> None:
        self.llm = llm
        self.repository = repository
        self.state = StateFile(repository)

    def run(self, iteration: int) -> ArchitecturePlan:
        prompt = self._build_prompt(iteration)

        response = self.llm.complete(
            system_prompt=self._system_prompt(),
            user_prompt=prompt,
        )

        return self._parse(response)

    def _system_prompt(self) -> str:
        return """
You are the Architect of a software project.

Your responsibility is architecture analysis and planning only.

You MUST NOT implement code.

Analyze the current repository and identify concrete implementation
actions for the Programmer.

Every action must contain:
- id
- description
- files
- acceptance_criteria

Only propose actions supported by repository evidence.

Return ONLY valid JSON:

{
  "summary": "...",
  "actions": [
    {
      "id": "A001",
      "description": "...",
      "files": ["..."],
      "acceptance_criteria": ["..."]
    }
  ]
}
"""

    def _build_prompt(self, iteration: int) -> str:
        files = self.repository.list_files()

        context = []

        for filename in (
            "AGENTS.md",
            "STATE.md",
            "roadmap.md",
        ):
            if self.repository.exists(filename):
                context.append(
                    f"\n--- {filename} ---\n"
                    f"{self.repository.read(filename)}"
                )

        return f"""
Iteration: {iteration}

Repository files:
{chr(10).join(files)}

Project context:
{"".join(context)}

Perform the architectural review for this iteration.
Create only actionable work for the Programmer.
"""

    def _parse(self, response: str) -> ArchitecturePlan:
        data = json.loads(response)

        actions = [
            Action(
                id=item["id"],
                description=item["description"],
                files=item.get("files", []),
                acceptance_criteria=item["acceptance_criteria"],
            )
            for item in data["actions"]
        ]

        return ArchitecturePlan(
            summary=data["summary"],
            actions=actions,
        )