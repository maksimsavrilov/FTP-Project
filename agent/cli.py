import argparse

from .architect import run_architecture_review
from .config import Config


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ftp-agent",
        description="AI agents for FTP-Project",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    architect = subparsers.add_parser(
        "architect",
        help="Run architecture review",
    )

    architect_subparsers = architect.add_subparsers(
        dest="architect_command",
        required=True,
    )

    architect_subparsers.add_parser(
        "review",
        help="Review current project architecture",
    )

    args = parser.parse_args()

    if (
        args.command == "architect"
        and args.architect_command == "review"
    ):
        config = Config.from_environment()
        run_architecture_review(config)


if __name__ == "__main__":
    main()