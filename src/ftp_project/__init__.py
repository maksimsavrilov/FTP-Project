"""Public package API and CLI entry point."""

from .master import MasterApiError, MasterClient, MasterClientError
from .session import AuthenticationClient, LoginError, SessionStore, UserSession
from .worker_agent import WorkerAgentMasterClient
from .cli.parser import build_parser
from .cli.session import CliContext

__all__ = [
    "AuthenticationClient",
    "LoginError",
    "MasterApiError",
    "MasterClient",
    "MasterClientError",
    "SessionStore",
    "UserSession",
    "WorkerAgentMasterClient",
    "main",
]


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and invoke the handler registered by the subparser."""

    args = build_parser().parse_args(argv)
    context = CliContext(AuthenticationClient, MasterClient, SessionStore)
    return args.handler(args, context)
