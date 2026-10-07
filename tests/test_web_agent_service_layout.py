import importlib
import json
import os

from fastapi.testclient import TestClient

from agents.web_agent import entrypoint


def test_web_agent_registers_with_master_at_startup_and_persists_credentials(
    monkeypatch,
):
    captured = {}

    class FakeResponse:
        def __init__(self, body):
            self._body = body.encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return self._body

    def fake_open(request, timeout=5):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse(
            json.dumps({"id": "node-42", "credential": "node-credential-1"})
        )

    monkeypatch.setenv("MASTER_SERVICE_URL", "http://master:8000")
    monkeypatch.setenv("NODE_BOOTSTRAP_CREDENTIAL", "bootstrap-secret")
    monkeypatch.setenv("WEB_AGENT_HOSTNAME", "web-agent-01")
    monkeypatch.delenv("WEB_AGENT_NODE_ID", raising=False)
    monkeypatch.delenv("WEB_AGENT_NODE_CREDENTIAL", raising=False)

    registration = entrypoint.register_node(opener=fake_open)

    assert registration.node_id == "node-42"
    assert registration.credential == "node-credential-1"
    assert captured["url"] == "http://master:8000/v1/nodes/register"
    assert captured["payload"]["bootstrap_credential"] == "bootstrap-secret"
    assert os.environ["WEB_AGENT_NODE_ID"] == "node-42"
    assert os.environ["WEB_AGENT_NODE_CREDENTIAL"] == "node-credential-1"


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
    assert response.json() == {
        "accepted": True,
        "service_id": "service-1",
        "version": 1,
    }
