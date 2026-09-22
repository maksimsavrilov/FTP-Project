from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .config import settings
from .llm import ask_llm
from .repository import (
    build_repository_index,
    read_files,
)
from .state import (
    read_state,
    update_after_architect,
    validate_state,
)


def read_prompt(name: str) -> str:
    path = (
        Path(__file__).parent
        / "prompts"
        / name
    )

    return path.read_text(
        encoding="utf-8",
    )


def read_architecture_context(
    root: Path,
) -> str:
    parts: list[str] = []

    for filename in (
        "AGENTS.md",
        "STATE.md",
        "roadmap.md",
    ):
        path = root / filename

        if path.exists():
            parts.append(
                f"\n===== {filename} =====\n"
                + path.read_text(
                    encoding="utf-8",
                )
            )

    for directory in (
        "structurizr",
        "domain-model",
    ):
        path = root / directory

        if not path.exists():
            continue

        for file in sorted(path.rglob("*")):
            if not file.is_file():
                continue

            parts.append(
                f"\n===== {file.relative_to(root)} =====\n"
                + file.read_text(
                    encoding="utf-8",
                )
            )

    return "\n".join(parts)


def parse_json_response(
    response: str,
) -> dict:
    try:
        return json.loads(response)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Architect returned invalid JSON:\n"
            + response
        ) from exc


def discovery(root: Path) -> list[str]:
    system_prompt = read_prompt(
        "architect_discovery.md",
    )

    context = read_architecture_context(root)

    index = build_repository_index(root)

    response = ask_llm(
        system_prompt=system_prompt,
        user_prompt=f"""
ARCHITECTURAL CONTEXT
=====================

{context}

REPOSITORY FILE INDEX
=====================

{index}

Determine which implementation and test files
must be inspected for the architectural review.
""",
    )

    result = parse_json_response(response)

    files = result.get("files")

    if not isinstance(files, list):
        raise RuntimeError(
            "Discovery result contains no valid files list."
        )

    return [
        filename
        for filename in files
        if isinstance(filename, str)
    ]


def perform_review(
    root: Path,
    selected_files: list[str],
) -> dict:
    system_prompt = read_prompt(
        "architect_review.md",
    )

    context = read_architecture_context(root)

    implementation = read_files(
        root,
        selected_files,
    )

    response = ask_llm(
        system_prompt=system_prompt,
        user_prompt=f"""
ARCHITECTURAL CONTEXT
=====================

{context}

IMPLEMENTATION
==============

{implementation}

Perform the architectural review.
""",
    )

    return parse_json_response(response)


def save_review(
    root: Path,
    result: dict,
    selected_files: list[str],
) -> Path:
    directory = (
        root
        / "reviews"
        / "architecture"
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d-%H%M%S"
    )

    result["review_metadata"] = {
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "selected_files": selected_files,
    }

    content = json.dumps(
        result,
        indent=2,
        ensure_ascii=False,
    )

    path = directory / f"{timestamp}.json"

    path.write_text(
        content,
        encoding="utf-8",
    )

    (
        directory / "latest.json"
    ).write_text(
        content,
        encoding="utf-8",
    )

    return path


def extract_next_step(
    result: dict,
) -> str:
    next_actions = result.get(
        "next_actions",
        [],
    )

    if not isinstance(next_actions, list):
        raise RuntimeError(
            "Architect returned invalid next_actions."
        )

    if not next_actions:
        return "No architectural action required."

    return str(next_actions[0])


def run_architect(
    root: Path,
    *,
    update_state: bool = False,
) -> dict:
    validate_state(root)

    print(
        "Architect: discovering relevant files..."
    )

    selected_files = discovery(root)

    print(
        f"Architect: selected "
        f"{len(selected_files)} files."
    )

    print(
        "Architect: performing review..."
    )

    result = perform_review(
        root,
        selected_files,
    )

    review_path = save_review(
        root,
        result,
        selected_files,
    )

    if update_state:
        next_step = extract_next_step(
            result,
        )

        update_after_architect(
            root,
            review_file=str(
                review_path.relative_to(root)
            ),
            status=result.get(
                "status",
                "unknown",
            ),
            next_step=next_step,
        )

    return result
