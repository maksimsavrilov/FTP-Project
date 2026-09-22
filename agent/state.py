from __future__ import annotations

import re
from pathlib import Path


STATE_FILE = "STATE.md"

REQUIRED_SECTIONS = (
    "Current State",
    "Current Task",
    "Next Step",
    "Architectural Constraints",
    "Last Architect Review",
    "Last Test Result",
)


def state_path(root: Path) -> Path:
    return root / STATE_FILE


def read_state(root: Path) -> str:
    path = state_path(root)

    if not path.exists():
        raise RuntimeError(
            f"{STATE_FILE} does not exist."
        )

    return path.read_text(encoding="utf-8")


def validate_state(root: Path) -> None:
    content = read_state(root)

    for section in REQUIRED_SECTIONS:
        pattern = rf"^## {re.escape(section)}\s*$"

        if not re.search(
            pattern,
            content,
            flags=re.MULTILINE,
        ):
            raise RuntimeError(
                f"STATE.md is missing section: {section}"
            )


def replace_section(
    content: str,
    section: str,
    new_content: str,
) -> str:
    pattern = re.compile(
        rf"(^## {re.escape(section)}\s*$)"
        rf"(.*?)"
        rf"(?=^## |\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )

    match = pattern.search(content)

    if not match:
        raise RuntimeError(
            f"STATE.md is missing section: {section}"
        )

    replacement = (
        match.group(1)
        + "\n\n"
        + new_content.strip()
        + "\n\n"
    )

    return (
        content[:match.start()]
        + replacement
        + content[match.end():]
    )


def update_state_sections(
    root: Path,
    *,
    next_step: str | None = None,
    architect_review: str | None = None,
    test_result: str | None = None,
) -> None:
    path = state_path(root)

    content = read_state(root)

    if next_step is not None:
        content = replace_section(
            content,
            "Next Step",
            next_step,
        )

    if architect_review is not None:
        content = replace_section(
            content,
            "Last Architect Review",
            architect_review,
        )

    if test_result is not None:
        content = replace_section(
            content,
            "Last Test Result",
            test_result,
        )

    path.write_text(
        content,
        encoding="utf-8",
    )


def update_after_architect(
    root: Path,
    *,
    review_file: str,
    status: str,
    next_step: str,
) -> None:
    update_state_sections(
        root,
        next_step=next_step,
        architect_review=(
            f"Status: {status}\n\n"
            f"Review: `{review_file}`"
        ),
    )


def update_after_tests(
    root: Path,
    *,
    status: str,
    details: str,
) -> None:
    update_state_sections(
        root,
        test_result=(
            f"Status: {status}\n\n"
            f"{details}"
        ),
    )