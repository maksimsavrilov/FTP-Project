from __future__ import annotations

import json
from dataclasses import dataclass

from .architect import Action
from .llm import OpenRouterLLM
from .repository import Repository


@dataclass
class ImplementationResult:
    action_id: str
    status: str
    summary: str
    diff: str


class Programmer:
    def __init__(
        self,
        llm: OpenRouterLLM,
        repository: Repository,
    ) -> None:
        self.llm = llm
        self.repository = repository

    def run(
        self,
        action: Action,
        tester_feedback: str = "",
    ) -> ImplementationResult:
        prompt = self._build_prompt(
            action,
            tester_feedback,
        )

        response = self.llm.complete(
            system_prompt=self._system_prompt(),
            user_prompt=prompt,
        )

        data = json.loads(response)

        return ImplementationResult(
            action_id=action.id,
            status=data["status"],
            summary=data["summary"],
            diff=self.repository.git_diff(),
        )

    def _system_prompt(self) -> str:
        return """
You are the Programmer of a software project.

Implement the Architect's requested action directly in the repository.

Rules:

1. Read the existing code before modifying it.
2. Follow AGENTS.md.
3. Do not change architecture outside the requested action.
4. Do not modify STATE.md.
5. Do not invent requirements.
6. Run appropriate tests or validation commands.
7. If Tester feedback is provided, fix the reported failure.
8. Keep the implementation minimal and production-quality.

Return ONLY valid JSON:

{
  "status": "IMPLEMENTED",
  "summary": "..."
}
"""

    def _build_prompt(
        self,
        action: Action,
        tester_feedback: str,
    ) -> str:
        files = []

        for filename in action.files:
            if self.repository.exists(filename):
                files.append(
                    f"\n--- {filename} ---\n"
                    f"{self.repository.read(filename)}"
                )

        feedback = tester_feedback or "No previous Tester feedback."

        return f"""
Action ID: {action.id}

Description:
{action.description}

Acceptance criteria:
{json.dumps(action.acceptance_criteria, indent=2)}

Relevant files:
{"".join(files)}

Previous Tester feedback:
{feedback}

Implement this action now.
"""
    