from __future__ import annotations

import json
import secrets
import stat
import webbrowser
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


class LoginError(RuntimeError):
    """The Authentication Service could not complete a CLI login."""


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, new):
        return None


@dataclass(frozen=True)
class UserSession:
    access_token: str
    token_type: str = "Bearer"
    refresh_token: str | None = None
    expires_in: int | float | None = None

    @property
    def authorization(self) -> str:
        return f"{self.token_type} {self.access_token}"


class SessionStore:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else Path.home() / ".config" / "ftp-project" / "session.json"

    def load(self) -> UserSession | None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, ValueError):
            return None
        return _session_from_response(data)

    def save(self, session: UserSession) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(asdict(session), sort_keys=True) + "\n", encoding="utf-8")
        self.path.chmod(stat.S_IRUSR | stat.S_IWUSR)

    def clear(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


class AuthenticationClient:
    def __init__(self, base_url: str = "http://localhost:8001", opener: Callable[..., Any] | None = None):
        self.base_url = base_url.rstrip("/")
        self.opener = opener or build_opener(_NoRedirectHandler()).open

    def start_login(self, state: str | None = None, open_browser: bool = False) -> tuple[str, str]:
        state = state or secrets.token_urlsafe(32)
        request = Request(f"{self.base_url}/v1/login?{urlencode({'state': state})}", method="GET")
        try:
            with self._open(request) as response:
                if response.getcode() not in (301, 302, 303, 307, 308):
                    raise LoginError("authentication service returned an invalid login response")
                location = response.headers.get("Location")
        except (HTTPError, URLError, OSError) as exc:
            raise LoginError("authentication service is unavailable") from exc
        if not location:
            raise LoginError("authentication service did not return a login URL")
        if open_browser:
            webbrowser.open(location)
        return location, state

    def complete_login(self, callback_url: str, expected_state: str, store: SessionStore | None = None) -> UserSession:
        query = parse_qs(urlparse(callback_url).query)
        if query.get("state", [None])[0] != expected_state:
            raise LoginError("login state does not match")
        if query.get("error", [None])[0]:
            raise LoginError(query.get("error_description", query["error"])[0])
        if not query.get("code", [None])[0]:
            raise LoginError("login callback does not contain an authorization code")
        request = Request(callback_url, headers={"Accept": "application/json"}, method="GET")
        try:
            with self._open(request) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, OSError, UnicodeDecodeError, ValueError) as exc:
            raise LoginError("authentication service is unavailable") from exc
        if not isinstance(body, dict):
            raise LoginError("authentication service returned an invalid token response")
        if body.get("code"):
            raise LoginError(str(body.get("message", body["code"])))
        session = _session_from_response(body)
        if store:
            store.save(session)
        return session

    def _open(self, request: Request):
        return self.opener(request, timeout=5)


def _session_from_response(response: Any) -> UserSession:
    if not isinstance(response, dict) or not isinstance(response.get("access_token"), str):
        raise LoginError("authentication service returned an invalid access token")
    token_type = response.get("token_type", "Bearer")
    if token_type != "Bearer":
        raise LoginError("authentication service returned an unsupported token type")
    expires_in = response.get("expires_in")
    if expires_in is not None and not isinstance(expires_in, (int, float)):
        raise LoginError("authentication service returned an invalid token expiry")
    refresh_token = response.get("refresh_token")
    if refresh_token is not None and not isinstance(refresh_token, str):
        raise LoginError("authentication service returned an invalid refresh token")
    return UserSession(response["access_token"], token_type, refresh_token, expires_in)
