from __future__ import annotations

import json
from dataclasses import dataclass

from .architect import Action
from .llm import OpenRouterLLM
from .programmer import ImplementationResult
from .repository import Repository


@dataclass
class TestResult:
    action_id: str
    status: str
    summary: str
    failures: list[str]


class Tester:
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
        implementation: ImplementationResult,
    ) -> TestResult:
        commands = self._run_tests()

        prompt = self._build_prompt(
            action,
            implementation,
            commands,
        )

        response = self.llm.complete(
            system_prompt=self._system_prompt(),
            user_prompt=prompt,
        )

        data = json.loads(response)

        return TestResult(
            action_id=action.id,
            status=data["status"],
            summary=data["summary"],
            failures=data.get("failures", []),
        )

    def _run_tests(self) -> list[dict[str, str | int]]:
        commands = [
            ["pytest", "-q"],
        ]

        results = []

        for command in commands:
            code, output = self.repository.run(command)

            results.append(
                {
                    "command": " ".join(command),
                    "exit_code": code,
                    "output": output[-12000:],
                }
            )

        return results

    def _system_prompt(self) -> str:
        return """
You are the Tester of a software project.

Your responsibility is independent validation.

Do NOT modify files.

Evaluate:
1. Architect acceptance criteria.
2. Actual implementation.
3. Test results.
4. Existing project conventions.

PASS only when the acceptance criteria are actually satisfied.

Return ONLY valid JSON:

{
  "status": "PASS" | "FAIL",
  "summary": "...",
  "failures": [
    "..."
  ]
}
"""

    def _build_prompt(
        self,
        action: Action,
        implementation: ImplementationResult,
        tests: list[dict[str, str | int]],
    ) -> str:
        return f"""
Action:
{action.id}

Description:
{action.description}

Acceptance criteria:
{json.dumps(action.acceptance_criteria, indent=2)}

Programmer report:
{implementation.summary}

Git diff:
{self.repository.git_diff()}

Test execution:
{json.dumps(tests, indent=2)}

Determine whether this action is complete.
"""
    