from __future__ import annotations

import argparse

from .config import Config
from .workflow import Workflow


def main() -> None:
    parser = argparse.ArgumentParser(
        description="FTP Project development agent"
    )

    parser.add_argument(
        "command",
        choices=["run"],
    )

    args = parser.parse_args()

    if args.command == "run":
        config = Config.from_env()
        Workflow(config).run()


if __name__ == "__main__":
    main()