import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from master.auth import AuthenticationClient
from master.composition import build_master_api, create_master_app


class MasterCompositionTests(unittest.TestCase):
    def test_production_composition_wires_all_master_boundaries(self):
        engine = create_engine("sqlite:///:memory:")
        authentication_client = AuthenticationClient("http://auth")

        api = build_master_api(lambda: Session(engine), authentication_client)

        self.assertIs(api.authorization_client, authentication_client)
        for service_name in (
            "node_service",
            "reconciliation_service",
            "user_service",
            "service_plan_service",
            "subscription_service",
            "domain_service",
            "website_service",
            "service_service",
            "web_service_service",
            "dns_service_service",
            "mail_service_service",
            "database_service_service",
            "database_user_service",
            "mail_domain_service",
            "mail_account_service",
            "identity_reference_service",
            "account_service",
            "resource_entitlement_service",
        ):
            self.assertIsNotNone(getattr(api, service_name))

    def test_app_factory_reads_production_configuration(self):
        app = create_master_app("sqlite:///:memory:", "http://auth")

        self.assertTrue(any(route.path == "/v1/users" for route in app.routes))
