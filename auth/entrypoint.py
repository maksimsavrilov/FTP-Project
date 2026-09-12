import os

from .fastapi import create_app


app = create_app(
    issuer=os.environ.get("ZITADEL_ISSUER", "http://localhost:8080"),
    client_id=os.environ.get("ZITADEL_CLIENT_ID", ""),
    redirect_uri=os.environ.get("AUTH_LOGIN_REDIRECT_URI", "http://localhost:8001/v1/login/callback"),
)
