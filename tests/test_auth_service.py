import asyncio
import json
import unittest

from starlette.requests import Request

from auth.fastapi import create_app
from auth.service import IntrospectionResult


class FakeClient:
    def introspect(self, credential):
        self.credential = credential
        return IntrospectionResult("user-1", "USER", ["service:read"], None)


class AuthenticationServiceTests(unittest.TestCase):
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
