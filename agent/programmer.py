from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .config import settings
from .llm import ask_llm
from .repository import read_files


@dataclass(frozen=True)
class ProgrammerResult:
    summary: str
    patch: str


def read_prompt() -> str:
    path = (
        Path(__file__).parent
        / "prompts"
        / "programmer.md"
    )

    return path.read_text(
        encoding="utf-8",
    )


def parse_response(response: str) -> ProgrammerResult:
    try:
        data = json.loads(response)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Programmer returned invalid JSON:\n"
            + response
        ) from exc

    summary = data.get("summary")

    if not isinstance(summary, str):
        raise RuntimeError(
            "Programmer response has no valid summary."
        )

    patch = data.get("patch")

    if not isinstance(patch, str):
        raise RuntimeError(
            "Programmer response has no valid patch."
        )

    return ProgrammerResult(
        summary=summary,
        patch=patch,
    )


def run_programmer(
    root: Path,
    *,
    action: str,
    selected_files: list[str],
    tester_feedback: str = "",
) -> ProgrammerResult:
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

SELECTED IMPLEMENTATION FILES
=============================

{implementation}

PREVIOUS TESTER FEEDBACK
========================

{tester_feedback or "None. This is the first attempt."}

Implement the Architect action.

Return a unified git diff containing only the required changes.
""",
        model=settings.programmer_model,
        max_tokens=settings.programmer_max_tokens,
    )

    return parse_response(response)
