"""Authentication and user command declarations."""

import json

from .. import handlers


def register(registry) -> None:
    registry.register(
        "login", handler=handlers.login,
        arguments=((("--callback-url",), {}), (("--no-browser",), {"action": "store_true"})),
    )
    registry.register(
        "user", "create", handler=handlers.user_create,
        arguments=((("--status",), {"default": "ACTIVE"}),),
    )
    registry.register(
        "user", "get", handler=handlers.user_get,
        arguments=((("user_id",), {}),),
    )
