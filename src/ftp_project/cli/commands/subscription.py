"""Subscription and entitlement command declarations."""

from .. import handlers


def register(registry) -> None:
    registry.register("subscription", "create", handler=handlers.subscription_create,
                      arguments=((("--user-id",), {"required": True}), (("--plan-id",), {"required": True}),
                                  (("--status",), {"default": "ACTIVE"}), (("--expires-at",), {})))
    registry.register("subscription", "get", handler=handlers.subscription_get,
                      arguments=((("subscription_id",), {}),))
    registry.register("subscription", "entitlement", "list", handler=handlers.entitlement_list,
                      arguments=((("subscription_id",), {}),))
    registry.register("subscription", "entitlement", "get", handler=handlers.entitlement_get,
                      arguments=((("subscription_id",), {}), (("resource_name",), {})))
    registry.register("subscription", "entitlement", "create", handler=handlers.entitlement_create,
                      arguments=((("subscription_id",), {}), (("--resource-name",), {"required": True}),
                                  (("--source",), {"required": True}), (("--limit",), {"type": float, "default": 0}),
                                  (("--usage",), {"type": float, "default": 0}), (("--reservation",), {"type": float, "default": 0})))
