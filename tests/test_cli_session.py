import json
import tempfile
import unittest
from pathlib import Path

from ftp_project.session import AuthenticationClient, LoginError, SessionStore


class Response:
    def __init__(self, status=200, body=b"{}", location=None):
        self.status = status
        self.body = body
        self.headers = {"Location": location} if location else {}

    def getcode(self):
        return self.status

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class CliSessionTests(unittest.TestCase):
    def test_login_callback_validates_state_and_persists_session(self):
        callback = "http://localhost:8001/v1/login/callback?code=code-1&state=cli-state"
        responses = iter([
            Response(302, location="https://zitadel.example/oauth/v2/authorize?state=cli-state"),
            Response(body=json.dumps({"access_token": "access-1", "token_type": "Bearer", "expires_in": 3600}).encode()),
        ])
        client = AuthenticationClient(opener=lambda request, timeout: next(responses))
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / "session.json")
            location, state = client.start_login(state="cli-state")
            session = client.complete_login(callback, state, store)
            self.assertIn("zitadel.example", location)
            self.assertEqual(session.authorization, "Bearer access-1")
            self.assertEqual(store.load(), session)

    def test_login_callback_rejects_state_mismatch(self):
        client = AuthenticationClient(opener=lambda request, timeout: self.fail("callback must not be requested"))
        with self.assertRaisesRegex(LoginError, "state"):
            client.complete_login("http://localhost/callback?code=code-1&state=wrong", "expected")


if __name__ == "__main__":
    unittest.main()
