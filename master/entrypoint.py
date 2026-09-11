"""Production ASGI entrypoint for the Master container."""

from .composition import create_master_app


app = create_master_app()
