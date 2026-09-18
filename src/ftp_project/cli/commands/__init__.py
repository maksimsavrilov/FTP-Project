"""Domain-specific command declarations."""

from . import hosting, identity, session, subscription


def register_all(registry) -> None:
    for domain in (session, identity, hosting, subscription):
        domain.register(registry)
