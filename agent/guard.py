from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from .repository import (
    IGNORED_DIRS,
    TEXT_EXTENSIONS,
)


PROTECTED_FILES = {
    "STATE.md",
    "AGENTS.md",
    "roadmap.md",
}


@dataclass(frozen=True)
class FileSnapshot:
    exists: bool
    digest: str
    content: bytes | None


@dataclass(frozen=True)
class GuardResult:
    valid: bool
    changed_files: list[str]
    protected_files: list[str]
    unexpected_files: list[str]
    reason: str


def _snapshot_file(
    root: Path,
    relative_path: str,
) -> FileSnapshot:
    path = root / relative_path

    if not path.is_file():
        return FileSnapshot(
            exists=False,
            digest="",
            content=None,
        )

    content = path.read_bytes()

    return FileSnapshot(
        exists=True,
        digest=hashlib.sha256(
            content
        ).hexdigest(),
        content=content,
    )


def snapshot_protected_files(
    root: Path,
) -> dict[str, FileSnapshot]:
    return {
        filename: _snapshot_file(
            root,
            filename,
        )
        for filename in PROTECTED_FILES
    }


def restore_protected_files(
    root: Path,
    snapshot: dict[str, FileSnapshot],
) -> None:
    for filename, state in snapshot.items():
        path = root / filename

        if state.exists:
            assert state.content is not None

            path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            path.write_bytes(
                state.content
            )

        elif path.exists():
            path.unlink()


def _git_changed_files(
    root: Path,
) -> list[str]:
    import subprocess

    result = subprocess.run(
        [
            "git",
            "status",
            "--short",
            "--untracked-files=all",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Unable to inspect git working tree:\n"
            + result.stderr
        )

    files: list[str] = []

    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue

        status = line[:2]
        filename = line[3:]

        if "->" in filename:
            filename = filename.split("->", 1)[-1].strip()

        files.append(filename)

    return sorted(set(files))


def check(
    root: Path,
    protected_before: dict[str, FileSnapshot],
) -> GuardResult:
    changed_files = _git_changed_files(root)

    protected_files: list[str] = []

    for filename, before in protected_before.items():
        after = _snapshot_file(
            root,
            filename,
        )

        if (
            before.exists != after.exists
            or before.digest != after.digest
        ):
            protected_files.append(filename)

    if protected_files:
        return GuardResult(
            valid=False,
            changed_files=changed_files,
            protected_files=protected_files,
            unexpected_files=[],
            reason=(
                "Programmer modified protected files: "
                + ", ".join(protected_files)
            ),
        )

    return GuardResult(
        valid=True,
        changed_files=changed_files,
        protected_files=[],
        unexpected_files=[],
        reason="Repository guard passed.",
    )
