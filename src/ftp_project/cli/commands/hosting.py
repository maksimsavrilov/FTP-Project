"""Hosting resource and worker-service command declarations."""

import json

from .. import handlers


def _create_get(registry, name, create, get, create_args, identifier):
    arguments = tuple(((flag,), kwargs) for flag, kwargs in create_args)
    registry.register(name, "create", handler=create, arguments=arguments)
    registry.register(name, "get", handler=get, arguments=(((identifier,), {}),))


def register(registry) -> None:
    _create_get(registry, "service", handlers.service_create, handlers.service_get,
                (("--subscription-id", {"required": True}), ("--type", {"required": True}),
                 ("--allocation", {"type": json.loads, "required": True}),
                 ("--lifecycle-state", {"required": True}),
                 ("--configuration", {"type": json.loads, "required": True})), "service_id")
    registry.register("service", "state", "get", handler=handlers.service_state_get,
                      arguments=((('service_id',), {}),))
    _create_get(registry, "service-plan", handlers.service_plan_create, handlers.service_plan_get,
                (("--name", {"required": True}), ("--status", {"default": "ACTIVE"}),
                 ("--resource-limits", {"type": json.loads, "default": {}}),
                 ("--object-limits", {"type": json.loads, "default": {}})), "plan_id")
    _create_get(registry, "domain", handlers.domain_create, handlers.domain_get,
                (("--subscription-id", {"required": True}), ("--name", {"required": True}),
                 ("--status", {"default": "PENDING"})), "domain_id")
    _create_get(registry, "website", handlers.website_create, handlers.website_get,
                (("--domain-id", {"required": True}), ("--document-root", {"required": True}),
                 ("--status", {"default": "PENDING"})), "website_id")
    _create_get(registry, "mail-domain", handlers.mail_domain_create, handlers.mail_domain_get,
                (("--subscription-id", {"required": True}), ("--domain-id", {"required": True}),
                 ("--status", {"default": "PENDING"})), "mail_domain_id")
    _create_get(registry, "mail-account", handlers.mail_account_create, handlers.mail_account_get,
                (("--mail-domain-id", {"required": True}), ("--address", {"required": True}),
                 ("--status", {"default": "PENDING"})), "mail_account_id")
    _create_get(registry, "mail-service", handlers.mail_service_create, handlers.mail_service_get,
                (("--subscription-id", {"required": True}), ("--domain-id", {"required": True}),
                 ("--allocation", {"type": json.loads, "required": True}),
                 ("--lifecycle-state", {"required": True}), ("--configuration", {"type": json.loads, "required": True})), "mail_service_id")
    _create_get(registry, "database-service", handlers.database_service_create, handlers.database_service_get,
                (("--subscription-id", {"required": True}), ("--allocation", {"type": json.loads, "required": True}),
                 ("--lifecycle-state", {"required": True}), ("--database-type", {"required": True}),
                 ("--database-name", {"required": True})), "database_service_id")
    _create_get(registry, "database-user", handlers.database_user_create, handlers.database_user_get,
                (("--database-service-id", {"required": True}), ("--username", {"required": True}),
                 ("--status", {"default": "PENDING"}), ("--privileges", {"type": json.loads, "default": {}})), "database_user_id")
    _create_get(registry, "web-service", handlers.web_service_create, handlers.web_service_get,
                (("--subscription-id", {"required": True}), ("--website-id", {"required": True}),
                 ("--allocation", {"type": json.loads, "required": True}), ("--lifecycle-state", {"required": True}),
                 ("--web-server", {"required": True}), ("--php-version", {"required": True}),
                 ("--document-root", {"required": True})), "web_service_id")
    _create_get(registry, "dns-service", handlers.dns_service_create, handlers.dns_service_get,
                (("--subscription-id", {"required": True}), ("--domain-id", {"required": True}),
                 ("--allocation", {"type": json.loads, "required": True}), ("--lifecycle-state", {"required": True}),
                 ("--configuration", {"type": json.loads, "required": True})), "dns_service_id")
