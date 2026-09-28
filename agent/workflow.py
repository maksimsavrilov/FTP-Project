from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .architect import run_architect
from .config import settings
from .guard import (
    check as guard_check,
    restore_protected_files,
    snapshot_protected_files,
)
from .programmer import run_programmer
from .repository import read_files
from .state import (
    update_after_architect,
    update_after_tests,
    validate_state,
)
from .tester import (
    run_tester,
    run_tests,
)


def latest_iteration(root: Path) -> int:
    path = (
        root
        / "reviews"
        / "architecture"
        / "latest.json"
    )

    if not path.exists():
        return 0

    try:
        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        metadata = data.get(
            "review_metadata",
            {},
        )

        return int(
            metadata.get(
                "iteration",
                0,
            )
        )

    except (
        OSError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
    ):
        return 0


def apply_patch(
    root: Path,
    patch: str,
) -> None:
    if not patch.strip():
        return

    check = subprocess.run(
        [
            "git",
            "apply",
            "--check",
            "--whitespace=nowarn",
        ],
        cwd=root,
        input=patch,
        capture_output=True,
        text=True,
        check=False,
    )

    if check.returncode != 0:
        raise RuntimeError(
            "Programmer returned an invalid patch:\n"
            + check.stderr
        )

    result = subprocess.run(
        [
            "git",
            "apply",
            "--whitespace=nowarn",
        ],
        cwd=root,
        input=patch,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Unable to apply Programmer patch:\n"
            + result.stderr
        )


def run_workflow(root: Path) -> None:
    validate_state(root)

    iteration = latest_iteration(root) + 1

    for _ in range(settings.max_iterations):
        print()
        print(
            f"=== ITERATION {iteration} ==="
        )

        result = run_architect(
            root,
            iteration=iteration,
            update_state=False,
        )

        status = result.get(
            "status",
            "unknown",
        )

        review_file = (
            "reviews/architecture/latest.json"
        )

        next_actions = result.get(
            "next_actions",
            [],
        )

        if not isinstance(
            next_actions,
            list,
        ):
            raise RuntimeError(
                "Architect returned invalid next_actions."
            )

        update_after_architect(
            root,
            review_file=review_file,
            status=str(status),
            next_step=(
                str(next_actions[0])
                if next_actions
                else "No architectural action required."
            ),
        )

        if status == "ok" or not next_actions:
            print(
                "Architect found no further actions."
            )
            return

        action = str(next_actions[0])

        selected_files = (
            result
            .get("review_metadata", {})
            .get("selected_files", [])
        )

        if not isinstance(
            selected_files,
            list,
        ):
            selected_files = []

        selected_files = [
            filename
            for filename in selected_files
            if isinstance(filename, str)
        ]

        execute_action(
            root,
            iteration=iteration,
            action=action,
            selected_files=selected_files,
        )

        iteration += 1

    raise RuntimeError(
        "Maximum Architect iterations exceeded: "
        f"{settings.max_iterations}"
    )


def execute_action(
    root: Path,
    *,
    iteration: int,
    action: str,
    selected_files: list[str],
) -> None:
    baseline_exit_code, baseline_output = (
        run_tests(root)
    )

    tester_feedback = ""

    for attempt in range(
        1,
        settings.max_attempts + 1,
    ):
        print()
        print(
            f"[PROGRAMMER] "
            f"iteration={iteration} "
            f"attempt={attempt}/"
            f"{settings.max_attempts}"
        )

        protected_before = (
            snapshot_protected_files(root)
        )

        programmer = run_programmer(
            root,
            action=action,
            selected_files=selected_files,
            tester_feedback=tester_feedback,
        )

        try:
            apply_patch(
                root,
                programmer.patch,
            )
        except Exception:
            restore_protected_files(
                root,
                protected_before,
            )
            raise

        guard = guard_check(
            root,
            protected_before,
        )

        if not guard.valid:
            print(
                "[GUARD] FAIL: "
                + guard.reason
            )

            restore_protected_files(
                root,
                protected_before,
            )

            tester_feedback = (
                "Repository Guard rejected the previous "
                "implementation.\n\n"
                + guard.reason
            )

            continue

        print(
            "[GUARD] PASS: "
            + guard.reason
        )

        current_exit_code, current_output = (
            run_tests(root)
        )

        print(
            "[TESTS] exit code: "
            f"{current_exit_code}"
        )

        tester = run_tester(
            root,
            action=action,
            selected_files=selected_files,
            programmer_summary=programmer.summary,
            baseline_test_exit_code=baseline_exit_code,
            baseline_test_output=baseline_output,
            current_test_exit_code=current_exit_code,
            current_test_output=current_output,
        )

        update_after_tests(
            root,
            status=tester.status,
            details=(
                f"Iteration: {iteration}\n"
                f"Attempt: {attempt}\n\n"
                f"{tester.summary}"
            ),
        )

        if tester.status == "PASS":
            print(
                "[TESTER] PASS: "
                + tester.summary
            )
            return

        print(
            "[TESTER] FAIL: "
            + tester.summary
        )

        tester_feedback = "\n".join(
            tester.failures
        )

    raise RuntimeError(
        f"Action failed after "
        f"{settings.max_attempts} attempts: "
        f"{action}"
    )
