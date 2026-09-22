import unittest

from fastapi.testclient import TestClient

from agents.web_agent.app import DesiredWebServiceState, WebAgentDesiredStateStore
from ftp_project.web_agent import create_app


class WebAgentTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app(master_token="master-token"))
        self.headers = {
            "Authorization": "Bearer master-token",
            "X-Request-ID": "request-1",
        }

    def test_accepts_authenticated_web_service_desired_state_idempotently(self):
        payload = {
            "service_type": "WEB",
            "assignment_id": "assignment-1",
            "version": 1,
            "lifecycle_state": "PROVISIONING",
            "configuration": {"web_server": "nginx", "php_version": "8.3"},
        }

        first = self.client.post("/v1/services/service-1/desired-state", json=payload, headers=self.headers)
        second = self.client.post("/v1/services/service-1/desired-state", json=payload, headers=self.headers)

        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 202)
        self.assertEqual(first.json(), {"accepted": True, "service_id": "service-1", "version": 1})
        self.assertEqual(second.json(), first.json())

    def test_rejects_missing_or_invalid_master_credentials(self):
        payload = {
            "service_type": "WEB",
            "assignment_id": "assignment-1",
            "version": 1,
            "lifecycle_state": "PROVISIONING",
            "configuration": {},
        }

        response = self.client.post("/v1/services/service-1/desired-state", json=payload)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "AUTHENTICATION_FAILED")

    def test_returns_current_reconciliation_state_for_accepted_desired_version(self):
        payload = {
            "service_type": "WEB",
            "assignment_id": "assignment-1",
            "version": 3,
            "lifecycle_state": "RUNNING",
            "configuration": {"web_server": "nginx", "php_version": "8.3"},
        }

        accepted = self.client.post(
            "/v1/services/service-2/desired-state",
            json=payload,
            headers=self.headers,
        )
        reconciliation = self.client.get(
            "/v1/services/service-2/reconciliation",
            headers=self.headers,
        )

        self.assertEqual(accepted.status_code, 202)
        self.assertEqual(reconciliation.status_code, 200)
        self.assertEqual(
            reconciliation.json(),
            {
                "service_id": "service-2",
                "service_type": "WEB",
                "assignment_id": "assignment-1",
                "version": 3,
                "lifecycle_state": "RUNNING",
                "configuration": {"web_server": "nginx", "php_version": "8.3"},
                "status": "ACCEPTED",
            },
        )

    def test_store_reports_accepted_desired_state_to_master(self):
        store = WebAgentDesiredStateStore()
        state = DesiredWebServiceState.model_validate(
            {
                "service_type": "WEB",
                "assignment_id": "assignment-2",
                "version": 7,
                "lifecycle_state": "RUNNING",
                "configuration": {"web_server": "nginx", "php_version": "8.3"},
            }
        )
        accepted, rejection = store.accept("service-3", state)

        self.assertTrue(accepted)
        self.assertIsNone(rejection)

        class Client:
            def __init__(self):
                self.calls = []

            def report_web_service_actual_state(
                self,
                service_id,
                assignment_id,
                version,
                status,
                configuration,
                health,
                observed_at,
                request_id=None,
            ):
                self.calls.append(
                    {
                        "service_id": service_id,
                        "assignment_id": assignment_id,
                        "version": version,
                        "status": status,
                        "configuration": configuration,
                        "health": health,
                        "observed_at": observed_at,
                        "request_id": request_id,
                    }
                )
                return {"accepted": True}

        client = Client()
        result = store.report_actual_state(
            "service-3",
            client,
            status="RUNNING",
            health={"ready": True},
            observed_at="2026-01-01T00:10:00Z",
        )

        self.assertEqual(result, {"accepted": True})
        self.assertEqual(client.calls, [{
            "service_id": "service-3",
            "assignment_id": "assignment-2",
            "version": 7,
            "status": "RUNNING",
            "configuration": {"web_server": "nginx", "php_version": "8.3"},
            "health": {"ready": True},
            "observed_at": "2026-01-01T00:10:00Z",
            "request_id": None,
        }])


if __name__ == "__main__":
    unittest.main()
