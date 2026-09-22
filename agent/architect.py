from pathlib import Path
from datetime import datetime, timezone

from .config import Config
from .llm import OpenRouterLLM


CONTEXT_FILES = [
    "AGENTS.md",
    "STATE.md",
    "roadmap.md",
]


CONTEXT_DIRECTORIES = [
    "structurizr",
    "domain-model",
]


def read_file(path: Path) -> str:
    if not path.exists():
        return f"[FILE NOT FOUND: {path}]"

    if not path.is_file():
        return f"[NOT A FILE: {path}]"

    return path.read_text(encoding="utf-8")


def collect_context(project_root: Path) -> str:
    sections: list[str] = []

    for relative_path in CONTEXT_FILES:
        path = project_root / relative_path

        sections.append(
            f"""
===== {relative_path} =====

{read_file(path)}
"""
        )

    for directory in CONTEXT_DIRECTORIES:
        directory_path = project_root / directory

        if not directory_path.exists():
            sections.append(
                f"\n===== {directory}/ =====\n[DIRECTORY NOT FOUND]\n"
            )
            continue

        for path in sorted(directory_path.rglob("*")):
            if not path.is_file():
                continue

            relative_path = path.relative_to(project_root)

            sections.append(
                f"""
===== {relative_path} =====

{read_file(path)}
"""
            )

    return "\n".join(sections)


def build_prompt(context: str) -> str:
    return f"""
You are reviewing the architecture of the FTP-Project.

Your role is ARCHITECT only.

Do NOT implement code.
Do NOT modify files.
Do NOT invent architecture that is not supported by the project documentation.
Do NOT report a problem without concrete evidence.

The project follows an architecture documented in Structurizr DSL,
domain model documentation, AGENTS.md, STATE.md and roadmap.md.

Your task is to determine whether the current project direction and
implementation are consistent with the documented architecture.

Review the following areas:

1. Architecture consistency
2. Domain model consistency
3. Service and agent boundaries
4. Master/worker responsibilities
5. API boundaries
6. Authentication and authorization boundaries
7. CLI architecture
8. Dependency direction
9. Test coverage of architectural rules
10. Roadmap consistency

For every finding provide:

- unique ID
- severity
- area
- title
- description
- concrete evidence
- expected architecture
- recommended action

Severity must be one of:

- critical
- high
- medium
- low
- info

IMPORTANT:

A finding MUST contain concrete evidence from the supplied project context.

If the architecture is unclear, report it as an architectural ambiguity
rather than inventing a violation.

At the end provide:

- overall status
- architectural strengths
- findings
- recommended next actions

Return ONLY valid JSON.

Expected structure:

{{
  "status": "ok | attention_required | critical",
  "architectural_strengths": [
    "..."
  ],
  "findings": [
    {{
      "id": "ARCH-001",
      "severity": "high",
      "area": "...",
      "title": "...",
      "description": "...",
      "evidence": [
        "..."
      ],
      "expected_architecture": "...",
      "recommended_action": "..."
    }}
  ],
  "next_actions": [
    "..."
  ]
}}

PROJECT CONTEXT:

{context}
"""


def save_review(project_root: Path, content: str, model: str) -> Path:
    review_dir = project_root / "reviews" / "architecture"
    review_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc)
    filename = timestamp.strftime("%Y-%m-%dT%H-%M-%SZ.md")

    path = review_dir / filename

    document = f"""# Architecture Review

**Date:** {timestamp.isoformat()}
**Model:** `{model}`

## Review

```json
{content}
```
"""
    path.write_text(document, encoding="utf-8")

    latest = review_dir / "latest.md"
    latest.write_text(document, encoding="utf-8")

    return path

def run_architecture_review(config: Config) -> Path:
    project_root = Path(config.project_root).resolve()

    print("Collecting project context...")

    context = collect_context(project_root)

    print(f"Context size: {len(context):,} characters")
    print(f"Model: {config.model}")
    print("Running architecture review...")

    llm = OpenRouterLLM(config)

    response = llm.generate(
        build_prompt(context)
    )

    path = save_review(
        project_root,
        response.content,
        response.model,
    )

    print()
    print("Architecture review completed.")
    print(f"Model: {response.model}")
    print(f"Review: {path}")

    return path