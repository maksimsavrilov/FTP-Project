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
    identity_reference = commands.add_parser("identity-reference")
    identity_reference_commands = identity_reference.add_subparsers(
        dest="identity_reference_command", required=True
    )
    identity_reference_create = identity_reference_commands.add_parser("create")
    identity_reference_create.add_argument("--provider", required=True)
    identity_reference_create.add_argument("--subject-id", required=True)
    identity_reference_get = identity_reference_commands.add_parser("get")
    identity_reference_get.add_argument("identity_reference_id")
    domain = commands.add_parser("domain")
    domain_commands = domain.add_subparsers(dest="domain_command", required=True)
    domain_create = domain_commands.add_parser("create")
    domain_create.add_argument("--subscription-id", required=True)
    domain_create.add_argument("--name", required=True)
    domain_create.add_argument("--status", default="PENDING")
    website = commands.add_parser("website")
    website_commands = website.add_subparsers(dest="website_command", required=True)
    website_create = website_commands.add_parser("create")
    website_create.add_argument("--domain-id", required=True)
    website_create.add_argument("--document-root", required=True)
    website_create.add_argument("--status", default="PENDING")
    website_get = website_commands.add_parser("get")
    website_get.add_argument("website_id")
    mail_domain = commands.add_parser("mail-domain")
    mail_domain_commands = mail_domain.add_subparsers(dest="mail_domain_command", required=True)
    mail_domain_create = mail_domain_commands.add_parser("create")
    mail_domain_create.add_argument("--subscription-id", required=True)
    mail_domain_create.add_argument("--domain-id", required=True)
    mail_domain_create.add_argument("--status", default="PENDING")
    mail_domain_get = mail_domain_commands.add_parser("get")
    mail_domain_get.add_argument("mail_domain_id")
    mail_account = commands.add_parser("mail-account")
    mail_account_commands = mail_account.add_subparsers(dest="mail_account_command", required=True)
    mail_account_create = mail_account_commands.add_parser("create")
    mail_account_create.add_argument("--mail-domain-id", required=True)
    mail_account_create.add_argument("--address", required=True)
    mail_account_create.add_argument("--status", default="PENDING")
    mail_account_get = mail_account_commands.add_parser("get")
    mail_account_get.add_argument("mail_account_id")
    mail_service = commands.add_parser("mail-service")
    mail_service_commands = mail_service.add_subparsers(dest="mail_service_command", required=True)
    mail_service_create = mail_service_commands.add_parser("create")
    mail_service_create.add_argument("--subscription-id", required=True)
    mail_service_create.add_argument("--domain-id", required=True)
    mail_service_create.add_argument("--allocation", type=json.loads, required=True)
    mail_service_create.add_argument("--lifecycle-state", required=True)
    mail_service_create.add_argument("--configuration", type=json.loads, required=True)
    mail_service_get = mail_service_commands.add_parser("get")
    mail_service_get.add_argument("mail_service_id")
    database_service = commands.add_parser("database-service")
    database_service_commands = database_service.add_subparsers(
        dest="database_service_command", required=True
    )
    database_service_create = database_service_commands.add_parser("create")
    database_service_create.add_argument("--subscription-id", required=True)
    database_service_create.add_argument("--allocation", type=json.loads, required=True)
    database_service_create.add_argument("--lifecycle-state", required=True)
    database_service_create.add_argument("--database-type", required=True)
    database_service_create.add_argument("--database-name", required=True)
    database_service_get = database_service_commands.add_parser("get")
    database_service_get.add_argument("database_service_id")
    database_user = commands.add_parser("database-user")
    database_user_commands = database_user.add_subparsers(
        dest="database_user_command", required=True
    )
    database_user_create = database_user_commands.add_parser("create")
    database_user_create.add_argument("--database-service-id", required=True)
    database_user_create.add_argument("--username", required=True)
    database_user_create.add_argument("--status", default="PENDING")
    database_user_create.add_argument("--privileges", type=json.loads, default={})
    service_plan = commands.add_parser("service-plan")
    service_plan_commands = service_plan.add_subparsers(dest="service_plan_command", required=True)
    service_plan_create = service_plan_commands.add_parser("create")
    service_plan_create.add_argument("--name", required=True)
    service_plan_create.add_argument("--status", default="ACTIVE")
    service_plan_create.add_argument("--resource-limits", type=json.loads, default={})
    service_plan_create.add_argument("--object-limits", type=json.loads, default={})
    service_plan_get = service_plan_commands.add_parser("get")
    service_plan_get.add_argument("plan_id")
    subscription = commands.add_parser("subscription")
    subscription_commands = subscription.add_subparsers(dest="subscription_command", required=True)
    subscription_create = subscription_commands.add_parser("create")
    subscription_create.add_argument("--user-id", required=True)
    subscription_create.add_argument("--plan-id", required=True)
    subscription_create.add_argument("--status", default="ACTIVE")
    subscription_create.add_argument("--expires-at")
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

    if args.command == "identity-reference":
        session = SessionStore().load()
        if session is None:
            print(
                "No authenticated session. Log in before accessing an identity reference.",
                file=sys.stderr,
            )
            return 1
        client = MasterClient(
            session,
            base_url=os.environ.get("FTP_PROJECT_MASTER_URL", "http://localhost:8000"),
        )
        try:
            if args.identity_reference_command == "get":
                result = client.get(f"/v1/identity-references/{args.identity_reference_id}")
            else:
                result = client.create(
                    "/v1/identity-references",
                    {"provider": args.provider, "subject_id": args.subject_id},
                )
        except MasterClientError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(result, sort_keys=True))
        return 0

    if args.command == "service-plan" and args.service_plan_command == "create":
        session = SessionStore().load()
        if session is None:
            print("No authenticated session. Log in before creating a service plan.", file=sys.stderr)
            return 1
        try:
            result = MasterClient(
                session,
                base_url=os.environ.get("FTP_PROJECT_MASTER_URL", "http://localhost:8000"),
            ).create(
                "/v1/service-plans",
                {
                    "name": args.name,
                    "status": args.status,
                    "resource_limits": args.resource_limits,
                    "object_limits": args.object_limits,
                },
            )
        except MasterClientError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(result, sort_keys=True))
        return 0

    if args.command == "service-plan" and args.service_plan_command == "get":
        session = SessionStore().load()
        if session is None:
            print("No authenticated session. Log in before reading a service plan.", file=sys.stderr)
            return 1
        try:
            result = MasterClient(
                session,
                base_url=os.environ.get("FTP_PROJECT_MASTER_URL", "http://localhost:8000"),
            ).get(f"/v1/service-plans/{args.plan_id}")
        except MasterClientError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(result, sort_keys=True))
        return 0

    if args.command == "domain" and args.domain_command == "create":
        session = SessionStore().load()
        if session is None:
            print("No authenticated session. Log in before creating a domain.", file=sys.stderr)
            return 1
        try:
            result = MasterClient(
                session,
                base_url=os.environ.get("FTP_PROJECT_MASTER_URL", "http://localhost:8000"),
            ).create(
                "/v1/domains",
                {
                    "subscription_id": args.subscription_id,
                    "name": args.name,
                    "status": args.status,
                },
            )
        except MasterClientError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(result, sort_keys=True))
        return 0

    if args.command == "website" and args.website_command == "create":
        session = SessionStore().load()
        if session is None:
            print("No authenticated session. Log in before creating a website.", file=sys.stderr)
            return 1
        try:
            result = MasterClient(
                session,
                base_url=os.environ.get("FTP_PROJECT_MASTER_URL", "http://localhost:8000"),
            ).create(
                "/v1/websites",
                {
                    "domain_id": args.domain_id,
                    "document_root": args.document_root,
                    "status": args.status,
                },
            )
        except MasterClientError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(result, sort_keys=True))
        return 0

    if args.command == "website" and args.website_command == "get":
        session = SessionStore().load()
        if session is None:
            print("No authenticated session. Log in before reading a website.", file=sys.stderr)
            return 1
        try:
            result = MasterClient(
                session,
                base_url=os.environ.get("FTP_PROJECT_MASTER_URL", "http://localhost:8000"),
            ).get(f"/v1/websites/{args.website_id}")
        except MasterClientError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(result, sort_keys=True))
        return 0

    if args.command == "mail-domain" and args.mail_domain_command == "create":
        session = SessionStore().load()
        if session is None:
            print("No authenticated session. Log in before creating a mail domain.", file=sys.stderr)
            return 1
        try:
            result = MasterClient(
                session,
                base_url=os.environ.get("FTP_PROJECT_MASTER_URL", "http://localhost:8000"),
            ).create(
                "/v1/mail-domains",
                {
                    "subscription_id": args.subscription_id,
                    "domain_id": args.domain_id,
                    "status": args.status,
                },
            )
        except MasterClientError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(result, sort_keys=True))
        return 0

    if args.command == "mail-domain" and args.mail_domain_command == "get":
        session = SessionStore().load()
        if session is None:
            print("No authenticated session. Log in before reading a mail domain.", file=sys.stderr)
            return 1
        try:
            result = MasterClient(
                session,
                base_url=os.environ.get("FTP_PROJECT_MASTER_URL", "http://localhost:8000"),
            ).get(f"/v1/mail-domains/{args.mail_domain_id}")
        except MasterClientError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(result, sort_keys=True))
        return 0

    if args.command == "mail-account" and args.mail_account_command == "create":
        session = SessionStore().load()
        if session is None:
            print("No authenticated session. Log in before creating a mail account.", file=sys.stderr)
            return 1
        try:
            result = MasterClient(
                session,
                base_url=os.environ.get("FTP_PROJECT_MASTER_URL", "http://localhost:8000"),
            ).create(
                "/v1/mail-accounts",
                {
                    "mail_domain_id": args.mail_domain_id,
                    "address": args.address,
                    "status": args.status,
                },
            )
        except MasterClientError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(result, sort_keys=True))
        return 0

    if args.command == "mail-account" and args.mail_account_command == "get":
        session = SessionStore().load()
        if session is None:
            print("No authenticated session. Log in before reading a mail account.", file=sys.stderr)
            return 1
        try:
            result = MasterClient(
                session,
                base_url=os.environ.get("FTP_PROJECT_MASTER_URL", "http://localhost:8000"),
            ).get(f"/v1/mail-accounts/{args.mail_account_id}")
        except MasterClientError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(result, sort_keys=True))
        return 0

    if args.command == "mail-service" and args.mail_service_command == "create":
        session = SessionStore().load()
        if session is None:
            print("No authenticated session. Log in before creating a mail service.", file=sys.stderr)
            return 1
        try:
            result = MasterClient(
                session,
                base_url=os.environ.get("FTP_PROJECT_MASTER_URL", "http://localhost:8000"),
            ).create(
                "/v1/mail-services",
                {
                    "subscription_id": args.subscription_id,
                    "domain_id": args.domain_id,
                    "allocation": args.allocation,
                    "lifecycle_state": args.lifecycle_state,
                    "configuration": args.configuration,
                },
            )
        except MasterClientError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(result, sort_keys=True))
        return 0

    if args.command == "mail-service" and args.mail_service_command == "get":
        session = SessionStore().load()
        if session is None:
            print("No authenticated session. Log in before reading a mail service.", file=sys.stderr)
            return 1
        try:
            result = MasterClient(
                session,
                base_url=os.environ.get("FTP_PROJECT_MASTER_URL", "http://localhost:8000"),
            ).get(f"/v1/mail-services/{args.mail_service_id}")
        except MasterClientError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(result, sort_keys=True))
        return 0

    if args.command == "database-service" and args.database_service_command == "create":
        session = SessionStore().load()
        if session is None:
            print("No authenticated session. Log in before creating a database service.", file=sys.stderr)
            return 1
        try:
            result = MasterClient(
                session,
                base_url=os.environ.get("FTP_PROJECT_MASTER_URL", "http://localhost:8000"),
            ).create(
                "/v1/database-services",
                {
                    "subscription_id": args.subscription_id,
                    "allocation": args.allocation,
                    "lifecycle_state": args.lifecycle_state,
                    "database_type": args.database_type,
                    "database_name": args.database_name,
                },
            )
        except MasterClientError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(result, sort_keys=True))
        return 0

    if args.command == "database-service" and args.database_service_command == "get":
        session = SessionStore().load()
        if session is None:
            print("No authenticated session. Log in before reading a database service.", file=sys.stderr)
            return 1
        try:
            result = MasterClient(
                session,
                base_url=os.environ.get("FTP_PROJECT_MASTER_URL", "http://localhost:8000"),
            ).get(f"/v1/database-services/{args.database_service_id}")
        except MasterClientError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(result, sort_keys=True))
        return 0

    if args.command == "database-user" and args.database_user_command == "create":
        session = SessionStore().load()
        if session is None:
            print("No authenticated session. Log in before creating a database user.", file=sys.stderr)
            return 1
        try:
            result = MasterClient(
                session,
                base_url=os.environ.get("FTP_PROJECT_MASTER_URL", "http://localhost:8000"),
            ).create(
                "/v1/database-users",
                {
                    "database_service_id": args.database_service_id,
                    "username": args.username,
                    "status": args.status,
                    "privileges": args.privileges,
                },
            )
        except MasterClientError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(result, sort_keys=True))
        return 0

    if args.command == "subscription" and args.subscription_command == "create":
        session = SessionStore().load()
        if session is None:
            print("No authenticated session. Log in before creating a subscription.", file=sys.stderr)
            return 1
        try:
            result = MasterClient(
                session,
                base_url=os.environ.get("FTP_PROJECT_MASTER_URL", "http://localhost:8000"),
            ).create(
                "/v1/subscriptions",
                {
                    "user_id": args.user_id,
                    "plan_id": args.plan_id,
                    "status": args.status,
                    "expires_at": args.expires_at,
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
