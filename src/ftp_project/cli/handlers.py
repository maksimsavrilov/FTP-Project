"""Command handlers for the ftp-project CLI."""

import os
import sys

from ..session import LoginError
from .session import CliContext, run_authenticated


def login(args, context: CliContext) -> int:
    client = context.authentication_client(
        base_url=os.environ.get("FTP_PROJECT_AUTH_URL", "http://localhost:8001")
    )
    try:
        location, state = client.start_login(open_browser=not args.no_browser)
        print(f"Open this URL to log in: {location}")
        callback_url = args.callback_url or input("Paste the callback URL: ").strip()
        client.complete_login(callback_url, state, context.session_store())
    except LoginError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print("Login successful.")
    return 0


def user_create(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before creating a user.",
        lambda client: client.create("/v1/users", {"status": args.status}),
    )


def user_get(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before reading a user.",
        lambda client: client.get(f"/v1/users/{args.user_id}"),
    )


def account_create(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before accessing an account.",
        lambda client: client.create(
            "/v1/accounts",
            {
                "role": args.role,
                "status": args.status,
                "identity_reference_id": args.identity_reference_id,
                "parent_account_id": args.parent_account_id,
            },
        ),
    )


def account_get(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before accessing an account.",
        lambda client: client.get(f"/v1/accounts/{args.account_id}"),
    )


def identity_reference_create(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before accessing an identity reference.",
        lambda client: client.create(
            "/v1/identity-references",
            {"provider": args.provider, "subject_id": args.subject_id},
        ),
    )


def identity_reference_get(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before accessing an identity reference.",
        lambda client: client.get(f"/v1/identity-references/{args.identity_reference_id}"),
    )


def service_plan_create(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before creating a service plan.",
        lambda client: client.create(
            "/v1/service-plans",
            {
                "name": args.name,
                "status": args.status,
                "resource_limits": args.resource_limits,
                "object_limits": args.object_limits,
            },
        ),
    )


def service_create(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before creating a service.",
        lambda client: client.create(
            "/v1/services",
            {"subscription_id": args.subscription_id, "type": args.type,
             "allocation": args.allocation, "lifecycle_state": args.lifecycle_state,
             "configuration": args.configuration},
        ),
    )


def service_get(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before reading a service.",
        lambda client: client.get(f"/v1/services/{args.service_id}"),
    )


def service_state_get(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before reading service state.",
        lambda client: client.get(f"/v1/services/{args.service_id}/state"),
    )


def service_plan_get(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before reading a service plan.",
        lambda client: client.get(f"/v1/service-plans/{args.plan_id}"),
    )


def domain_create(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before creating a domain.",
        lambda client: client.create(
            "/v1/domains",
            {"subscription_id": args.subscription_id, "name": args.name, "status": args.status},
        ),
    )


def domain_get(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before reading a domain.",
        lambda client: client.get(f"/v1/domains/{args.domain_id}"),
    )


def website_create(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before creating a website.",
        lambda client: client.create(
            "/v1/websites",
            {"domain_id": args.domain_id, "document_root": args.document_root, "status": args.status},
        ),
    )


def website_get(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before reading a website.",
        lambda client: client.get(f"/v1/websites/{args.website_id}"),
    )


def mail_domain_create(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before creating a mail domain.",
        lambda client: client.create(
            "/v1/mail-domains",
            {"subscription_id": args.subscription_id, "domain_id": args.domain_id, "status": args.status},
        ),
    )


def mail_domain_get(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before reading a mail domain.",
        lambda client: client.get(f"/v1/mail-domains/{args.mail_domain_id}"),
    )


def mail_account_create(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before creating a mail account.",
        lambda client: client.create(
            "/v1/mail-accounts",
            {"mail_domain_id": args.mail_domain_id, "address": args.address, "status": args.status},
        ),
    )


def mail_account_get(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before reading a mail account.",
        lambda client: client.get(f"/v1/mail-accounts/{args.mail_account_id}"),
    )


def mail_service_create(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before creating a mail service.",
        lambda client: client.create(
            "/v1/mail-services",
            {"subscription_id": args.subscription_id, "domain_id": args.domain_id,
             "allocation": args.allocation, "lifecycle_state": args.lifecycle_state,
             "configuration": args.configuration},
        ),
    )


def mail_service_get(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before reading a mail service.",
        lambda client: client.get(f"/v1/mail-services/{args.mail_service_id}"),
    )


def database_service_create(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before creating a database service.",
        lambda client: client.create(
            "/v1/database-services",
            {"subscription_id": args.subscription_id, "allocation": args.allocation,
             "lifecycle_state": args.lifecycle_state, "database_type": args.database_type,
             "database_name": args.database_name},
        ),
    )


def database_service_get(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before reading a database service.",
        lambda client: client.get(f"/v1/database-services/{args.database_service_id}"),
    )


def database_user_create(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before creating a database user.",
        lambda client: client.create(
            "/v1/database-users",
            {"database_service_id": args.database_service_id, "username": args.username,
             "status": args.status, "privileges": args.privileges},
        ),
    )


def database_user_get(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before reading a database user.",
        lambda client: client.get(f"/v1/database-users/{args.database_user_id}"),
    )


def web_service_create(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before creating a web service.",
        lambda client: client.create(
            "/v1/web-services",
            {"subscription_id": args.subscription_id, "website_id": args.website_id,
             "allocation": args.allocation, "lifecycle_state": args.lifecycle_state,
             "web_server": args.web_server, "php_version": args.php_version,
             "document_root": args.document_root},
        ),
    )


def web_service_get(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before reading a web service.",
        lambda client: client.get(f"/v1/web-services/{args.web_service_id}"),
    )


def dns_service_create(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before creating a DNS service.",
        lambda client: client.create(
            "/v1/dns-services",
            {"subscription_id": args.subscription_id, "domain_id": args.domain_id,
             "allocation": args.allocation, "lifecycle_state": args.lifecycle_state,
             "configuration": args.configuration},
        ),
    )


def dns_service_get(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before reading a DNS service.",
        lambda client: client.get(f"/v1/dns-services/{args.dns_service_id}"),
    )


def subscription_create(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before creating a subscription.",
        lambda client: client.create(
            "/v1/subscriptions",
            {"user_id": args.user_id, "plan_id": args.plan_id,
             "status": args.status, "expires_at": args.expires_at},
        ),
    )


def subscription_get(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before reading a subscription.",
        lambda client: client.get(f"/v1/subscriptions/{args.subscription_id}"),
    )


def entitlement_list(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before accessing an entitlement.",
        lambda client: client.get(f"/v1/subscriptions/{args.subscription_id}/entitlements"),
    )


def entitlement_get(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before accessing an entitlement.",
        lambda client: client.get(
            f"/v1/subscriptions/{args.subscription_id}/entitlements/{args.resource_name}"
        ),
    )


def entitlement_create(args, context):
    return run_authenticated(
        context,
        "No authenticated session. Log in before accessing an entitlement.",
        lambda client: client.create(
            f"/v1/subscriptions/{args.subscription_id}/entitlements",
            {"resource_name": args.resource_name, "source": args.source,
             "limit": args.limit, "usage": args.usage, "reservation": args.reservation},
        ),
    )
