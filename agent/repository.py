from __future__ import annotations

import subprocess
from pathlib import Path


IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "dist",
    "build"
    ".structurizr",
    ".idea",
    ".vscode",
}


class Repository:
    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()

    def read(self, relative_path: str) -> str:
        path = self._resolve(relative_path)
        return path.read_text(encoding="utf-8")

    def write(self, relative_path: str, content: str) -> None:
        path = self._resolve(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def exists(self, relative_path: str) -> bool:
        return self._resolve(relative_path).exists()

    def list_files(self) -> list[str]:
        result: list[str] = []

        for path in self.root.rglob("*"):
            if not path.is_file():
                continue

            if any(part in IGNORED_DIRS for part in path.parts):
                continue

            result.append(str(path.relative_to(self.root)))

        return sorted(result)

    def git_diff(self) -> str:
        result = subprocess.run(
            ["git", "diff", "--no-ext-diff"],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )

        return result.stdout

    def run(self, command: list[str]) -> tuple[int, str]:
        result = subprocess.run(
            command,
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )

        output = result.stdout

        if result.stderr:
            output += "\n" + result.stderr

        return result.returncode, output
    