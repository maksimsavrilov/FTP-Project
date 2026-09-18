"""Session lifecycle helpers used by CLI command handlers."""

import os
import sys
from dataclasses import dataclass
from typing import Callable, Type

from ..master import MasterClient, MasterClientError
from ..session import SessionStore, UserSession


@dataclass(frozen=True)
class CliContext:
    """Runtime dependencies for handlers.

    Keeping dependencies here also makes handlers independent from the package
    entry point and straightforward to exercise in isolation.
    """

    authentication_client: Type
    master_client: Type[MasterClient]
    session_store: Type[SessionStore]


def load_session(context: CliContext, message: str) -> UserSession | None:
    session = context.session_store().load()
    if session is None:
        print(message, file=sys.stderr)
    return session


def master_client(context: CliContext, session: UserSession) -> MasterClient:
    return context.master_client(
        session,
        base_url=os.environ.get("FTP_PROJECT_MASTER_URL", "http://localhost:8000"),
    )


def run_authenticated(
    context: CliContext,
    missing_session_message: str,
    operation: Callable[[MasterClient], object],
) -> int:
    session = load_session(context, missing_session_message)
    if session is None:
        return 1
    try:
        result = operation(master_client(context, session))
    except MasterClientError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    import json

    print(json.dumps(result, sort_keys=True))
    return 0
