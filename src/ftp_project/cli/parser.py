"""Argument parser and command registration for the CLI."""

import argparse
import json
from collections.abc import Callable

from . import handlers


def _command(parent, name: str, handler: Callable):
    parser = parent.add_parser(name)
    parser.set_defaults(handler=handler)
    return parser


def _resource_commands(parent, resource: str, create_handler, get_handler, *, create_args=(), get_arg="id"):
    commands = parent.add_subparsers(dest=f"{resource.replace('-', '_')}_command", required=True)
    create = _command(commands, "create", create_handler)
    for args, kwargs in create_args:
        create.add_argument(args, **kwargs)
    get = _command(commands, "get", get_handler)
    get.add_argument(get_arg)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ftp-project")
    commands = parser.add_subparsers(dest="command", required=True)

    login = _command(commands, "login", handlers.login)
    login.add_argument("--callback-url")
    login.add_argument("--no-browser", action="store_true")

    user = commands.add_parser("user")
    _resource_commands(
        user,
        "user",
        handlers.user_create,
        handlers.user_get,
        create_args=(("--status", {"default": "ACTIVE"}),),
        get_arg="user_id",
    )

    account = commands.add_parser("account")
    _resource_commands(
        account,
        "account",
        handlers.account_create,
        handlers.account_get,
        create_args=(
            ("--role", {"required": True}),
            ("--status", {"default": "ACTIVE"}),
            ("--identity-reference-id", {}),
            ("--parent-account-id", {}),
        ),
        get_arg="account_id",
    )

    identity = commands.add_parser("identity-reference")
    _resource_commands(
        identity,
        "identity_reference",
        handlers.identity_reference_create,
        handlers.identity_reference_get,
        create_args=(("--provider", {"required": True}), ("--subject-id", {"required": True})),
        get_arg="identity_reference_id",
    )

    service_plan = commands.add_parser("service-plan")
    _resource_commands(
        service_plan,
        "service_plan",
        handlers.service_plan_create,
        handlers.service_plan_get,
        create_args=(
            ("--name", {"required": True}),
            ("--status", {"default": "ACTIVE"}),
            ("--resource-limits", {"type": json.loads, "default": {}}),
            ("--object-limits", {"type": json.loads, "default": {}}),
        ),
        get_arg="plan_id",
    )

    domain = commands.add_parser("domain")
    _resource_commands(
        domain,
        "domain",
        handlers.domain_create,
        handlers.domain_get,
        create_args=(
            ("--subscription-id", {"required": True}),
            ("--name", {"required": True}),
            ("--status", {"default": "PENDING"}),
        ),
        get_arg="domain_id",
    )

    website = commands.add_parser("website")
    _resource_commands(
        website,
        "website",
        handlers.website_create,
        handlers.website_get,
        create_args=(("--domain-id", {"required": True}), ("--document-root", {"required": True}), ("--status", {"default": "PENDING"})),
        get_arg="website_id",
    )

    mail_domain = commands.add_parser("mail-domain")
    _resource_commands(
        mail_domain,
        "mail_domain",
        handlers.mail_domain_create,
        handlers.mail_domain_get,
        create_args=(("--subscription-id", {"required": True}), ("--domain-id", {"required": True}), ("--status", {"default": "PENDING"})),
        get_arg="mail_domain_id",
    )

    mail_account = commands.add_parser("mail-account")
    _resource_commands(
        mail_account,
        "mail_account",
        handlers.mail_account_create,
        handlers.mail_account_get,
        create_args=(("--mail-domain-id", {"required": True}), ("--address", {"required": True}), ("--status", {"default": "PENDING"})),
        get_arg="mail_account_id",
    )

    mail_service = commands.add_parser("mail-service")
    _resource_commands(
        mail_service,
        "mail_service",
        handlers.mail_service_create,
        handlers.mail_service_get,
        create_args=(("--subscription-id", {"required": True}), ("--domain-id", {"required": True}), ("--allocation", {"type": json.loads, "required": True}), ("--lifecycle-state", {"required": True}), ("--configuration", {"type": json.loads, "required": True})),
        get_arg="mail_service_id",
    )

    database_service = commands.add_parser("database-service")
    _resource_commands(
        database_service,
        "database_service",
        handlers.database_service_create,
        handlers.database_service_get,
        create_args=(("--subscription-id", {"required": True}), ("--allocation", {"type": json.loads, "required": True}), ("--lifecycle-state", {"required": True}), ("--database-type", {"required": True}), ("--database-name", {"required": True})),
        get_arg="database_service_id",
    )

    database_user = commands.add_parser("database-user")
    _resource_commands(
        database_user,
        "database_user",
        handlers.database_user_create,
        handlers.database_user_get,
        create_args=(("--database-service-id", {"required": True}), ("--username", {"required": True}), ("--status", {"default": "PENDING"}), ("--privileges", {"type": json.loads, "default": {}})),
        get_arg="database_user_id",
    )

    web_service = commands.add_parser("web-service")
    _resource_commands(
        web_service,
        "web_service",
        handlers.web_service_create,
        handlers.web_service_get,
        create_args=(("--subscription-id", {"required": True}), ("--website-id", {"required": True}), ("--allocation", {"type": json.loads, "required": True}), ("--lifecycle-state", {"required": True}), ("--web-server", {"required": True}), ("--php-version", {"required": True}), ("--document-root", {"required": True})),
        get_arg="web_service_id",
    )

    dns_service = commands.add_parser("dns-service")
    _resource_commands(
        dns_service,
        "dns_service",
        handlers.dns_service_create,
        handlers.dns_service_get,
        create_args=(("--subscription-id", {"required": True}), ("--domain-id", {"required": True}), ("--allocation", {"type": json.loads, "required": True}), ("--lifecycle-state", {"required": True}), ("--configuration", {"type": json.loads, "required": True})),
        get_arg="dns_service_id",
    )

    subscription = commands.add_parser("subscription")
    subscription_commands = subscription.add_subparsers(dest="subscription_command", required=True)
    subscription_create = _command(subscription_commands, "create", handlers.subscription_create)
    subscription_create.add_argument("--user-id", required=True)
    subscription_create.add_argument("--plan-id", required=True)
    subscription_create.add_argument("--status", default="ACTIVE")
    subscription_create.add_argument("--expires-at")
    subscription_get = _command(subscription_commands, "get", handlers.subscription_get)
    subscription_get.add_argument("subscription_id")

    entitlement = subscription_commands.add_parser("entitlement")
    entitlement_commands = entitlement.add_subparsers(dest="entitlement_command", required=True)
    entitlement_list = _command(entitlement_commands, "list", handlers.entitlement_list)
    entitlement_list.add_argument("subscription_id")
    entitlement_get = _command(entitlement_commands, "get", handlers.entitlement_get)
    entitlement_get.add_argument("subscription_id")
    entitlement_get.add_argument("resource_name")
    entitlement_create = _command(entitlement_commands, "create", handlers.entitlement_create)
    entitlement_create.add_argument("subscription_id")
    entitlement_create.add_argument("--resource-name", required=True)
    entitlement_create.add_argument("--source", required=True)
    entitlement_create.add_argument("--limit", type=float, default=0)
    entitlement_create.add_argument("--usage", type=float, default=0)
    entitlement_create.add_argument("--reservation", type=float, default=0)

    return parser
