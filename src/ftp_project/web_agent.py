"""Backward-compatible wrapper for the standalone Web Agent service."""

from agents.web_agent.app import DesiredWebServiceState, WebAgentDesiredStateStore, create_app
from agents.web_agent.providers import (
	NginxProvider,
	ProviderApplyResult,
	ProviderConfigurationError,
	ProviderError,
	ProviderExecutionError,
	WebProvider,
)

__all__ = [
	"DesiredWebServiceState",
	"WebAgentDesiredStateStore",
	"NginxProvider",
	"ProviderApplyResult",
	"ProviderConfigurationError",
	"ProviderError",
	"ProviderExecutionError",
	"WebProvider",
	"create_app",
]
