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

        if any(part in IGNORED_DIRS for part in path.parts):
            continue

        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue

        yield path


def build_repository_index(root: Path) -> str:
    files = sorted(iter_repository_files(root))

    lines = ["Repository files:", ""]

    for path in files:
        lines.append(str(path.relative_to(root)))

    return "\n".join(lines)


def read_files(
    root: Path,
    files: list[str],
    max_file_size: int = 100_000,
) -> str:
    sections: list[str] = []

    for filename in files:
        path = (root / filename).resolve()

        # Prevent the agent from requesting files outside the repository.
        try:
            path.relative_to(root.resolve())
        except ValueError:
            continue

        if not path.is_file():
            continue

        if path.stat().st_size > max_file_size:
            sections.append(
                f"\n===== {filename} =====\n"
                f"[FILE TOO LARGE: {path.stat().st_size} bytes]\n"
            )
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            sections.append(
                f"\n===== {filename} =====\n"
                "[BINARY OR NON-UTF8 FILE]\n"
            )
            continue

        sections.append(
            f"\n===== {filename} =====\n"
            f"{content}\n"
        )

    return "\n".join(sections)
