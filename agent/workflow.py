from __future__ import annotations

from .architect import Architect, ArchitecturePlan, Action
from .config import Config
from .llm import OpenRouterLLM
from .programmer import Programmer
from .repository import Repository
from .state import StateFile
from .tester import Tester


class Workflow:
    def __init__(self, config: Config) -> None:
        self.repository = Repository(
            config.repository_root
        )

        self.llm = OpenRouterLLM(config)

        self.architect = Architect(
            self.llm,
            self.repository,
        )

        self.programmer = Programmer(
            self.llm,
            self.repository,
        )

        self.tester = Tester(
            self.llm,
            self.repository,
        )

        self.state = StateFile(
            self.repository
        )

        self.max_iterations = config.max_iterations
        self.max_action_attempts = config.max_action_attempts

    def run(self) -> None:
        for iteration in range(
            1,
            self.max_iterations + 1,
        ):
            print(f"\n=== ITERATION {iteration} ===")

            self.state.update(
                iteration=iteration,
                status="ARCHITECT",
            )

            plan = self.architect.run(iteration)

            if not plan.actions:
                self.state.update(
                    iteration=iteration,
                    status="COMPLETED",
                    summary=plan.summary,
                )

                print("Architecture review has no actions.")
                print("Workflow completed.")

                return

            print(
                f"Architect created "
                f"{len(plan.actions)} action(s)."
            )

            for action in plan.actions:
                self._execute_action(
                    iteration,
                    action,
                )

            self.state.update(
                iteration=iteration,
                status="COMPLETED",
                summary=(
                    f"All {len(plan.actions)} "
                    f"actions passed."
                ),
            )

        raise RuntimeError(
            f"Maximum iterations exceeded: "
            f"{self.max_iterations}"
        )

    def _execute_action(
        self,
        iteration: int,
        action: Action,
    ) -> None:
        feedback = ""

        for attempt in range(
            1,
            self.max_action_attempts + 1,
        ):
            print(
                f"\n[{action.id}] "
                f"attempt {attempt}/"
                f"{self.max_action_attempts}"
            )

            self.state.update(
                iteration=iteration,
                status="PROGRAMMER",
                action=action.id,
            )

            implementation = self.programmer.run(
                action=action,
                tester_feedback=feedback,
            )

            self.state.update(
                iteration=iteration,
                status="TESTER",
                action=action.id,
            )

            result = self.tester.run(
                action=action,
                implementation=implementation,
            )

            if result.status == "PASS":
                print(
                    f"[{action.id}] PASS: "
                    f"{result.summary}"
                )
                return

            feedback = "\n".join(
                result.failures
            )

            print(
                f"[{action.id}] FAIL: "
                f"{result.summary}"
            )

        raise RuntimeError(
            f"Action {action.id} failed after "
            f"{self.max_action_attempts} attempts."
        )
    