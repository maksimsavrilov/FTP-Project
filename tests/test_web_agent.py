import unittest

from fastapi.testclient import TestClient

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


if __name__ == "__main__":
    unittest.main()
