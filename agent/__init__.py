"""FTP-Project AI agents.

.env file variables:
OPENROUTER_API_KEY=

OPENROUTER_MODEL=

# Application-level OpenRouter request limiter.
OPENROUTER_REQUESTS_PER_MINUTE=10

# Maximum Programmer -> Tester cycles for one action.
AGENT_MAX_ACTION_ATTEMPTS=3

# Maximum Architect iterations.
AGENT_MAX_ITERATIONS=20

AGENT_REPOSITORY_ROOT=.

uv run python -m agent.cli run

"""