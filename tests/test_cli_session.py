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
    def test_login_command_completes_and_stores_session(self):
        import ftp_project

        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / "session.json")
            session = UserSession("access-1")
            with patch("ftp_project.AuthenticationClient") as client_type, patch(
                "ftp_project.SessionStore", return_value=store
            ):
                client_type.return_value.start_login.return_value = (
                    "https://zitadel.example/login",
                    "state-1",
                )
                client_type.return_value.complete_login.return_value = session

                self.assertEqual(
                    ftp_project.main(
                        ["login", "--no-browser", "--callback-url", "http://localhost/callback"]
                    ),
                    0,
                )

                client_type.assert_called_once_with(base_url="http://localhost:8001")
                client_type.return_value.start_login.assert_called_once_with(open_browser=False)
                client_type.return_value.complete_login.assert_called_once_with(
                    "http://localhost/callback", "state-1", store
                )

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

    def test_user_get_command_uses_saved_session(self):
        import ftp_project

        session = UserSession("access-1")
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / "session.json")
            store.save(session)
            with patch("ftp_project.SessionStore", return_value=store), patch(
                "ftp_project.MasterClient"
            ) as client_type:
                client_type.return_value.get.return_value = {"id": "user-1", "status": "ACTIVE"}

                self.assertEqual(ftp_project.main(["user", "get", "user-1"]), 0)

                client_type.assert_called_once_with(session, base_url="http://localhost:8000")
                client_type.return_value.get.assert_called_once_with("/v1/users/user-1")

    def test_account_and_entitlement_commands_use_saved_session(self):
        import ftp_project

        session = UserSession("access-1")
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / "session.json")
            store.save(session)
            with patch("ftp_project.SessionStore", return_value=store), patch(
                "ftp_project.MasterClient"
            ) as client_type:
                client_type.return_value.get.return_value = {"id": "resource-1"}
                client_type.return_value.create.return_value = {"id": "resource-1"}

                self.assertEqual(
                    ftp_project.main(["account", "create", "--role", "CUSTOMER"]), 0
                )
                self.assertEqual(ftp_project.main(["account", "get", "account-1"]), 0)
                self.assertEqual(
                    ftp_project.main(["subscription", "entitlement", "list", "subscription-1"]), 0
                )
                self.assertEqual(
                    ftp_project.main(
                        ["subscription", "entitlement", "get", "subscription-1", "disk"]
                    ),
                    0,
                )
                self.assertEqual(
                    ftp_project.main(
                        [
                            "subscription",
                            "entitlement",
                            "create",
                            "subscription-1",
                            "--resource-name",
                            "disk",
                            "--source",
                            "PLAN",
                            "--limit",
                            "100",
                        ]
                    ),
                    0,
                )

                self.assertEqual(client_type.call_count, 5)
                self.assertEqual(
                    client_type.return_value.create.call_args_list[1].args,
                    (
                        "/v1/subscriptions/subscription-1/entitlements",
                        {
                            "resource_name": "disk",
                            "source": "PLAN",
                            "limit": 100,
                            "usage": 0,
                            "reservation": 0,
                        },
                    ),
                )
                self.assertEqual(
                    client_type.return_value.get.call_args_list[0].args,
                    ("/v1/accounts/account-1",),
                )

    def test_identity_reference_get_command_uses_saved_session(self):
        import ftp_project

        session = UserSession("access-1")
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / "session.json")
            store.save(session)
            with patch("ftp_project.SessionStore", return_value=store), patch(
                "ftp_project.MasterClient"
            ) as client_type:
                client_type.return_value.get.return_value = {
                    "id": "identity-1",
                    "provider": "zitadel",
                    "subject_id": "user-1",
                }

                self.assertEqual(
                    ftp_project.main(["identity-reference", "get", "identity-1"]), 0
                )

                client_type.assert_called_once_with(session, base_url="http://localhost:8000")
                client_type.return_value.get.assert_called_once_with(
                    "/v1/identity-references/identity-1"
                )

    def test_subscription_create_command_uses_saved_session(self):
        import ftp_project

        session = UserSession("access-1")
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / "session.json")
            store.save(session)
            with patch("ftp_project.SessionStore", return_value=store), patch(
                "ftp_project.MasterClient"
            ) as client_type:
                client_type.return_value.create.return_value = {"id": "subscription-1"}

                self.assertEqual(
                    ftp_project.main(
                        [
                            "subscription",
                            "create",
                            "--user-id",
                            "user-1",
                            "--plan-id",
                            "plan-1",
                            "--expires-at",
                            "2027-01-01T00:00:00Z",
                        ]
                    ),
                    0,
                )

                client_type.assert_called_once_with(session, base_url="http://localhost:8000")
                client_type.return_value.create.assert_called_once_with(
                    "/v1/subscriptions",
                    {
                        "user_id": "user-1",
                        "plan_id": "plan-1",
                        "status": "ACTIVE",
                        "expires_at": "2027-01-01T00:00:00Z",
                    },
                )

    def test_subscription_get_command_uses_saved_session(self):
        import ftp_project

        session = UserSession("access-1")
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / "session.json")
            store.save(session)
            with patch("ftp_project.SessionStore", return_value=store), patch(
                "ftp_project.MasterClient"
            ) as client_type:
                client_type.return_value.get.return_value = {
                    "id": "subscription-1",
                    "status": "ACTIVE",
                }

                self.assertEqual(
                    ftp_project.main(["subscription", "get", "subscription-1"]), 0
                )

                client_type.assert_called_once_with(session, base_url="http://localhost:8000")
                client_type.return_value.get.assert_called_once_with(
                    "/v1/subscriptions/subscription-1"
                )

    def test_identity_reference_create_command_uses_saved_session(self):
        import ftp_project

        session = UserSession("access-1")
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / "session.json")
            store.save(session)
            with patch("ftp_project.SessionStore", return_value=store), patch(
                "ftp_project.MasterClient"
            ) as client_type:
                client_type.return_value.create.return_value = {"id": "identity-1"}

                self.assertEqual(
                    ftp_project.main(
                        [
                            "identity-reference",
                            "create",
                            "--provider",
                            "zitadel",
                            "--subject-id",
                            "user-1",
                        ]
                    ),
                    0,
                )

                client_type.assert_called_once_with(session, base_url="http://localhost:8000")
                client_type.return_value.create.assert_called_once_with(
                    "/v1/identity-references",
                    {"provider": "zitadel", "subject_id": "user-1"},
                )

    def test_service_plan_create_command_uses_saved_session(self):
        import ftp_project

        session = UserSession("access-1")
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / "session.json")
            store.save(session)
            with patch("ftp_project.SessionStore", return_value=store), patch(
                "ftp_project.MasterClient"
            ) as client_type:
                client_type.return_value.create.return_value = {"id": "plan-1"}

                self.assertEqual(
                    ftp_project.main(
                        [
                            "service-plan",
                            "create",
                            "--name",
                            "small",
                            "--resource-limits",
                            '{"cpu": 2}',
                            "--object-limits",
                            '{"domains": 5}',
                        ]
                    ),
                    0,
                )

                client_type.assert_called_once_with(session, base_url="http://localhost:8000")
                client_type.return_value.create.assert_called_once_with(
                    "/v1/service-plans",
                    {
                        "name": "small",
                        "status": "ACTIVE",
                        "resource_limits": {"cpu": 2},
                        "object_limits": {"domains": 5},
                    },
                )

    def test_service_plan_get_command_uses_saved_session(self):
        import ftp_project

        session = UserSession("access-1")
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / "session.json")
            store.save(session)
            with patch("ftp_project.SessionStore", return_value=store), patch(
                "ftp_project.MasterClient"
            ) as client_type:
                client_type.return_value.get.return_value = {"id": "plan-1", "name": "small"}

                self.assertEqual(ftp_project.main(["service-plan", "get", "plan-1"]), 0)

                client_type.assert_called_once_with(session, base_url="http://localhost:8000")
                client_type.return_value.get.assert_called_once_with("/v1/service-plans/plan-1")

    def test_domain_create_command_uses_saved_session(self):
        import ftp_project

        session = UserSession("access-1")
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / "session.json")
            store.save(session)
            with patch("ftp_project.SessionStore", return_value=store), patch(
                "ftp_project.MasterClient"
            ) as client_type:
                client_type.return_value.create.return_value = {"id": "domain-1"}

                self.assertEqual(
                    ftp_project.main(
                        [
                            "domain",
                            "create",
                            "--subscription-id",
                            "subscription-1",
                            "--name",
                            "example.test",
                        ]
                    ),
                    0,
                )

                client_type.assert_called_once_with(session, base_url="http://localhost:8000")
                client_type.return_value.create.assert_called_once_with(
                    "/v1/domains",
                    {
                        "subscription_id": "subscription-1",
                        "name": "example.test",
                        "status": "PENDING",
                    },
                )

    def test_website_create_command_uses_saved_session(self):
        import ftp_project

        session = UserSession("access-1")
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / "session.json")
            store.save(session)
            with patch("ftp_project.SessionStore", return_value=store), patch(
                "ftp_project.MasterClient"
            ) as client_type:
                client_type.return_value.create.return_value = {"id": "website-1"}

                self.assertEqual(
                    ftp_project.main(
                        [
                            "website",
                            "create",
                            "--domain-id",
                            "domain-1",
                            "--document-root",
                            "/var/www/example.test",
                        ]
                    ),
                    0,
                )

                client_type.assert_called_once_with(session, base_url="http://localhost:8000")
                client_type.return_value.create.assert_called_once_with(
                    "/v1/websites",
                    {
                        "domain_id": "domain-1",
                        "document_root": "/var/www/example.test",
                        "status": "PENDING",
                    },
                )

    def test_website_get_command_uses_saved_session(self):
        import ftp_project

        session = UserSession("access-1")
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / "session.json")
            store.save(session)
            with patch("ftp_project.SessionStore", return_value=store), patch(
                "ftp_project.MasterClient"
            ) as client_type:
                client_type.return_value.get.return_value = {
                    "id": "website-1",
                    "domain_id": "domain-1",
                }

                self.assertEqual(ftp_project.main(["website", "get", "website-1"]), 0)

                client_type.assert_called_once_with(session, base_url="http://localhost:8000")
                client_type.return_value.get.assert_called_once_with("/v1/websites/website-1")

    def test_mail_domain_create_command_uses_saved_session(self):
        import ftp_project

        session = UserSession("access-1")
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / "session.json")
            store.save(session)
            with patch("ftp_project.SessionStore", return_value=store), patch(
                "ftp_project.MasterClient"
            ) as client_type:
                client_type.return_value.create.return_value = {"id": "mail-domain-1"}

                self.assertEqual(
                    ftp_project.main(
                        [
                            "mail-domain",
                            "create",
                            "--subscription-id",
                            "subscription-1",
                            "--domain-id",
                            "domain-1",
                        ]
                    ),
                    0,
                )

                client_type.assert_called_once_with(session, base_url="http://localhost:8000")
                client_type.return_value.create.assert_called_once_with(
                    "/v1/mail-domains",
                    {
                        "subscription_id": "subscription-1",
                        "domain_id": "domain-1",
                        "status": "PENDING",
                    },
                )

    def test_mail_domain_get_command_uses_saved_session(self):
        import ftp_project

        session = UserSession("access-1")
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / "session.json")
            store.save(session)
            with patch("ftp_project.SessionStore", return_value=store), patch(
                "ftp_project.MasterClient"
            ) as client_type:
                client_type.return_value.get.return_value = {
                    "id": "mail-domain-1",
                    "domain_id": "domain-1",
                }

                self.assertEqual(
                    ftp_project.main(["mail-domain", "get", "mail-domain-1"]), 0
                )

                client_type.assert_called_once_with(session, base_url="http://localhost:8000")
                client_type.return_value.get.assert_called_once_with(
                    "/v1/mail-domains/mail-domain-1"
                )

    def test_mail_account_create_command_uses_saved_session(self):
        import ftp_project

        session = UserSession("access-1")
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / "session.json")
            store.save(session)
            with patch("ftp_project.SessionStore", return_value=store), patch(
                "ftp_project.MasterClient"
            ) as client_type:
                client_type.return_value.create.return_value = {"id": "mail-account-1"}

                self.assertEqual(
                    ftp_project.main(
                        [
                            "mail-account",
                            "create",
                            "--mail-domain-id",
                            "mail-domain-1",
                            "--address",
                            "postmaster@example.test",
                        ]
                    ),
                    0,
                )

                client_type.assert_called_once_with(session, base_url="http://localhost:8000")
                client_type.return_value.create.assert_called_once_with(
                    "/v1/mail-accounts",
                    {
                        "mail_domain_id": "mail-domain-1",
                        "address": "postmaster@example.test",
                        "status": "PENDING",
                    },
                )

    def test_mail_account_get_command_uses_saved_session(self):
        import ftp_project

        session = UserSession("access-1")
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / "session.json")
            store.save(session)
            with patch("ftp_project.SessionStore", return_value=store), patch(
                "ftp_project.MasterClient"
            ) as client_type:
                client_type.return_value.get.return_value = {
                    "id": "mail-account-1",
                    "mail_domain_id": "mail-domain-1",
                }

                self.assertEqual(
                    ftp_project.main(["mail-account", "get", "mail-account-1"]), 0
                )

                client_type.assert_called_once_with(session, base_url="http://localhost:8000")
                client_type.return_value.get.assert_called_once_with(
                    "/v1/mail-accounts/mail-account-1"
                )

    def test_mail_service_create_command_uses_saved_session(self):
        import ftp_project

        session = UserSession("access-1")
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / "session.json")
            store.save(session)
            with patch("ftp_project.SessionStore", return_value=store), patch(
                "ftp_project.MasterClient"
            ) as client_type:
                client_type.return_value.create.return_value = {"id": "mail-service-1"}

                self.assertEqual(
                    ftp_project.main(
                        [
                            "mail-service",
                            "create",
                            "--subscription-id",
                            "subscription-1",
                            "--domain-id",
                            "domain-1",
                            "--allocation",
                            '{"cpu": 1, "memory": 512, "disk": 1000}',
                            "--lifecycle-state",
                            "PROVISIONING",
                            "--configuration",
                            '{"mail_domains": []}',
                        ]
                    ),
                    0,
                )

                client_type.assert_called_once_with(session, base_url="http://localhost:8000")
                client_type.return_value.create.assert_called_once_with(
                    "/v1/mail-services",
                    {
                        "subscription_id": "subscription-1",
                        "domain_id": "domain-1",
                        "allocation": {"cpu": 1, "memory": 512, "disk": 1000},
                        "lifecycle_state": "PROVISIONING",
                        "configuration": {"mail_domains": []},
                    },
                )

    def test_mail_service_get_command_uses_saved_session(self):
        import ftp_project

        session = UserSession("access-1")
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / "session.json")
            store.save(session)
            with patch("ftp_project.SessionStore", return_value=store), patch(
                "ftp_project.MasterClient"
            ) as client_type:
                client_type.return_value.get.return_value = {
                    "id": "mail-service-1",
                    "type": "MAIL",
                }

                self.assertEqual(
                    ftp_project.main(["mail-service", "get", "mail-service-1"]), 0
                )

                client_type.assert_called_once_with(session, base_url="http://localhost:8000")
                client_type.return_value.get.assert_called_once_with(
                    "/v1/mail-services/mail-service-1"
                )

    def test_database_service_create_command_uses_saved_session(self):
        import ftp_project

        session = UserSession("access-1")
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / "session.json")
            store.save(session)
            with patch("ftp_project.SessionStore", return_value=store), patch(
                "ftp_project.MasterClient"
            ) as client_type:
                client_type.return_value.create.return_value = {"id": "database-service-1"}

                self.assertEqual(
                    ftp_project.main(
                        [
                            "database-service",
                            "create",
                            "--subscription-id",
                            "subscription-1",
                            "--allocation",
                            '{"cpu": 2, "memory": 1024, "disk": 5000}',
                            "--lifecycle-state",
                            "PROVISIONING",
                            "--database-type",
                            "postgresql",
                            "--database-name",
                            "app_db",
                        ]
                    ),
                    0,
                )

                client_type.assert_called_once_with(session, base_url="http://localhost:8000")
                client_type.return_value.create.assert_called_once_with(
                    "/v1/database-services",
                    {
                        "subscription_id": "subscription-1",
                        "allocation": {"cpu": 2, "memory": 1024, "disk": 5000},
                        "lifecycle_state": "PROVISIONING",
                        "database_type": "postgresql",
                        "database_name": "app_db",
                    },
                )

    def test_database_service_get_command_uses_saved_session(self):
        import ftp_project

        session = UserSession("access-1")
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / "session.json")
            store.save(session)
            with patch("ftp_project.SessionStore", return_value=store), patch(
                "ftp_project.MasterClient"
            ) as client_type:
                client_type.return_value.get.return_value = {
                    "id": "database-service-1",
                    "database_type": "postgresql",
                }

                self.assertEqual(
                    ftp_project.main(["database-service", "get", "database-service-1"]), 0
                )

                client_type.assert_called_once_with(session, base_url="http://localhost:8000")
                client_type.return_value.get.assert_called_once_with(
                    "/v1/database-services/database-service-1"
                )

    def test_database_user_create_command_uses_saved_session(self):
        import ftp_project

        session = UserSession("access-1")
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / "session.json")
            store.save(session)
            with patch("ftp_project.SessionStore", return_value=store), patch(
                "ftp_project.MasterClient"
            ) as client_type:
                client_type.return_value.create.return_value = {"id": "database-user-1"}

                self.assertEqual(
                    ftp_project.main(
                        [
                            "database-user",
                            "create",
                            "--database-service-id",
                            "database-service-1",
                            "--username",
                            "app_user",
                            "--privileges",
                            '{"read": true, "write": true}',
                        ]
                    ),
                    0,
                )

                client_type.assert_called_once_with(session, base_url="http://localhost:8000")
                client_type.return_value.create.assert_called_once_with(
                    "/v1/database-users",
                    {
                        "database_service_id": "database-service-1",
                        "username": "app_user",
                        "status": "PENDING",
                        "privileges": {"read": True, "write": True},
                    },
                )

    def test_database_user_get_command_uses_saved_session(self):
        import ftp_project

        session = UserSession("access-1")
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / "session.json")
            store.save(session)
            with patch("ftp_project.SessionStore", return_value=store), patch(
                "ftp_project.MasterClient"
            ) as client_type:
                client_type.return_value.get.return_value = {
                    "id": "database-user-1",
                    "database_service_id": "database-service-1",
                }

                self.assertEqual(
                    ftp_project.main(["database-user", "get", "database-user-1"]), 0
                )

                client_type.assert_called_once_with(session, base_url="http://localhost:8000")
                client_type.return_value.get.assert_called_once_with(
                    "/v1/database-users/database-user-1"
                )

    def test_web_service_create_command_uses_saved_session(self):
        import ftp_project

        session = UserSession("access-1")
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / "session.json")
            store.save(session)
            with patch("ftp_project.SessionStore", return_value=store), patch(
                "ftp_project.MasterClient"
            ) as client_type:
                client_type.return_value.create.return_value = {"id": "web-service-1"}

                self.assertEqual(
                    ftp_project.main(
                        [
                            "web-service",
                            "create",
                            "--subscription-id",
                            "subscription-1",
                            "--website-id",
                            "website-1",
                            "--allocation",
                            '{"cpu": 2, "memory": 1024, "disk": 10000}',
                            "--lifecycle-state",
                            "PROVISIONING",
                            "--web-server",
                            "nginx",
                            "--php-version",
                            "8.3",
                            "--document-root",
                            "/srv/www/example.test",
                        ]
                    ),
                    0,
                )

                client_type.assert_called_once_with(session, base_url="http://localhost:8000")
                client_type.return_value.create.assert_called_once_with(
                    "/v1/web-services",
                    {
                        "subscription_id": "subscription-1",
                        "website_id": "website-1",
                        "allocation": {"cpu": 2, "memory": 1024, "disk": 10000},
                        "lifecycle_state": "PROVISIONING",
                        "web_server": "nginx",
                        "php_version": "8.3",
                        "document_root": "/srv/www/example.test",
                    },
                )

    def test_web_service_get_command_uses_saved_session(self):
        import ftp_project

        session = UserSession("access-1")
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / "session.json")
            store.save(session)
            with patch("ftp_project.SessionStore", return_value=store), patch(
                "ftp_project.MasterClient"
            ) as client_type:
                client_type.return_value.get.return_value = {
                    "id": "web-service-1",
                    "type": "WEB",
                }

                self.assertEqual(
                    ftp_project.main(["web-service", "get", "web-service-1"]), 0
                )

                client_type.assert_called_once_with(session, base_url="http://localhost:8000")
                client_type.return_value.get.assert_called_once_with(
                    "/v1/web-services/web-service-1"
                )

    def test_dns_service_create_command_uses_saved_session(self):
        import ftp_project

        session = UserSession("access-1")
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / "session.json")
            store.save(session)
            with patch("ftp_project.SessionStore", return_value=store), patch(
                "ftp_project.MasterClient"
            ) as client_type:
                client_type.return_value.create.return_value = {"id": "dns-service-1"}

                self.assertEqual(
                    ftp_project.main(
                        [
                            "dns-service",
                            "create",
                            "--subscription-id",
                            "subscription-1",
                            "--domain-id",
                            "domain-1",
                            "--allocation",
                            '{"cpu": 1, "memory": 512, "disk": 2000}',
                            "--lifecycle-state",
                            "PROVISIONING",
                            "--configuration",
                            '{"nameservers": ["ns1.example.test"]}',
                        ]
                    ),
                    0,
                )

                client_type.assert_called_once_with(session, base_url="http://localhost:8000")
                client_type.return_value.create.assert_called_once_with(
                    "/v1/dns-services",
                    {
                        "subscription_id": "subscription-1",
                        "domain_id": "domain-1",
                        "allocation": {"cpu": 1, "memory": 512, "disk": 2000},
                        "lifecycle_state": "PROVISIONING",
                        "configuration": {"nameservers": ["ns1.example.test"]},
                    },
                )

    def test_dns_service_get_command_uses_saved_session(self):
        import ftp_project

        session = UserSession("access-1")
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / "session.json")
            store.save(session)
            with patch("ftp_project.SessionStore", return_value=store), patch(
                "ftp_project.MasterClient"
            ) as client_type:
                client_type.return_value.get.return_value = {
                    "id": "dns-service-1",
                    "type": "DNS",
                }

                self.assertEqual(
                    ftp_project.main(["dns-service", "get", "dns-service-1"]), 0
                )

                client_type.assert_called_once_with(session, base_url="http://localhost:8000")
                client_type.return_value.get.assert_called_once_with(
                    "/v1/dns-services/dns-service-1"
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
