"""Backward-compatible wrapper for the standalone Web Agent service."""

from agents.web_agent.app import DesiredWebServiceState, WebAgentDesiredStateStore, create_app

__all__ = ["DesiredWebServiceState", "WebAgentDesiredStateStore", "create_app"]
