import asyncio
import json
import unittest

from starlette.requests import Request

from auth.fastapi import create_app
from auth.service import IntrospectionResult, ZitadelClient


class FakeClient:
    def introspect(self, credential):
        self.credential = credential
        return IntrospectionResult("user-1", "USER", ["service:read"], None)

    def authorization_url(self, issuer, client_id, redirect_uri, state):
        return f"{issuer}/authorize?client_id={client_id}&state={state}"

    def exchange_code(self, issuer, code, redirect_uri):
        self.exchange = (issuer, code, redirect_uri)
        return {"access_token": "access-1", "token_type": "Bearer"}


class AuthenticationServiceTests(unittest.TestCase):
    def test_introspection_validates_user_access_token_response(self):
        captured = {}

        class Response:
            def getcode(self):
                return 200

            def read(self):
                return json.dumps({
                    "active": True,
                    "sub": "user-1",
                    "username": "user@example.com",
                    "scope": "service:read",
                    "exp": 123,
                    "token_type": "Bearer",
                }).encode()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def opener(request, timeout):
            captured["body"] = request.data.decode()
            return Response()

        result = ZitadelClient("https://zitadel.example", "client", "secret", opener=opener).introspect("access-1")

        self.assertEqual(result.subject_type, "USER")
        self.assertEqual(result.expires_at, "123")
        self.assertIn("token_type_hint=access_token", captured["body"])

    def test_login_redirects_to_zitadel_and_callback_returns_access_token(self):
        client = FakeClient()
        app = create_app(client, issuer="https://zitadel.example", client_id="client-1", redirect_uri="http://auth/callback")
        login = next(route.endpoint for route in app.routes if route.path == "/v1/login")
        callback = next(route.endpoint for route in app.routes if route.path == "/v1/login/callback")

        login_request = Request({"type": "http", "method": "GET", "path": "/v1/login", "query_string": b"state=cli-state", "headers": []})
        login_response = asyncio.run(login(login_request))
        self.assertEqual(login_response.status_code, 302)
        self.assertEqual(login_response.headers["location"], "https://zitadel.example/authorize?client_id=client-1&state=cli-state")

        callback_request = Request({"type": "http", "method": "GET", "path": "/v1/login/callback", "query_string": b"code=code-1&state=cli-state", "headers": [(b"x-request-id", b"req-login")]})
        callback_response = asyncio.run(callback(callback_request))
        self.assertEqual(callback_response.status_code, 200)
        self.assertEqual(json.loads(callback_response.body), {"access_token": "access-1", "token_type": "Bearer", "request_id": "req-login", "state": "cli-state"})

    def test_authorize_returns_principal_for_allowed_scope(self):
        sent = False

        async def receive():
            nonlocal sent
            if sent:
                return {"type": "http.disconnect"}
            sent = True
            return {
                "type": "http.request",
                "body": b'{"resource":"service:service-1","action":"read"}',
                "more_body": False,
            }

        request = Request(
            {
                "type": "http",
                "http_version": "1.1",
                "method": "POST",
                "scheme": "http",
                "path": "/v1/authorize",
                "raw_path": b"/v1/authorize",
                "query_string": b"",
                "root_path": "",
                "headers": [
                    (b"authorization", b"Bearer token"),
                    (b"x-request-id", b"req-1"),
                ],
                "server": ("testserver", 80),
                "client": ("testclient", 50000),
            },
            receive,
        )
        endpoint = next(route.endpoint for route in create_app(FakeClient()).routes if route.path == "/v1/authorize")
        response = asyncio.run(endpoint(request))

        self.assertEqual(response.status_code, 200)
        response_body = json.loads(response.body)
        self.assertEqual(response_body["request_id"], "req-1")
        self.assertEqual(response_body["principal"]["subject_id"], "user-1")


if __name__ == "__main__":
    unittest.main()
