from __future__ import annotations

import argparse

from .architect import run_architect
from .config import settings


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ftp-agent",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    architect = subparsers.add_parser(
        "architect",
    )

    architect_subparsers = (
        architect.add_subparsers(
            dest="action",
            required=True,
        )
    )

    review = architect_subparsers.add_parser(
        "review",
    )

    review.add_argument(
        "--update-state",
        action="store_true",
        help="Update STATE.md with the next step.",
    )

    args = parser.parse_args()

    if (
        args.command == "architect"
        and args.action == "review"
    ):
        result = run_architect(
            settings.project_root,
            update_state=args.update_state,
        )

        print()
        print("Architecture review completed.")
        print(
            f"Status: {result.get('status', 'unknown')}"
        )
        print(
            "Review: "
            "reviews/architecture/latest.json"
        )

        actions = result.get(
            "next_actions",
            [],
        )

        if actions:
            print()
            print("Next step:")
            print(f"  {actions[0]}")

        if args.update_state:
            print()
            print("STATE.md updated.")


if __name__ == "__main__":
    main()