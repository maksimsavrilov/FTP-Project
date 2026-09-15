import argparse
import json
import os
import sys

from .master import MasterApiError, MasterClient, MasterClientError
from .session import AuthenticationClient, LoginError, SessionStore, UserSession

__all__ = [
    "AuthenticationClient",
    "LoginError",
    "MasterApiError",
    "MasterClient",
    "MasterClientError",
    "SessionStore",
    "UserSession",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ftp-project")
    commands = parser.add_subparsers(dest="command", required=True)
    login = commands.add_parser("login")
    login.add_argument("--callback-url")
    login.add_argument("--no-browser", action="store_true")
    user = commands.add_parser("user")
    user_commands = user.add_subparsers(dest="user_command", required=True)
    create = user_commands.add_parser("create")
    create.add_argument("--status", default="ACTIVE")
    get = user_commands.add_parser("get")
    get.add_argument("user_id")

    args = parser.parse_args(argv)
    if args.command == "login":
        client = AuthenticationClient(
            base_url=os.environ.get("FTP_PROJECT_AUTH_URL", "http://localhost:8001")
        )
        try:
            location, state = client.start_login(open_browser=not args.no_browser)
            print(f"Open this URL to log in: {location}")
            callback_url = args.callback_url or input("Paste the callback URL: ").strip()
            client.complete_login(callback_url, state, SessionStore())
        except LoginError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print("Login successful.")
        return 0

    if args.command == "user" and args.user_command == "create":
        session = SessionStore().load()
        if session is None:
            print("No authenticated session. Log in before creating a user.", file=sys.stderr)
            return 1
        try:
            result = MasterClient(
                session,
                base_url=os.environ.get("FTP_PROJECT_MASTER_URL", "http://localhost:8000"),
            ).create("/v1/users", {"status": args.status})
        except MasterClientError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(result, sort_keys=True))
        return 0

    if args.command == "user" and args.user_command == "get":
        session = SessionStore().load()
        if session is None:
            print("No authenticated session. Log in before reading a user.", file=sys.stderr)
            return 1
        try:
            result = MasterClient(
                session,
                base_url=os.environ.get("FTP_PROJECT_MASTER_URL", "http://localhost:8000"),
            ).get(f"/v1/users/{args.user_id}")
        except MasterClientError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(result, sort_keys=True))
        return 0

    parser.error("unsupported command")
    return 2
