import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ftp_project.master import MasterApiError, MasterClient
from ftp_project.session import AuthenticationClient, LoginError, SessionStore, UserSession


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

    def close(self):
        pass


class CliSessionTests(unittest.TestCase):
    def test_user_create_command_uses_saved_session(self):
        import ftp_project

        session = UserSession("access-1")
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / "session.json")
            store.save(session)
            with patch("ftp_project.SessionStore", return_value=store), patch(
                "ftp_project.MasterClient"
            ) as client_type:
                client_type.return_value.create.return_value = {"id": "user-1"}

                self.assertEqual(ftp_project.main(["user", "create"]), 0)

                client_type.assert_called_once_with(session, base_url="http://localhost:8000")
                client_type.return_value.create.assert_called_once_with(
                    "/v1/users", {"status": "ACTIVE"}
                )

    def test_master_client_sends_session_and_request_id(self):
        request_data = {}

        def opener(request, timeout):
            request_data.update(
                method=request.method,
                url=request.full_url,
                headers=dict(request.header_items()),
                body=request.data,
                timeout=timeout,
            )
            return Response(body=b'{"id":"user-1"}')

        client = MasterClient(
            UserSession("access-1"),
            base_url="http://master:8000",
            opener=opener,
        )

        self.assertEqual(client.create("/v1/users", {"status": "ACTIVE"}, "req-master"), {"id": "user-1"})
        self.assertEqual(request_data["method"], "POST")
        self.assertEqual(request_data["url"], "http://master:8000/v1/users")
        self.assertEqual(request_data["headers"]["Authorization"], "Bearer access-1")
        self.assertEqual(request_data["headers"]["X-request-id"], "req-master")
        self.assertEqual(json.loads(request_data["body"]), {"status": "ACTIVE"})

    def test_master_client_surfaces_api_error(self):
        from urllib.error import HTTPError

        def opener(request, timeout):
            raise HTTPError(
                request.full_url,
                403,
                "Forbidden",
                {},
                Response(body=b'{"code":"AUTHORIZATION_DENIED","message":"no","request_id":"req-master"}'),
            )

        with self.assertRaises(MasterApiError) as context:
            MasterClient(UserSession("access-1"), opener=opener).get("/v1/users/user-1", "req-master")
        self.assertEqual(context.exception.status_code, 403)
        self.assertEqual(context.exception.code, "AUTHORIZATION_DENIED")

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
