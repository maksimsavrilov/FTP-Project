import importlib

from fastapi.testclient import TestClient


def test_agents_web_agent_module_is_loadable_and_accepts_desired_state():
    module = importlib.import_module("agents.web_agent")
    app = module.create_app(master_token="master-token")
    client = TestClient(app)

    response = client.post(
        "/v1/services/service-1/desired-state",
        json={
            "service_type": "WEB",
            "assignment_id": "assignment-1",
            "version": 1,
            "lifecycle_state": "PROVISIONING",
            "configuration": {"web_server": "nginx"},
        },
        headers={"Authorization": "Bearer master-token", "X-Request-ID": "request-1"},
    )

    assert response.status_code == 202
    assert response.json() == {"accepted": True, "service_id": "service-1", "version": 1}
