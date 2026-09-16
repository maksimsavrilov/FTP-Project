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
    account = commands.add_parser("account")
    account_commands = account.add_subparsers(dest="account_command", required=True)
    account_create = account_commands.add_parser("create")
    account_create.add_argument("--role", required=True)
    account_create.add_argument("--status", default="ACTIVE")
    account_create.add_argument("--identity-reference-id")
    account_create.add_argument("--parent-account-id")
    account_get = account_commands.add_parser("get")
    account_get.add_argument("account_id")
    subscription = commands.add_parser("subscription")
    subscription_commands = subscription.add_subparsers(dest="subscription_command", required=True)
    entitlement = subscription_commands.add_parser("entitlement")
    entitlement_commands = entitlement.add_subparsers(dest="entitlement_command", required=True)
    entitlement_list = entitlement_commands.add_parser("list")
    entitlement_list.add_argument("subscription_id")
    entitlement_get = entitlement_commands.add_parser("get")
    entitlement_get.add_argument("subscription_id")
    entitlement_get.add_argument("resource_name")
    entitlement_create = entitlement_commands.add_parser("create")
    entitlement_create.add_argument("subscription_id")
    entitlement_create.add_argument("--resource-name", required=True)
    entitlement_create.add_argument("--source", required=True)
    entitlement_create.add_argument("--limit", type=float, default=0)
    entitlement_create.add_argument("--usage", type=float, default=0)
    entitlement_create.add_argument("--reservation", type=float, default=0)

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

    if args.command == "account":
        session = SessionStore().load()
        if session is None:
            print("No authenticated session. Log in before accessing an account.", file=sys.stderr)
            return 1
        client = MasterClient(
            session,
            base_url=os.environ.get("FTP_PROJECT_MASTER_URL", "http://localhost:8000"),
        )
        try:
            if args.account_command == "get":
                result = client.get(f"/v1/accounts/{args.account_id}")
            else:
                result = client.create(
                    "/v1/accounts",
                    {
                        "role": args.role,
                        "status": args.status,
                        "identity_reference_id": args.identity_reference_id,
                        "parent_account_id": args.parent_account_id,
                    },
                )
        except MasterClientError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(result, sort_keys=True))
        return 0

    if args.command == "subscription" and args.subscription_command == "entitlement":
        session = SessionStore().load()
        if session is None:
            print("No authenticated session. Log in before accessing an entitlement.", file=sys.stderr)
            return 1
        client = MasterClient(
            session,
            base_url=os.environ.get("FTP_PROJECT_MASTER_URL", "http://localhost:8000"),
        )
        try:
            if args.entitlement_command == "list":
                result = client.get(f"/v1/subscriptions/{args.subscription_id}/entitlements")
            elif args.entitlement_command == "get":
                result = client.get(
                    f"/v1/subscriptions/{args.subscription_id}/entitlements/{args.resource_name}"
                )
            else:
                result = client.create(
                    f"/v1/subscriptions/{args.subscription_id}/entitlements",
                    {
                        "resource_name": args.resource_name,
                        "source": args.source,
                        "limit": args.limit,
                        "usage": args.usage,
                        "reservation": args.reservation,
                    },
                )
        except MasterClientError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(result, sort_keys=True))
        return 0

    parser.error("unsupported command")
    return 2
