"""Account and external identity command declarations."""

from .. import handlers


def register(registry) -> None:
    registry.register(
        "account", "create", handler=handlers.account_create,
        arguments=((("--role",), {"required": True}), (("--status",), {"default": "ACTIVE"}),
                    (("--identity-reference-id",), {}), (("--parent-account-id",), {})),
    )
    registry.register("account", "get", handler=handlers.account_get,
                     arguments=((("account_id",), {}),))
    registry.register(
        "identity-reference", "create", handler=handlers.identity_reference_create,
        arguments=((("--provider",), {"required": True}), (("--subject-id",), {"required": True})),
    )
    registry.register("identity-reference", "get", handler=handlers.identity_reference_get,
                     arguments=((("identity_reference_id",), {}),))
