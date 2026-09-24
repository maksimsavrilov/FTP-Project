from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .config import settings
from .llm import ask_llm
from .repository import read_files


@dataclass(frozen=True)
class TesterResult:
    status: str
    summary: str
    failures: list[str]


def read_prompt() -> str:
    path = (
        Path(__file__).parent
        / "prompts"
        / "tester.md"
    )

    return path.read_text(
        encoding="utf-8",
    )


def parse_response(response: str) -> TesterResult:
    try:
        data = json.loads(response)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Tester returned invalid JSON:\n"
            + response
        ) from exc

    status = data.get("status")

    if status not in {"PASS", "FAIL"}:
        raise RuntimeError(
            "Tester returned invalid status."
        )

    summary = data.get("summary", "")

    failures = data.get(
        "failures",
        [],
    )

    if not isinstance(failures, list):
        raise RuntimeError(
            "Tester returned invalid failures."
        )

    return TesterResult(
        status=status,
        summary=str(summary),
        failures=[
            str(item)
            for item in failures
        ],
    )


def run_tests(
    root: Path,
) -> tuple[int, str]:
    import subprocess

    result = subprocess.run(
        ["make", "test"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )

    output = (
        result.stdout
        + "\n"
        + result.stderr
    )

    return (
        result.returncode,
        output[-20000:],
    )


def run_tester(
    root: Path,
    *,
    action: str,
    selected_files: list[str],
    programmer_summary: str,
    baseline_test_exit_code: int,
    baseline_test_output: str,
    current_test_exit_code: int,
    current_test_output: str,
) -> TesterResult:
    system_prompt = read_prompt()

    implementation = read_files(
        root,
        selected_files,
    )

    response = ask_llm(
        system_prompt=system_prompt,
        user_prompt=f"""
ARCHITECT ACTION
================

{action}

PROGRAMMER SUMMARY
==================

{programmer_summary}

RELEVANT IMPLEMENTATION AFTER PROGRAMMER
========================================

{implementation}

BASELINE TEST RESULT
====================

Exit code: {baseline_test_exit_code}

{baseline_test_output}

CURRENT TEST RESULT
===================

Exit code: {current_test_exit_code}

{current_test_output}

Determine whether the Architect action is complete.
""",
        model=settings.tester_model,
        max_tokens=settings.tester_max_tokens,
    )

    return parse_response(response)
