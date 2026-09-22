from __future__ import annotations

from pathlib import Path


IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
    ".idea",
    ".vscode",
}


TEXT_EXTENSIONS = {
    ".py",
    ".md",
    ".yaml",
    ".yml",
    ".toml",
    ".json",
    ".xml",
    ".ini",
    ".cfg",
    ".conf",
    ".dsl",
    ".sql",
    ".sh",
}


def iter_repository_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue

        if any(
            part in IGNORED_DIRS
            for part in path.parts
        ):
            continue

        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue

        yield path


def build_repository_index(root: Path) -> str:
    files = sorted(iter_repository_files(root))

    return "\n".join(
        str(path.relative_to(root))
        for path in files
    )


def resolve_repository_file(
    root: Path,
    filename: str,
) -> Path | None:
    repository_root = root.resolve()
    path = (root / filename).resolve()

    try:
        path.relative_to(repository_root)
    except ValueError:
        return None

    if not path.is_file():
        return None

    if any(
        part in IGNORED_DIRS
        for part in path.relative_to(repository_root).parts
    ):
        return None

    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return None

    return path


def read_files(
    root: Path,
    files: list[str],
    max_file_size: int = 100_000,
) -> str:
    sections: list[str] = []

    for filename in files:
        path = resolve_repository_file(
            root,
            filename,
        )

        if path is None:
            continue

        if path.stat().st_size > max_file_size:
            sections.append(
                f"\n===== {filename} =====\n"
                "[FILE TOO LARGE]\n"
            )
            continue

        try:
            content = path.read_text(
                encoding="utf-8",
            )
        except UnicodeDecodeError:
            continue

        sections.append(
            f"\n===== {filename} =====\n"
            f"{content}\n"
        )

    return "\n".join(sections)